import os
import math
import threading
import time
import logging
import string
import tempfile
import shutil
from random import choice
from Queue import Queue, Empty, PriorityQueue

import boto
import boto.glacier as glacier

DEFAULT_PART_SIZE = 4 * 1024 * 1024
_END_SENTINEL = object()
log = logging.getLogger('boto.glacier.concurrent')

class DownloadArchiveError(Exception):
    pass

def _get_random_alphanumeric(length):
    '''
    Create random alphanumeric string of given length
    @param length:
    '''
    chars = string.letters + string.digits
    characters = []
    for _i in range(length):
        characters.append(choice(chars))
    return "".join(characters)

class ConcurrentDownloader(object):
    """
    Concurrently download an archive from glacier.

    This class uses a thread pool to concurrently download an archive
    from glacier.

    The threadpool is completely managed by this class and is
    transparent to the users of this class.

    """
    def __init__(self, job, part_size=DEFAULT_PART_SIZE,
                 num_threads=10):
        """
        :param job: A layer2 job object for archive retrieval object.

        :param part_size: The size, in bytes, of the chunks to use when uploading
            the archive parts.  The part size must be a megabyte multiplied by
            a power of two.

        """
        self._job = job
        self._part_size = part_size
        self._num_threads = num_threads
        self._threads = []

    def download(self, filename):
        """
        Concurrently download an archive.

        :param filename: The filename to download the archive to
        :type filename: str

        """
        total_size = self._job.archive_size
        total_parts = int(math.ceil(total_size / float(self._part_size)))
        worker_queue = Queue()
        result_queue = PriorityQueue()
        self._add_work_items_to_queue(total_parts, worker_queue)
        self._start_download_threads(result_queue, worker_queue)
        try:
            self._wait_for_upload_threads(filename, result_queue, total_parts)
        except DownloadArchiveError, e:
            log.debug("An error occurred while downloading an archive, aborting "
                      "multipart download.")
            raise e
        log.debug("Completing download.")
        return 0

    def _wait_for_upload_threads(self, filename, result_queue, total_parts):
        '''
        Waits until the result_queue is filled with all the downloaded parts
        This indicates that all part downloads have completed
        
        Saves downloaded parts into filename
        
        :param filename:
        :param result_queue:
        :param total_parts:
        '''
        #   TODO:   Need to delete temp files if download fails or is shutdown before completing
        while result_queue.qsize() < total_parts:
            time.sleep(.5)
        #   Pops part_number and location of the download temp file from the result_queue
        #   Result_queue is a priority queue so parts are always popped in order
        #   Temp file is read and data appended to final download file
        #   Original temp file deleted
        with open(filename, "wb") as f:
            while not result_queue.empty():
                _part_number, tmp_file = result_queue.get()
                if isinstance(tmp_file, Exception):
                    log.debug("An error was found in the result queue, terminating "
                              "threads: %s", tmp_file)
                    self._shutdown_threads()
                    raise DownloadArchiveError("An error occurred while uploading "
                                             "an archive: %s" % tmp_file)
                with open(tmp_file, 'rb') as f_tmp:
                    shutil.copyfileobj(f_tmp, f)
                os.remove(tmp_file)
        self._shutdown_threads()

    def _shutdown_threads(self):
        log.debug("Shutting down threads.")
        for thread in self._threads:
            thread.should_continue = False
        for thread in self._threads:
            thread.join()
        log.debug("Threads have exited.")

    def _start_download_threads(self, result_queue, worker_queue):
        log.debug("Starting threads.")
        for _ in xrange(self._num_threads):
            thread = DownloadWorkerThread(self._job, worker_queue, result_queue)
            time.sleep(0.2)
            thread.start()
            self._threads.append(thread)

    def _add_work_items_to_queue(self, total_parts, worker_queue):
        log.debug("Adding work items to queue.")
        for i in xrange(total_parts):
            worker_queue.put((i, self._part_size))
        for i in xrange(self._num_threads):
            worker_queue.put(_END_SENTINEL)


class DownloadWorkerThread(threading.Thread):
    def __init__(self, job,
                 worker_queue, result_queue,
                 tmp_dir = tempfile.gettempdir(),
                 num_retries=5,
                 time_between_retries=5,
                 retry_exceptions=Exception):
        '''
        Individual download thread that will download parts of the file from Glacier. Parts
        to download stored in work queue.

        Parts download to a temp dir with each part a separate file
        
        :param job:    Glacier job object
        :param work_queue:    A queue of tuples which include the part_number and part_size
        :param result_queue:    A priority queue of tuples which include the part_number and the path to the temp file that holds that part's data
        :param tmp_dir:    Directory to hold downloaded parts
        '''
        threading.Thread.__init__(self)
        self._job = job
        self._worker_queue = worker_queue
        self._result_queue = result_queue
        self._tmp_dir = tmp_dir
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
        '''
        Attempt to download a part of the archive from Glacier
        Store the result in the result_queue
        
        :param work:
        '''
        result = None
        for _ in xrange(self._num_retries):
            try:
                result = self._download_chunk(work)
                break
            except self._retry_exceptions, e:
                log.error("Exception caught downloading part number %s for "
                          "job %s", work[0], self._job,)
                time.sleep(self._time_between_retries)
                #   If there is an exception, we want the exception to be the first item in the
                #   result_queue, hence the 0 in the tuple
                result = (0, e)
        return result

    def _download_chunk(self, work):
        '''
        Downloads a chunk of archive from Glacier. Saves the data to a temp file
        Returns the part number and temp file location
        
        :param work:
        '''
        part_number, part_size = work
        start_byte = part_number * part_size
        byte_range = (start_byte, start_byte + part_size - 1)
        tmp_file = os.path.join(self._tmp_dir, "glacier_download_{}.{}".format(_get_random_alphanumeric(5),
                                                                               part_number))
        log.debug("Downloading chunk %s of size %s", part_number, part_size)
        response = self._job.get_output(byte_range)
        data = response.read()
        with open(tmp_file, "wb") as f:
            f.write(data)
        return (part_number, tmp_file)

if __name__ == '__main__':
    pass
    """
    Sample download code
    
    DEFAULT_PART_SIZE = 4 * 1024 * 1024
    THREADS = 10
    
    glacier_l2 = boto.glacier.connect_to_region(region_name='us-east-1', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    vault = glacier_l2.get_vault(VAULT_NAME)
    job = vault.get_job(archive_download_request_job_id)    
    cd = ConcurrentDownloader(job, part_size=DEFAULT_PART_SIZE*10, num_threads=THREADS)
    cd.download(download_file_path)
    """

