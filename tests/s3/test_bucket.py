# Copyright (c) 2011 Mitch Garnaat http://garnaat.org/
# All rights reserved.
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
Some unit tests for the S3 Bucket
"""

import unittest
import time
from boto.s3.connection import S3Connection

class S3BucketTest (unittest.TestCase):

    def setUp(self):
        self.conn = S3Connection()
        self.bucket_name = 'bucket-%d' % int(time.time())
        self.bucket = self.conn.create_bucket(self.bucket_name)

    def tearDown(self):
        for key in self.bucket:
            key.delete()
        self.bucket.delete()

    def test_next_marker(self):
        expected = ["a/", "b", "c"]
        for key_name in expected:
            key = self.bucket.new_key(key_name)
            key.set_contents_from_string(key_name)

        # Normal list of first 2 keys will have
        # no NextMarker set, so we use last key to iterate
        # last element will be "b" so no issue.
        rs = self.bucket.get_all_keys(max_keys=2)
        for element in rs:
            pass
        self.assertEqual(element.name, "b")
        self.assertEqual(rs.next_marker, None)

        # list using delimiter of first 2 keys will have
        # a NextMarker set (when truncated). As prefixes
        # are grouped together at the end, we get "a/" as
        # last element, but luckily we have next_marker.
        rs = self.bucket.get_all_keys(max_keys=2, delimiter="/")
        for element in rs:
            pass
        self.assertEqual(element.name, "a/")
        self.assertEqual(rs.next_marker, "b")

        # ensure bucket.list() still works by just
        # popping elements off the front of expected.
        rs = self.bucket.list()
        for element in rs:
            self.assertEqual(element.name, expected.pop(0))
        self.assertEqual(expected, [])
