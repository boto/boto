# Copyright 2013 Google Inc.
# Copyright 2011, Nexenta Systems Inc.
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

import cStringIO
import gzip
import os
import unittest
from boto.s3.keyfile import KeyFile
from tests.integration.s3.mock_storage_service import MockConnection
from tests.integration.s3.mock_storage_service import MockBucket


class KeyfileTest(unittest.TestCase):

    def setUp(self):
        service_connection = MockConnection()
        self.contents = '0123456789'
        bucket = MockBucket(service_connection, 'mybucket')
        key = bucket.new_key('mykey')
        key.set_contents_from_string(self.contents)
        self.keyfile = KeyFile(key)

    def tearDown(self):
        self.keyfile.close()

    def testReadFull(self):
        self.assertEqual(self.keyfile.read(len(self.contents)), self.contents)

    def testReadPartial(self):
        self.assertEqual(self.keyfile.read(5), self.contents[:5])
        self.assertEqual(self.keyfile.read(5), self.contents[5:])

    def testTell(self):
        self.assertEqual(self.keyfile.tell(), 0)
        self.keyfile.read(4)
        self.assertEqual(self.keyfile.tell(), 4)
        self.keyfile.read(6)
        self.assertEqual(self.keyfile.tell(), 10)
        self.keyfile.close()
        try:
            self.keyfile.tell()
        except ValueError as e:
            self.assertEqual(str(e), 'I/O operation on closed file')

    def testSeek(self):
        self.assertEqual(self.keyfile.read(4), self.contents[:4])
        self.keyfile.seek(0)
        self.assertEqual(self.keyfile.read(4), self.contents[:4])
        self.keyfile.seek(5)
        self.assertEqual(self.keyfile.read(5), self.contents[5:])

        # Seeking negative should raise.
        try:
            self.keyfile.seek(-5)
        except IOError as e:
            self.assertEqual(str(e), 'Invalid argument')

        # Reading past end of file is supposed to return empty string.
        self.keyfile.read(10)
        self.assertEqual(self.keyfile.read(20), '')

        # Seeking past end of file is supposed to silently work.
        self.keyfile.seek(50)
        self.assertEqual(self.keyfile.tell(), 50)
        self.assertEqual(self.keyfile.read(1), '')

    def testReadEnd(self):
        """Tests read behavior at the end of a file. If we read with a larger
        buffer size, we should end up with a location that's actually at the
        end of the file.
        """
        self.keyfile.seek(5)
        read = self.keyfile.read(len(self.contents))
        self.assertTrue(len(read) < len(self.contents))
        self.assertEqual(self.keyfile.tell(), len(self.contents))
        self.assertEqual(len(self.contents), self.keyfile.key.size)

    def testSeekEnd(self):
        self.assertEqual(self.keyfile.read(4), self.contents[:4])
        self.keyfile.seek(0, os.SEEK_END)
        self.assertEqual(self.keyfile.read(1), '')
        self.keyfile.seek(-1, os.SEEK_END)
        self.assertEqual(self.keyfile.tell(), 9)
        self.assertEqual(self.keyfile.read(1), '9')
        # Test attempt to seek backwards past the start from the end.
        try:
            self.keyfile.seek(-100, os.SEEK_END)
        except IOError as e:
            self.assertEqual(str(e), 'Invalid argument')

    def testSeekCur(self):
        self.assertEqual(self.keyfile.read(1), self.contents[0])
        self.keyfile.seek(1, os.SEEK_CUR)
        self.assertEqual(self.keyfile.tell(), 2)
        self.assertEqual(self.keyfile.read(4), self.contents[2:6])

    def testSetEtag(self):
        # Make sure both bytes and strings work as contents. This is one of the
        # very few places Boto uses the mock key object.
        # https://github.com/GoogleCloudPlatform/gsutil/issues/214#issuecomment-49906044
        self.keyfile.key.data = b'test'
        self.keyfile.key.set_etag()
        self.assertEqual(self.keyfile.key.etag, '098f6bcd4621d373cade4e832627b4f6')

        self.keyfile.key.etag = None
        self.keyfile.key.data = 'test'
        self.keyfile.key.set_etag()
        self.assertEqual(self.keyfile.key.etag, '098f6bcd4621d373cade4e832627b4f6')


# NOTE: Even though gzip is zlib compatible, they write slightly
# different formats. So, we're doing this instead of zlib.compress()
def get_gzip_compressed(uncompressed):
    fd = cStringIO.StringIO()
    z_fd = gzip.GzipFile(fileobj=fd, mode='w')
    z_fd.write(uncompressed)
    z_fd.close()
    return fd.getvalue()


class KeyfileGzipCompatibleTest(unittest.TestCase):
    """
    Mini [shouldn't be slow] integration test to test gzip compatibility.
    """

    def setUp(self):
        service_connection = MockConnection()
        self.uncompressed_contents = '0123456789'
        self.compressed_contents = get_gzip_compressed(self.uncompressed_contents)
        bucket = MockBucket(service_connection, 'mybucket')
        key = bucket.new_key('mykey')
        key.set_contents_from_string(self.compressed_contents)
        self.keyfile = KeyFile(key)

    def testGzipCompatible(self):
        z_fd = gzip.GzipFile(fileobj=self.keyfile, mode='r')
        contents = z_fd.read()
        self.assertEqual(contents, self.uncompressed_contents)
