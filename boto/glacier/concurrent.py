# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
import os
import math
import threading
import hashlib
import time
import logging
from Queue import Queue, Empty

from .writer import chunk_hashes, tree_hash, bytes_to_hex
from .exceptions import UploadArchiveError


DEFAULT_PART_SIZE = 4 * 1024 * 1024
_END_SENTINEL = object()
log = logging.getLogger('boto.glacier.concurrent')


class ConcurrentUploader(object):
    """Concurrently upload an archive to glacier.

    This class uses a thread pool to concurrently upload an archive
    to glacier using the multipart upload API.

    The threadpool is completely managed by this class and is
    transparent to the users of this class.

    """
    def __init__(self, api, vault_name, part_size=DEFAULT_PART_SIZE,
                 num_threads=10):
        """
        :type api: :class:`boto.glacier.layer1.Layer1`
        :param api: A layer1 glacier object.

        :type vault_name: str
        :param vault_name: The name of the vault.

        :type part_size: int
        :param part_size: The size, in bytes, of the chunks to use when uploading
            the archive parts.  The part size must be a megabyte multiplied by
            a power of two.

        """
        self._api = api
        self._vault_name = vault_name
        self._part_size = part_size
        self._num_threads = num_threads
        self._threads = []

    def upload(self, filename, description=None):
        """Concurrently create an archive.

        :type file: str
        :param file: The filename to upload

        :type description: str
        :param description: The description of the archive.

        :rtype: str
        :return: The archive id of the newly created archive.

        """
        fileobj = open(filename, 'rb')
        total_size = os.fstat(fileobj.fileno()).st_size
        total_parts = int(math.ceil(total_size / float(self._part_size)))
        hash_chunks = [None] * total_parts
        worker_queue = Queue()
        result_queue = Queue()
        response = self._api.initiate_multipart_upload(self._vault_name,
                                                       self._part_size,
                                                       description)
        upload_id = response['UploadId']
        # The basic idea is to add the chunks (the offsets not the actual
        # contents) to a work queue, start up a thread pool, let the crank
        # through the items in the work queue, and then place their results
        # in a result queue which we use to complete the multipart upload.
        self._add_work_items_to_queue(total_parts, worker_queue)
        self._start_upload_threads(result_queue, upload_id,
                                   worker_queue, filename)
        try:
            self._wait_for_upload_threads(hash_chunks, result_queue, total_parts)
        except UploadArchiveError, e:
            log.debug("An error occurred while uploading an archive, aborting "
                      "multipart upload.")
            self._api.abort_multipart_upload(self._vault_name, upload_id)
            raise e
        log.debug("Completing upload.")
        response = self._api.complete_multipart_upload(
            self._vault_name, upload_id, bytes_to_hex(tree_hash(hash_chunks)),
            total_size)
        log.debug("Upload finished.")
        return response['ArchiveId']

    def _wait_for_upload_threads(self, hash_chunks, result_queue, total_parts):
        for _ in xrange(total_parts):
            result = result_queue.get()
            if isinstance(result, Exception):
                log.debug("An error was found in the result queue, terminating "
                          "threads: %s", result)
                self._shutdown_threads()
                raise UploadArchiveError("An error occurred while uploading "
                                         "an archive: %s" % result)
            # Each unit of work returns the tree hash for the given part
            # number, which we use at the end to compute the tree hash of
            # the entire archive.
            part_number, tree_sha256 = result
            hash_chunks[part_number] = tree_sha256
        self._shutdown_threads()

    def _shutdown_threads(self):
        log.debug("Shutting down threads.")
        for thread in self._threads:
            thread.should_continue = False
        for thread in self._threads:
            thread.join()
        log.debug("Threads have exited.")

    def _start_upload_threads(self, result_queue, upload_id, worker_queue, filename):
        log.debug("Starting threads.")
        for _ in xrange(self._num_threads):
            thread = UploadWorkerThread(self._api, self._vault_name, filename,
                                        upload_id, worker_queue, result_queue)
            time.sleep(0.2)
            thread.start()
            self._threads.append(thread)

    def _add_work_items_to_queue(self, total_parts, worker_queue):
        log.debug("Adding work items to queue.")
        for i in xrange(total_parts):
            worker_queue.put((i, self._part_size))
        for i in xrange(self._num_threads):
            worker_queue.put(_END_SENTINEL)


class UploadWorkerThread(threading.Thread):
    def __init__(self, api, vault_name, filename, upload_id,
                 worker_queue, result_queue, num_retries=5,
                 time_between_retries=5,
                 retry_exceptions=Exception):
        threading.Thread.__init__(self)
        self._api = api
        self._vault_name = vault_name
        self._filename = filename
        self._fileobj = open(filename, 'rb')
        self._worker_queue = worker_queue
        self._result_queue = result_queue
        self._upload_id = upload_id
        self._num_retries = num_retries
        self._time_between_retries = time_between_retries
        self._retry_exceptions = retry_exceptions
        self.should_continue = True

    def run(self):
        while self.should_continue:
            try:
                work = self._worker_queue.get(timeout=1)
            except Empty:
                continue
            if work is _END_SENTINEL:
                return
            result = self._process_chunk(work)
            self._result_queue.put(result)

    def _process_chunk(self, work):
        result = None
        for _ in xrange(self._num_retries):
            try:
                result = self._upload_chunk(work)
                break
            except self._retry_exceptions, e:
                log.error("Exception caught uploading part number %s for "
                          "vault %s, filename: %s", work[0], self._vault_name,
                          self._filename)
                time.sleep(self._time_between_retries)
                result = e
        return result

    def _upload_chunk(self, work):
        part_number, part_size = work
        start_byte = part_number * part_size
        self._fileobj.seek(start_byte)
        contents = self._fileobj.read(part_size)
        linear_hash = hashlib.sha256(contents).hexdigest()
        tree_hash_bytes = tree_hash(chunk_hashes(contents))
        byte_range = (start_byte, start_byte + len(contents) - 1)
        log.debug("Uploading chunk %s of size %s", part_number, part_size)
        response = self._api.upload_part(self._vault_name, self._upload_id,
                                         linear_hash,
                                         bytes_to_hex(tree_hash_bytes),
                                         byte_range, contents)
        # Reading the response allows the connection to be reused.
        response.read()
        return (part_number, tree_hash_bytes)
