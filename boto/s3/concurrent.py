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

from __future__ import with_statement

import os
import math
import threading
import time
import logging
from Queue import Queue, Empty

from boto.s3.key import Key

_END_SENTINEL = object()

log = logging.getLogger('boto.s3.concurrent')

DEFAULT_PART_SIZE = 10 * 1024 * 1024
DEFAULT_NUM_THREADS = 1


class ConcurrentS3Error(Exception):
    pass


class UploadConcurrentS3Error(ConcurrentS3Error):
    pass


class ConcurrentTransferer(object):
    def __init__(self, part_size=DEFAULT_PART_SIZE, num_threads=DEFAULT_NUM_THREADS):
        if part_size < 5 * 1024 * 1024:
            raise ValueError("Minimum part size for multipart upload is 5MB")
        self._part_size = part_size
        self._num_threads = num_threads
        self._threads = []

    def _calculate_required_part_size(self, total_size):
        total_parts = int(math.ceil(total_size / float(self._part_size)))
        return total_parts, self._part_size

    def _shutdown_threads(self):
        log.debug("Shutting down threads.")
        for thread in self._threads:
            thread.should_continue = False
        for thread in self._threads:
            thread.join()
        log.debug("Threads have exited.")

    def _add_work_items_to_queue(self, total_parts, worker_queue, part_size):
        log.debug("Adding work items to queue.")
        for i in xrange(1, total_parts + 1):
            worker_queue.put((i, part_size))
        for i in xrange(self._num_threads):
            worker_queue.put(_END_SENTINEL)


class ConcurrentUploader(ConcurrentTransferer):
    """
    Concurrently upload a file to S3.

    This class uses a thread pool to concurrently upload a file
    to S3 using the multipart upload API.

    The threadpool is completely managed by this class and is
    transparent to the users of this class.

    """
    def __init__(self, boto_bucket, part_size=DEFAULT_PART_SIZE,
                 num_threads=DEFAULT_NUM_THREADS):
        """
        :type api: :class:`boto.s3.Bucket`
        :param boto_bucket: A boto S3 Bucket

        :type part_size: int
        :param part_size: The size, in bytes, of the chunks to use when uploading
            the file parts.

        :type num_threads: int
        :param num_threads: The number of threads to spawn for the thread pool.
            The number of threads will control how many parts are being
            concurrently uploaded.

        """
        super(ConcurrentUploader, self).__init__(part_size, num_threads)
        self._bucket = boto_bucket
        pass

    def upload(self, filename, key_name, headers=None,
               reduced_redundancy=False,
               metadata=None, encrypt_key=False,
               policy=None):
        """
        Concurrently upload file.

        The part_size value specified when the class was constructed
        will be used *unless* it is smaller than the minimum required
        part size needed for the size of the given file.  In that case,
        the part size used will be the minimum part size required
        to properly upload the given file.

        :type filename: str
        :param filename: The filename to upload

        :type key_name: string
        :param key_name: The name of the key that will ultimately
            result from this multipart upload operation.  This will be
            exactly as the key appears in the bucket after the upload
            process has been completed.

        :type headers: dict
        :param headers: Additional HTTP headers to send and store with the
            resulting key in S3.

        :type reduced_redundancy: boolean
        :param reduced_redundancy: In multipart uploads, the storage
            class is specified when initiating the upload, not when
            uploading individual parts.  So if you want the resulting
            key to use the reduced redundancy storage class set this
            flag when you initiate the upload.

        :type metadata: dict
        :param metadata: Any metadata that you would like to set on the key
            that results from the multipart upload.

        :type encrypt_key: bool
        :param encrypt_key: If True, the new copy of the object will
            be encrypted on the server-side by S3 and will be stored
            in an encrypted form while at rest in S3.

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the
            new key (once completed) in S3.
        """
        total_size = os.stat(filename).st_size
        total_parts, part_size = self._calculate_required_part_size(total_size)

        if self._bucket.get_key(key_name) is None:
            log.debug("Creating Key")
            k = Key(self._bucket)
            k.key = key_name
            k.set_contents_from_string('This is a test of S3')

        worker_queue = Queue()
        result_queue = Queue()
        mp_upload = self._bucket.initiate_multipart_upload(key_name, headers=headers,
                                                           reduced_redundancy=reduced_redundancy,
                                                           metadata=metadata, encrypt_key=encrypt_key,
                                                           policy=policy)
        # The basic idea is to add the chunks (the offsets not the actual
        # contents) to a work queue, start up a thread pool, let the crank
        # through the items in the work queue, and then place their results
        # in a result queue which we use to complete the multipart upload.
        self._add_work_items_to_queue(total_parts, worker_queue, part_size)
        self._start_upload_threads(result_queue, mp_upload,
                                   worker_queue, filename)
        try:
            self._wait_for_upload_threads(result_queue,
                                          total_parts)
        except UploadConcurrentS3Error as e:
            log.error("An error occurred while uploading file, aborting multipart upload.")
            log.error("Aborting upload")
            mp_upload.cancel_upload()
            raise e
        try:
            log.debug("Completing upload.")
            mp_upload.complete_upload()
            log.debug("Upload finished.")
        except Exception as e:
            log.error("An error occurred while uploading file, aborting multipart upload.")
            log.error("Aborting upload")
            mp_upload.cancel_upload()
            raise e

    def _wait_for_upload_threads(self, result_queue, total_parts):
        for _ in xrange(total_parts):
            result = result_queue.get()
            if isinstance(result, Exception):
                log.error("An error was found in the result queue, terminating "
                          "threads: %s", result)
                self._shutdown_threads()
                raise UploadConcurrentS3Error("An error occurred while uploading an archive: %s" % result)

        self._shutdown_threads()

    def _start_upload_threads(self, result_queue, mp_upload, worker_queue,
                              filename):
        log.debug("Starting threads.")
        for _ in xrange(self._num_threads):
            thread = UploadWorkerThread(filename, mp_upload, worker_queue, result_queue)
            time.sleep(0.2)
            thread.start()
            self._threads.append(thread)


class TransferThread(threading.Thread):
    def __init__(self, worker_queue, result_queue):
        super(TransferThread, self).__init__()
        self._worker_queue = worker_queue
        self._result_queue = result_queue
        # This value can be set externally by other objects
        # to indicate that the thread should be shut down.
        self.should_continue = True

    def run(self):
        while self.should_continue:
            try:
                work = self._worker_queue.get(timeout=1)
            except Empty:
                continue
            if work is _END_SENTINEL:
                self._cleanup()
                return
            result = self._process_chunk(work)
            self._result_queue.put(result)
        self._cleanup()

    def _process_chunk(self, work):
        pass

    def _cleanup(self):
        pass


class UploadWorkerThread(TransferThread):
    def __init__(self, filename, mp_upload,
                 worker_queue, result_queue, num_retries=5,
                 time_between_retries=5,
                 retry_exceptions=Exception):
        super(UploadWorkerThread, self).__init__(worker_queue, result_queue)
        self._filename = filename
        self._fileobj = open(filename, 'rb')
        self._mp_upload = mp_upload
        self._num_retries = num_retries
        self._time_between_retries = time_between_retries
        self._retry_exceptions = retry_exceptions

    def _process_chunk(self, work):
        result = None
        for i in xrange(self._num_retries + 1):
            try:
                result = self._upload_chunk(work)
                break
            except self._retry_exceptions, e:
                log.error("Exception caught uploading part number %s for "
                          "Multipart Upload %s, attempt: (%s / %s), filename: %s, "
                          "exception: %s, msg: %s",
                          work[0], self._mp_upload, i + 1, self._num_retries + 1,
                          self._filename, e.__class__, e)
                time.sleep(self._time_between_retries)
                result = e
        return result

    def _upload_chunk(self, work):
        part_number, part_size = work
        start_byte = (part_number-1) * part_size
        self._fileobj.seek(start_byte)
        log.debug("Uploading chunk %s of size %s", part_number, part_size)
        result = self._mp_upload.upload_part_from_file(self._fileobj, part_number, headers=None, replace=True,
                                                       cb=None, num_cb=10, md5=None, size=part_size)
        log.debug("Finished Uploading chunk %s of size %s", part_number, part_size)
        return result

    def _cleanup(self):
        self._fileobj.close()
