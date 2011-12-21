#!/usr/bin/env python
#
# Copyright 2010 Google Inc.
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

"""
Tests of resumable downloads.
"""

import errno
import getopt
import os
import random
import re
import shutil
import socket
import StringIO
import sys
import tempfile
import time
import unittest

import boto
from boto import storage_uri
from boto.s3.resumable_download_handler import get_cur_file_size
from boto.s3.resumable_download_handler import ResumableDownloadHandler
from boto.exception import ResumableTransferDisposition
from boto.exception import ResumableDownloadException
from boto.exception import StorageResponseError
from cb_test_harnass import CallbackTestHarnass

# We don't use the OAuth2 authentication plugin directly; importing it here
# ensures that it's loaded and available by default.
try:
  from oauth2_plugin import oauth2_plugin
except ImportError:
  # Do nothing - if user doesn't have OAuth2 configured it doesn't matter;
  # and if they do, the tests will fail (as they should in that case).
  pass


class ResumableDownloadTests(unittest.TestCase):
    """
    Resumable download test suite.
    """

    def get_suite_description(self):
        return 'Resumable download test suite'

    @staticmethod
    def resilient_close(key):
        try:
            key.close()
        except StorageResponseError, e:
            pass

    @classmethod
    def setUp(cls):
        """
        Creates file-like object for detination of each download test.

        This method's namingCase is required by the unittest framework.
        """
        cls.dst_fp = open(cls.dst_file_name, 'w')

    @classmethod
    def tearDown(cls):
        """
        Deletes any objects or files created by last test run, and closes
        any keys in case they were read incompletely (which would leave
        partial buffers of data for subsequent tests to trip over).

        This method's namingCase is required by the unittest framework.
        """
        # Recursively delete dst dir and then re-create it, so in effect we
        # remove all dirs and files under that directory.
        shutil.rmtree(cls.tmp_dir)
        os.mkdir(cls.tmp_dir)

        # Close test objects.
        cls.resilient_close(cls.empty_src_key)
        cls.resilient_close(cls.small_src_key)
        cls.resilient_close(cls.larger_src_key)

    @classmethod
    def build_test_input_object(cls, obj_name, size, debug):
        buf = []
        for i in range(size):
            buf.append(str(random.randint(0, 9)))
        string_data = ''.join(buf)
        uri = cls.src_bucket_uri.clone_replace_name(obj_name)
        key = uri.new_key(validate=False)
        key.set_contents_from_file(StringIO.StringIO(string_data))
        # Set debug on key's connection after creating data, so only the test
        # runs will show HTTP output (if called passed debug>0).
        key.bucket.connection.debug = debug
        return (string_data, key)

    @classmethod
    def set_up_class(cls, debug):
        """
        Initializes test suite.
        """

        # Create the test bucket.
        hostname = socket.gethostname().split('.')[0]
        uri_base_str = 'gs://res-download-test-%s-%s-%s' % (
            hostname, os.getpid(), int(time.time()))
        cls.src_bucket_uri = storage_uri('%s-dst' % uri_base_str)
        cls.src_bucket_uri.create_bucket()

        # Create test source objects.
        cls.empty_src_key_size = 0
        (cls.empty_src_key_as_string, cls.empty_src_key) = (
            cls.build_test_input_object('empty', cls.empty_src_key_size,
                                        debug=debug))
        cls.small_src_key_size = 2 * 1024  # 2 KB.
        (cls.small_src_key_as_string, cls.small_src_key) = (
            cls.build_test_input_object('small', cls.small_src_key_size,
                                        debug=debug))
        cls.larger_src_key_size = 500 * 1024  # 500 KB.
        (cls.larger_src_key_as_string, cls.larger_src_key) = (
            cls.build_test_input_object('larger', cls.larger_src_key_size,
                                        debug=debug))

        # Use a designated tmpdir prefix to make it easy to find the end of
        # the tmp path.
        cls.tmpdir_prefix = 'tmp_resumable_download_test'

        # Create temp dir and name for download file.
        cls.tmp_dir = tempfile.mkdtemp(prefix=cls.tmpdir_prefix)
        cls.dst_file_name = '%s%sdst_file' % (cls.tmp_dir, os.sep)

        cls.tracker_file_name = '%s%stracker' % (cls.tmp_dir, os.sep)

        cls.created_test_data = True

    @classmethod
    def tear_down_class(cls):
        """
        Deletes test objects and bucket and tmp dir created by set_up_class.
        """
        if not hasattr(cls, 'created_test_data'):
            return
        # Call cls.tearDown() in case the tests got interrupted, to ensure
        # dst objects get deleted.
        cls.tearDown()

        # Delete test objects.
        cls.empty_src_key.delete()
        cls.small_src_key.delete()
        cls.larger_src_key.delete()

        # Retry (for up to 2 minutes) the bucket gets deleted (it may not
        # the first time round, due to eventual consistency of bucket delete
        # operations).
        for i in range(60):
            try:
                cls.src_bucket_uri.delete_bucket()
                break
            except StorageResponseError:
                print 'Test bucket (%s) not yet deleted, still trying' % (
                    cls.src_bucket_uri.uri)
                time.sleep(2)
        shutil.rmtree(cls.tmp_dir)
        cls.tmp_dir = tempfile.mkdtemp(prefix=cls.tmpdir_prefix)

    def test_non_resumable_download(self):
        """
        Tests that non-resumable downloads work
        """
        self.small_src_key.get_contents_to_file(self.dst_fp)
        self.assertEqual(self.small_src_key_size,
                         get_cur_file_size(self.dst_fp))
        self.assertEqual(self.small_src_key_as_string,
                         self.small_src_key.get_contents_as_string())

    def test_download_without_persistent_tracker(self):
        """
        Tests a single resumable download, with no tracker persistence
        """
        res_download_handler = ResumableDownloadHandler()
        self.small_src_key.get_contents_to_file(
            self.dst_fp, res_download_handler=res_download_handler)
        self.assertEqual(self.small_src_key_size,
                         get_cur_file_size(self.dst_fp))
        self.assertEqual(self.small_src_key_as_string,
                         self.small_src_key.get_contents_as_string())

    def test_failed_download_with_persistent_tracker(self):
        """
        Tests that failed resumable download leaves a correct tracker file
        """
        harnass = CallbackTestHarnass()
        res_download_handler = ResumableDownloadHandler(
            tracker_file_name=self.tracker_file_name, num_retries=0)
        try:
            self.small_src_key.get_contents_to_file(
                self.dst_fp, cb=harnass.call,
                res_download_handler=res_download_handler)
            self.fail('Did not get expected ResumableDownloadException')
        except ResumableDownloadException, e:
            # We'll get a ResumableDownloadException at this point because
            # of CallbackTestHarnass (above). Check that the tracker file was
            # created correctly.
            self.assertEqual(e.disposition,
                             ResumableTransferDisposition.ABORT_CUR_PROCESS)
            self.assertTrue(os.path.exists(self.tracker_file_name))
            f = open(self.tracker_file_name)
            etag_line = f.readline()
            m = re.search(ResumableDownloadHandler.ETAG_REGEX, etag_line)
            f.close()
            self.assertTrue(m)

    def test_retryable_exception_recovery(self):
        """
        Tests handling of a retryable exception
        """
        # Test one of the RETRYABLE_EXCEPTIONS.
        exception = ResumableDownloadHandler.RETRYABLE_EXCEPTIONS[0]
        harnass = CallbackTestHarnass(exception=exception)
        res_download_handler = ResumableDownloadHandler(num_retries=1)
        self.small_src_key.get_contents_to_file(
            self.dst_fp, cb=harnass.call,
            res_download_handler=res_download_handler)
        # Ensure downloaded object has correct content.
        self.assertEqual(self.small_src_key_size,
                         get_cur_file_size(self.dst_fp))
        self.assertEqual(self.small_src_key_as_string,
                         self.small_src_key.get_contents_as_string())

    def test_broken_pipe_recovery(self):
        """
        Tests handling of a Broken Pipe (which interacts with an httplib bug)
        """
        exception = IOError(errno.EPIPE, "Broken pipe")
        harnass = CallbackTestHarnass(exception=exception)
        res_download_handler = ResumableDownloadHandler(num_retries=1)
        self.small_src_key.get_contents_to_file(
            self.dst_fp, cb=harnass.call,
            res_download_handler=res_download_handler)
        # Ensure downloaded object has correct content.
        self.assertEqual(self.small_src_key_size,
                         get_cur_file_size(self.dst_fp))
        self.assertEqual(self.small_src_key_as_string,
                         self.small_src_key.get_contents_as_string())

    def test_non_retryable_exception_handling(self):
        """
        Tests resumable download that fails with a non-retryable exception
        """
        harnass = CallbackTestHarnass(
            exception=OSError(errno.EACCES, 'Permission denied'))
        res_download_handler = ResumableDownloadHandler(num_retries=1)
        try:
            self.small_src_key.get_contents_to_file(
                self.dst_fp, cb=harnass.call,
                res_download_handler=res_download_handler)
            self.fail('Did not get expected OSError')
        except OSError, e:
            # Ensure the error was re-raised.
            self.assertEqual(e.errno, 13)

    def test_failed_and_restarted_download_with_persistent_tracker(self):
        """
        Tests resumable download that fails once and then completes,
        with tracker file
        """
        harnass = CallbackTestHarnass()
        res_download_handler = ResumableDownloadHandler(
            tracker_file_name=self.tracker_file_name, num_retries=1)
        self.small_src_key.get_contents_to_file(
            self.dst_fp, cb=harnass.call,
            res_download_handler=res_download_handler)
        # Ensure downloaded object has correct content.
        self.assertEqual(self.small_src_key_size,
                         get_cur_file_size(self.dst_fp))
        self.assertEqual(self.small_src_key_as_string,
                         self.small_src_key.get_contents_as_string())
        # Ensure tracker file deleted.
        self.assertFalse(os.path.exists(self.tracker_file_name))

    def test_multiple_in_process_failures_then_succeed(self):
        """
        Tests resumable download that fails twice in one process, then completes
        """
        res_download_handler = ResumableDownloadHandler(num_retries=3)
        self.small_src_key.get_contents_to_file(
            self.dst_fp, res_download_handler=res_download_handler)
        # Ensure downloaded object has correct content.
        self.assertEqual(self.small_src_key_size,
                         get_cur_file_size(self.dst_fp))
        self.assertEqual(self.small_src_key_as_string,
                         self.small_src_key.get_contents_as_string())

    def test_multiple_in_process_failures_then_succeed_with_tracker_file(self):
        """
        Tests resumable download that fails completely in one process,
        then when restarted completes, using a tracker file
        """
        # Set up test harnass that causes more failures than a single
        # ResumableDownloadHandler instance will handle, writing enough data
        # before the first failure that some of it survives that process run.
        harnass = CallbackTestHarnass(
            fail_after_n_bytes=self.larger_src_key_size/2, num_times_to_fail=2)
        res_download_handler = ResumableDownloadHandler(
            tracker_file_name=self.tracker_file_name, num_retries=0)
        try:
            self.larger_src_key.get_contents_to_file(
                self.dst_fp, cb=harnass.call,
                res_download_handler=res_download_handler)
            self.fail('Did not get expected ResumableDownloadException')
        except ResumableDownloadException, e:
            self.assertEqual(e.disposition,
                             ResumableTransferDisposition.ABORT_CUR_PROCESS)
            # Ensure a tracker file survived.
            self.assertTrue(os.path.exists(self.tracker_file_name))
        # Try it one more time; this time should succeed.
        self.larger_src_key.get_contents_to_file(
            self.dst_fp, cb=harnass.call,
            res_download_handler=res_download_handler)
        self.assertEqual(self.larger_src_key_size,
                         get_cur_file_size(self.dst_fp))
        self.assertEqual(self.larger_src_key_as_string,
                         self.larger_src_key.get_contents_as_string())
        self.assertFalse(os.path.exists(self.tracker_file_name))
        # Ensure some of the file was downloaded both before and after failure.
        self.assertTrue(
            len(harnass.transferred_seq_before_first_failure) > 1 and
            len(harnass.transferred_seq_after_first_failure) > 1)

    def test_download_with_inital_partial_download_before_failure(self):
        """
        Tests resumable download that successfully downloads some content
        before it fails, then restarts and completes
        """
        # Set up harnass to fail download after several hundred KB so download
        # server will have saved something before we retry.
        harnass = CallbackTestHarnass(
            fail_after_n_bytes=self.larger_src_key_size/2)
        res_download_handler = ResumableDownloadHandler(num_retries=1)
        self.larger_src_key.get_contents_to_file(
            self.dst_fp, cb=harnass.call,
            res_download_handler=res_download_handler)
        # Ensure downloaded object has correct content.
        self.assertEqual(self.larger_src_key_size,
                         get_cur_file_size(self.dst_fp))
        self.assertEqual(self.larger_src_key_as_string,
                         self.larger_src_key.get_contents_as_string())
        # Ensure some of the file was downloaded both before and after failure.
        self.assertTrue(
            len(harnass.transferred_seq_before_first_failure) > 1 and
            len(harnass.transferred_seq_after_first_failure) > 1)

    def test_zero_length_object_download(self):
        """
        Tests downloading a zero-length object (exercises boundary conditions).
        """
        res_download_handler = ResumableDownloadHandler()
        self.empty_src_key.get_contents_to_file(
            self.dst_fp, res_download_handler=res_download_handler)
        self.assertEqual(0, get_cur_file_size(self.dst_fp))

    def test_download_with_invalid_tracker_etag(self):
        """
        Tests resumable download with a tracker file containing an invalid etag
        """
        invalid_etag_tracker_file_name = (
            '%s%sinvalid_etag_tracker' % (self.tmp_dir, os.sep))
        f = open(invalid_etag_tracker_file_name, 'w')
        f.write('3.14159\n')
        f.close()
        res_download_handler = ResumableDownloadHandler(
            tracker_file_name=invalid_etag_tracker_file_name)
        # An error should be printed about the invalid tracker, but then it
        # should run the update successfully.
        self.small_src_key.get_contents_to_file(
            self.dst_fp, res_download_handler=res_download_handler)
        self.assertEqual(self.small_src_key_size,
                         get_cur_file_size(self.dst_fp))
        self.assertEqual(self.small_src_key_as_string,
                         self.small_src_key.get_contents_as_string())

    def test_download_with_inconsistent_etag_in_tracker(self):
        """
        Tests resumable download with an inconsistent etag in tracker file
        """
        inconsistent_etag_tracker_file_name = (
            '%s%sinconsistent_etag_tracker' % (self.tmp_dir, os.sep))
        f = open(inconsistent_etag_tracker_file_name, 'w')
        good_etag = self.small_src_key.etag.strip('"\'')
        new_val_as_list = []
        for c in reversed(good_etag):
            new_val_as_list.append(c)
        f.write('%s\n' % ''.join(new_val_as_list))
        f.close()
        res_download_handler = ResumableDownloadHandler(
            tracker_file_name=inconsistent_etag_tracker_file_name)
        # An error should be printed about the expired tracker, but then it
        # should run the update successfully.
        self.small_src_key.get_contents_to_file(
            self.dst_fp, res_download_handler=res_download_handler)
        self.assertEqual(self.small_src_key_size,
                         get_cur_file_size(self.dst_fp))
        self.assertEqual(self.small_src_key_as_string,
                         self.small_src_key.get_contents_as_string())

    def test_download_with_unwritable_tracker_file(self):
        """
        Tests resumable download with an unwritable tracker file
        """
        # Make dir where tracker_file lives temporarily unwritable.
        save_mod = os.stat(self.tmp_dir).st_mode
        try:
            os.chmod(self.tmp_dir, 0)
            res_download_handler = ResumableDownloadHandler(
                tracker_file_name=self.tracker_file_name)
        except ResumableDownloadException, e:
            self.assertEqual(e.disposition, ResumableTransferDisposition.ABORT)
            self.assertNotEqual(
                e.message.find('Couldn\'t write URI tracker file'), -1)
        finally:
            # Restore original protection of dir where tracker_file lives.
            os.chmod(self.tmp_dir, save_mod)

if __name__ == '__main__':
    if sys.version_info[:3] < (2, 5, 1):
        sys.exit('These tests must be run on at least Python 2.5.1\n')

    # Use -d to see more HTTP protocol detail during tests. Note that
    # unlike the upload test case, you won't see much for the downloads
    # because there's no HTTP server state protocol for in the download case
    # (and the actual Range GET HTTP protocol detail is suppressed by the
    # normal boto.s3.Key.get_file() processing).
    debug = 0
    opts, args = getopt.getopt(sys.argv[1:], 'd', ['debug'])
    for o, a in opts:
      if o in ('-d', '--debug'):
        debug = 2

    test_loader = unittest.TestLoader()
    test_loader.testMethodPrefix = 'test_'
    suite = test_loader.loadTestsFromTestCase(ResumableDownloadTests)
    # Seems like there should be a cleaner way to find the test_class.
    test_class = suite.__getattribute__('_tests')[0]
    # We call set_up_class() and tear_down_class() ourselves because we
    # don't assume the user has Python 2.7 (which supports classmethods
    # that do it, with camelCase versions of these names).
    try:
        print 'Setting up %s...' % test_class.get_suite_description()
        test_class.set_up_class(debug)
        print 'Running %s...' % test_class.get_suite_description()
        unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        print 'Cleaning up after %s...' % test_class.get_suite_description()
        test_class.tear_down_class()
        print ''
