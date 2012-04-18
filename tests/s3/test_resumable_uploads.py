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
Tests of Google Cloud Storage resumable uploads.
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
from boto.exception import GSResponseError
from boto.gs.resumable_upload_handler import ResumableUploadHandler
from boto.exception import InvalidUriError
from boto.exception import ResumableTransferDisposition
from boto.exception import ResumableUploadException
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


class ResumableUploadTests(unittest.TestCase):
    """
    Resumable upload test suite.
    """

    def get_suite_description(self):
        return 'Resumable upload test suite'

    def build_test_input_file(self, size):
        buf = []
        # I manually construct the random data here instead of calling
        # os.urandom() because I want to constrain the range of data (in
        # this case to 0'..'9') so the test
        # code can easily overwrite part of the StringIO file with
        # known-to-be-different values.
        for i in range(size):
            buf.append(str(random.randint(0, 9)))
        file_as_string = ''.join(buf)
        return (file_as_string, StringIO.StringIO(file_as_string))

    def get_dst_bucket_uri(self):
        """A unique bucket to test."""
        hostname = socket.gethostname().split('.')[0]
        uri_base_str = 'gs://res-upload-test-%s-%s-%s' % (
            hostname, os.getpid(), int(time.time()))
        return boto.storage_uri('%s-dst' % uri_base_str)

    def get_dst_key_uri(self):
        """A key to test."""
        return self.dst_bucket_uri.clone_replace_name('obj')

    def get_staged_host(self):
        """URL of an existing bucket."""
        return 'pub.commondatastorage.googleapis.com'

    def get_invalid_upload_id(self):
        return (
            'http://%s/?upload_id='
            'AyzB2Uo74W4EYxyi5dp_-r68jz8rtbvshsv4TX7srJVkJ57CxTY5Dw2' % (
                self.get_staged_host()))

    def setUp(self):
        """
        Creates dst bucket and data needed by each test.
        """
        # Use a designated tmpdir prefix to make it easy to find the end of
        # the tmp path.
        self.tmpdir_prefix = 'tmp_resumable_upload_test'

        # Create test source file data.
        self.empty_src_file_size = 0
        (self.empty_src_file_as_string, self.empty_src_file) = (
            self.build_test_input_file(self.empty_src_file_size))
        self.small_src_file_size = 2 * 1024  # 2 KB.
        (self.small_src_file_as_string, self.small_src_file) = (
            self.build_test_input_file(self.small_src_file_size))
        self.larger_src_file_size = 500 * 1024  # 500 KB.
        (self.larger_src_file_as_string, self.larger_src_file) = (
            self.build_test_input_file(self.larger_src_file_size))
        self.largest_src_file_size = 1024 * 1024  # 1 MB.
        (self.largest_src_file_as_string, self.largest_src_file) = (
            self.build_test_input_file(self.largest_src_file_size))

        # Create temp dir.
        self.tmp_dir = tempfile.mkdtemp(prefix=self.tmpdir_prefix)

        # Create the test bucket.
        self.dst_bucket_uri = self.get_dst_bucket_uri()
        self.dst_bucket_uri.create_bucket()
        self.dst_key_uri = self.get_dst_key_uri()

        self.tracker_file_name = '%s%suri_tracker' % (self.tmp_dir, os.sep)

        self.syntactically_invalid_tracker_file_name = (
            '%s%ssynt_invalid_uri_tracker' % (self.tmp_dir, os.sep))
        f = open(self.syntactically_invalid_tracker_file_name, 'w')
        f.write('ftp://example.com')
        f.close()

        self.invalid_upload_id = self.get_invalid_upload_id()
        self.invalid_upload_id_tracker_file_name = (
            '%s%sinvalid_upload_id_tracker' % (self.tmp_dir, os.sep))
        f = open(self.invalid_upload_id_tracker_file_name, 'w')
        f.write(self.invalid_upload_id)
        f.close()

        self.dst_key = self.dst_key_uri.new_key(validate=False)
        self.created_test_data = True

    def tearDown(self):
        """
        Deletes any objects, files, and bucket from each test run.
        """
        if not hasattr(self, 'created_test_data'):
            return

        shutil.rmtree(self.tmp_dir)

        # Retry (for up to 2 minutes) the bucket gets deleted (it may not
        # the first time round, due to eventual consistency of bucket delete
        # operations). We also retry key deletions because if the key fails
        # to be deleted on the first attempt, it will stop us from deleting
        # the bucket.
        for i in range(60):
            try:
                self.dst_key_uri.delete_key()
            except GSResponseError, e:
                # Ignore errors attempting to delete the key, because not all
                # tests will write to the dst key.
                pass
            try:
                self.dst_bucket_uri.delete_bucket()
                break
            except StorageResponseError:
                print 'Test bucket (%s) not yet deleted, still trying' % (
                    self.dst_bucket_uri.uri)
                time.sleep(2)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self.tmp_dir = tempfile.mkdtemp(prefix=self.tmpdir_prefix)

    def test_non_resumable_upload(self):
        """
        Tests that non-resumable uploads work
        """
        # Seek to end incase its the first test.
        self.small_src_file.seek(0, os.SEEK_END)
        try:
            self.dst_key.set_contents_from_file(self.small_src_file)
            self.fail("should fail as need to rewind the filepointer")
        except AttributeError:
            pass
        # Now try calling with a proper rewind.
        self.dst_key.set_contents_from_file(self.small_src_file, rewind=True)
        self.assertEqual(self.small_src_file_size, self.dst_key.size)
        self.assertEqual(self.small_src_file_as_string,
                         self.dst_key.get_contents_as_string())

    def test_upload_without_persistent_tracker(self):
        """
        Tests a single resumable upload, with no tracker URI persistence
        """
        res_upload_handler = ResumableUploadHandler()
        self.small_src_file.seek(0)
        self.dst_key.set_contents_from_file(
            self.small_src_file, res_upload_handler=res_upload_handler)
        self.assertEqual(self.small_src_file_size, self.dst_key.size)
        self.assertEqual(self.small_src_file_as_string,
                         self.dst_key.get_contents_as_string())

    def test_failed_upload_with_persistent_tracker(self):
        """
        Tests that failed resumable upload leaves a correct tracker URI file
        """
        harnass = CallbackTestHarnass()
        res_upload_handler = ResumableUploadHandler(
            tracker_file_name=self.tracker_file_name, num_retries=0)
        self.small_src_file.seek(0)
        try:
            self.dst_key.set_contents_from_file(
                self.small_src_file, cb=harnass.call,
                res_upload_handler=res_upload_handler)
            self.fail('Did not get expected ResumableUploadException')
        except ResumableUploadException, e:
            # We'll get a ResumableUploadException at this point because
            # of CallbackTestHarnass (above). Check that the tracker file was
            # created correctly.
            self.assertEqual(e.disposition,
                             ResumableTransferDisposition.ABORT_CUR_PROCESS)
            self.assertTrue(os.path.exists(self.tracker_file_name))
            f = open(self.tracker_file_name)
            uri_from_file = f.readline().strip()
            f.close()
            self.assertEqual(uri_from_file,
                             res_upload_handler.get_tracker_uri())

    def test_retryable_exception_recovery(self):
        """
        Tests handling of a retryable exception
        """
        # Test one of the RETRYABLE_EXCEPTIONS.
        exception = ResumableUploadHandler.RETRYABLE_EXCEPTIONS[0]
        harnass = CallbackTestHarnass(exception=exception)
        res_upload_handler = ResumableUploadHandler(num_retries=1)
        self.small_src_file.seek(0)
        self.dst_key.set_contents_from_file(
            self.small_src_file, cb=harnass.call,
            res_upload_handler=res_upload_handler)
        # Ensure uploaded object has correct content.
        self.assertEqual(self.small_src_file_size, self.dst_key.size)
        self.assertEqual(self.small_src_file_as_string,
                         self.dst_key.get_contents_as_string())

    def test_broken_pipe_recovery(self):
        """
        Tests handling of a Broken Pipe (which interacts with an httplib bug)
        """
        exception = IOError(errno.EPIPE, "Broken pipe")
        harnass = CallbackTestHarnass(exception=exception)
        res_upload_handler = ResumableUploadHandler(num_retries=1)
        self.small_src_file.seek(0)
        self.dst_key.set_contents_from_file(
            self.small_src_file, cb=harnass.call,
            res_upload_handler=res_upload_handler)
        # Ensure uploaded object has correct content.
        self.assertEqual(self.small_src_file_size, self.dst_key.size)
        self.assertEqual(self.small_src_file_as_string,
                         self.dst_key.get_contents_as_string())

    def test_non_retryable_exception_handling(self):
        """
        Tests a resumable upload that fails with a non-retryable exception
        """
        harnass = CallbackTestHarnass(
            exception=OSError(errno.EACCES, 'Permission denied'))
        res_upload_handler = ResumableUploadHandler(num_retries=1)
        self.small_src_file.seek(0)
        try:
            self.dst_key.set_contents_from_file(
                self.small_src_file, cb=harnass.call,
                res_upload_handler=res_upload_handler)
            self.fail('Did not get expected OSError')
        except OSError, e:
            # Ensure the error was re-raised.
            self.assertEqual(e.errno, 13)

    def test_failed_and_restarted_upload_with_persistent_tracker(self):
        """
        Tests resumable upload that fails once and then completes, with tracker
        file
        """
        harnass = CallbackTestHarnass()
        res_upload_handler = ResumableUploadHandler(
            tracker_file_name=self.tracker_file_name, num_retries=1)
        self.small_src_file.seek(0)
        self.dst_key.set_contents_from_file(
            self.small_src_file, cb=harnass.call,
            res_upload_handler=res_upload_handler)
        # Ensure uploaded object has correct content.
        self.assertEqual(self.small_src_file_size, self.dst_key.size)
        self.assertEqual(self.small_src_file_as_string,
                         self.dst_key.get_contents_as_string())
        # Ensure tracker file deleted.
        self.assertFalse(os.path.exists(self.tracker_file_name))

    def test_multiple_in_process_failures_then_succeed(self):
        """
        Tests resumable upload that fails twice in one process, then completes
        """
        res_upload_handler = ResumableUploadHandler(num_retries=3)
        self.small_src_file.seek(0)
        self.dst_key.set_contents_from_file(
            self.small_src_file, res_upload_handler=res_upload_handler)
        # Ensure uploaded object has correct content.
        self.assertEqual(self.small_src_file_size, self.dst_key.size)
        self.assertEqual(self.small_src_file_as_string,
                         self.dst_key.get_contents_as_string())

    def test_multiple_in_process_failures_then_succeed_with_tracker_file(self):
        """
        Tests resumable upload that fails completely in one process,
        then when restarted completes, using a tracker file
        """
        # Set up test harnass that causes more failures than a single
        # ResumableUploadHandler instance will handle, writing enough data
        # before the first failure that some of it survives that process run.
        harnass = CallbackTestHarnass(
            fail_after_n_bytes=self.larger_src_file_size/2, num_times_to_fail=2)
        res_upload_handler = ResumableUploadHandler(
            tracker_file_name=self.tracker_file_name, num_retries=1)
        self.larger_src_file.seek(0)
        try:
            self.dst_key.set_contents_from_file(
                self.larger_src_file, cb=harnass.call,
                res_upload_handler=res_upload_handler)
            self.fail('Did not get expected ResumableUploadException')
        except ResumableUploadException, e:
            self.assertEqual(e.disposition,
                             ResumableTransferDisposition.ABORT_CUR_PROCESS)
            # Ensure a tracker file survived.
            self.assertTrue(os.path.exists(self.tracker_file_name))
        # Try it one more time; this time should succeed.
        self.larger_src_file.seek(0)
        self.dst_key.set_contents_from_file(
            self.larger_src_file, cb=harnass.call,
            res_upload_handler=res_upload_handler)
        self.assertEqual(self.larger_src_file_size, self.dst_key.size)
        self.assertEqual(self.larger_src_file_as_string,
                         self.dst_key.get_contents_as_string())
        self.assertFalse(os.path.exists(self.tracker_file_name))
        # Ensure some of the file was uploaded both before and after failure.
        self.assertTrue(len(harnass.transferred_seq_before_first_failure) > 1
                        and
                        len(harnass.transferred_seq_after_first_failure) > 1)

    def test_upload_with_inital_partial_upload_before_failure(self):
        """
        Tests resumable upload that successfully uploads some content
        before it fails, then restarts and completes
        """
        # Set up harnass to fail upload after several hundred KB so upload
        # server will have saved something before we retry.
        harnass = CallbackTestHarnass(
            fail_after_n_bytes=self.larger_src_file_size/2)
        res_upload_handler = ResumableUploadHandler(num_retries=1)
        self.larger_src_file.seek(0)
        self.dst_key.set_contents_from_file(
            self.larger_src_file, cb=harnass.call,
            res_upload_handler=res_upload_handler)
        # Ensure uploaded object has correct content.
        self.assertEqual(self.larger_src_file_size, self.dst_key.size)
        self.assertEqual(self.larger_src_file_as_string,
                         self.dst_key.get_contents_as_string())
        # Ensure some of the file was uploaded both before and after failure.
        self.assertTrue(len(harnass.transferred_seq_before_first_failure) > 1
                        and
                        len(harnass.transferred_seq_after_first_failure) > 1)

    def test_empty_file_upload(self):
        """
        Tests uploading an empty file (exercises boundary conditions).
        """
        res_upload_handler = ResumableUploadHandler()
        self.empty_src_file.seek(0)
        self.dst_key.set_contents_from_file(
            self.empty_src_file, res_upload_handler=res_upload_handler)
        self.assertEqual(0, self.dst_key.size)

    def test_upload_retains_metadata(self):
        """
        Tests that resumable upload correctly sets passed metadata
        """
        res_upload_handler = ResumableUploadHandler()
        headers = {'Content-Type' : 'text/plain', 'Content-Encoding' : 'gzip',
                   'x-goog-meta-abc' : 'my meta', 'x-goog-acl' : 'public-read'}
        self.small_src_file.seek(0)
        self.dst_key.set_contents_from_file(
            self.small_src_file, headers=headers,
            res_upload_handler=res_upload_handler)
        self.assertEqual(self.small_src_file_size, self.dst_key.size)
        self.assertEqual(self.small_src_file_as_string,
                         self.dst_key.get_contents_as_string())
        self.dst_key.open_read()
        self.assertEqual('text/plain', self.dst_key.content_type)
        self.assertEqual('gzip', self.dst_key.content_encoding)
        self.assertTrue('abc' in self.dst_key.metadata)
        self.assertEqual('my meta', str(self.dst_key.metadata['abc']))
        acl = self.dst_key.get_acl()
        for entry in acl.entries.entry_list:
            if str(entry.scope) == '<AllUsers>':
                self.assertEqual('READ', str(acl.entries.entry_list[1].permission))
                return
        self.fail('No <AllUsers> scope found')

    def test_upload_with_file_size_change_between_starts(self):
        """
        Tests resumable upload on a file that changes sizes between inital
        upload start and restart
        """
        harnass = CallbackTestHarnass(
            fail_after_n_bytes=self.larger_src_file_size/2)
        # Set up first process' ResumableUploadHandler not to do any
        # retries (initial upload request will establish expected size to
        # upload server).
        res_upload_handler = ResumableUploadHandler(
            tracker_file_name=self.tracker_file_name, num_retries=0)
        self.larger_src_file.seek(0)
        try:
            self.dst_key.set_contents_from_file(
                self.larger_src_file, cb=harnass.call,
                res_upload_handler=res_upload_handler)
            self.fail('Did not get expected ResumableUploadException')
        except ResumableUploadException, e:
            # First abort (from harnass-forced failure) should be
            # ABORT_CUR_PROCESS.
            self.assertEqual(e.disposition, ResumableTransferDisposition.ABORT_CUR_PROCESS)
            # Ensure a tracker file survived.
            self.assertTrue(os.path.exists(self.tracker_file_name))
        # Try it again, this time with different size source file.
        # Wait 1 second between retry attempts, to give upload server a
        # chance to save state so it can respond to changed file size with
        # 500 response in the next attempt.
        time.sleep(1)
        try:
            self.largest_src_file.seek(0)
            self.dst_key.set_contents_from_file(
                self.largest_src_file, res_upload_handler=res_upload_handler)
            self.fail('Did not get expected ResumableUploadException')
        except ResumableUploadException, e:
            # This abort should be a hard abort (file size changing during
            # transfer).
            self.assertEqual(e.disposition, ResumableTransferDisposition.ABORT)
            self.assertNotEqual(e.message.find('file size changed'), -1, e.message) 

    def test_upload_with_file_size_change_during_upload(self):
        """
        Tests resumable upload on a file that changes sizes while upload
        in progress
        """
        # Create a file we can change during the upload.
        test_file_size = 500 * 1024  # 500 KB.
        test_file = self.build_test_input_file(test_file_size)[1]
        harnass = CallbackTestHarnass(fp_to_change=test_file,
                                      fp_change_pos=test_file_size)
        res_upload_handler = ResumableUploadHandler(num_retries=1)
        try:
            self.dst_key.set_contents_from_file(
                test_file, cb=harnass.call,
                res_upload_handler=res_upload_handler)
            self.fail('Did not get expected ResumableUploadException')
        except ResumableUploadException, e:
            self.assertEqual(e.disposition, ResumableTransferDisposition.ABORT)
            self.assertNotEqual(
                e.message.find('File changed during upload'), -1)

    def test_upload_with_file_content_change_during_upload(self):
        """
        Tests resumable upload on a file that changes one byte of content
        (so, size stays the same) while upload in progress
        """
        test_file_size = 500 * 1024  # 500 KB.
        test_file = self.build_test_input_file(test_file_size)[1]
        harnass = CallbackTestHarnass(fail_after_n_bytes=test_file_size/2,
                                      fp_to_change=test_file,
                                      # Writing at file_size-5 won't change file
                                      # size because CallbackTestHarnass only
                                      # writes 3 bytes.
                                      fp_change_pos=test_file_size-5)
        res_upload_handler = ResumableUploadHandler(num_retries=1)
        try:
            self.dst_key.set_contents_from_file(
                test_file, cb=harnass.call,
                res_upload_handler=res_upload_handler)
            self.fail('Did not get expected ResumableUploadException')
        except ResumableUploadException, e:
            self.assertEqual(e.disposition, ResumableTransferDisposition.ABORT)
            # Ensure the file size didn't change.
            test_file.seek(0, os.SEEK_END)
            self.assertEqual(test_file_size, test_file.tell())
            self.assertNotEqual(
                e.message.find('md5 signature doesn\'t match etag'), -1)
            # Ensure the bad data wasn't left around.
            try:
              self.dst_key_uri.get_key()
              self.fail('Did not get expected InvalidUriError')
            except InvalidUriError, e:
              pass

    def test_upload_with_content_length_header_set(self):
        """
        Tests resumable upload on a file when the user supplies a
        Content-Length header. This is used by gsutil, for example,
        to set the content length when gzipping a file.
        """
        res_upload_handler = ResumableUploadHandler()
        self.small_src_file.seek(0)
        try:
            self.dst_key.set_contents_from_file(
                self.small_src_file, res_upload_handler=res_upload_handler,
                headers={'Content-Length' : self.small_src_file_size})
            self.fail('Did not get expected ResumableUploadException')
        except ResumableUploadException, e:
            self.assertEqual(e.disposition, ResumableTransferDisposition.ABORT)
            self.assertNotEqual(
                e.message.find('Attempt to specify Content-Length header'), -1)

    def test_upload_with_syntactically_invalid_tracker_uri(self):
        """
        Tests resumable upload with a syntactically invalid tracker URI
        """
        res_upload_handler = ResumableUploadHandler(
            tracker_file_name=self.syntactically_invalid_tracker_file_name)
        # An error should be printed about the invalid URI, but then it
        # should run the update successfully.
        self.small_src_file.seek(0)
        self.dst_key.set_contents_from_file(
            self.small_src_file, res_upload_handler=res_upload_handler)
        self.assertEqual(self.small_src_file_size, self.dst_key.size)
        self.assertEqual(self.small_src_file_as_string,
                         self.dst_key.get_contents_as_string())

    def test_upload_with_invalid_upload_id_in_tracker_file(self):
        """
        Tests resumable upload with invalid upload ID
        """
        res_upload_handler = ResumableUploadHandler(
            tracker_file_name=self.invalid_upload_id_tracker_file_name)
        # An error should occur, but then the tracker URI should be
        # regenerated and the the update should succeed.
        self.small_src_file.seek(0)
        self.dst_key.set_contents_from_file(
            self.small_src_file, res_upload_handler=res_upload_handler)
        self.assertEqual(self.small_src_file_size, self.dst_key.size)
        self.assertEqual(self.small_src_file_as_string,
                         self.dst_key.get_contents_as_string())
        self.assertNotEqual(self.invalid_upload_id,
                            res_upload_handler.get_tracker_uri())

    def test_upload_with_unwritable_tracker_file(self):
        """
        Tests resumable upload with an unwritable tracker file
        """
        # Make dir where tracker_file lives temporarily unwritable.
        save_mod = os.stat(self.tmp_dir).st_mode
        try:
            os.chmod(self.tmp_dir, 0)
            res_upload_handler = ResumableUploadHandler(
                tracker_file_name=self.tracker_file_name)
        except ResumableUploadException, e:
            self.assertEqual(e.disposition, ResumableTransferDisposition.ABORT)
            self.assertNotEqual(
                e.message.find('Couldn\'t write URI tracker file'), -1)
        finally:
            # Restore original protection of dir where tracker_file lives.
            os.chmod(self.tmp_dir, save_mod)
