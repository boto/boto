#!/usr/bin/env python

# Copyright (c) 2006 Mitch Garnaat http://garnaat.org/
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
Some unit tests for the S3Connection
"""

import unittest
import time
import os
from boto.connection import S3Connection
from boto.key import Key

class S3ConnectionTest (unittest.TestCase):

    def test_1_basic(self):
        print '--- running S3Connection tests ---'
        c = S3Connection()
        # create a new, empty bucket
        bucket_name = 'test-%d' % int(time.time())
        bucket = c.create_bucket(bucket_name)
        # create a new key and store it's content from a string
        k = Key(bucket)
        k.key = 'foobar'
        s = 'This is a test of file upload and download'
        k.set_contents_from_string(s)
        fp = open('foobar', 'wb')
        # now get the contents from s3 to a local file
        k.get_contents_to_file(fp)
        fp.close()
        fp = open('foobar')
        # check to make sure content read from s3 is identical to original
        assert s == fp.read(), 'corrupted file'
        fp.close()
        bucket.delete_key(k)
        os.unlink('foobar')
        # test a few variations on get_all_keys - first load some data
        k.key = 'foo/bar'
        k.set_contents_from_string(s)
        k.key = 'foo/bas'
        k.set_contents_from_string(s)
        k.key = 'foo/bat'
        k.set_contents_from_string(s)
        k.key = 'fie/bar'
        k.set_contents_from_string(s)
        k.key = 'fie/bas'
        k.set_contents_from_string(s)
        k.key = 'fie/bat'
        k.set_contents_from_string(s)
        all = bucket.get_all_keys()
        assert len(all) == 6
        rs = bucket.get_all_keys(prefix='foo')
        assert len(rs) == 3
        rs = bucket.get_all_keys(maxkeys=5)
        assert len(rs) == 5
        # test the lookup method
        k = bucket.lookup('foo/bar')
        assert isinstance(k, Key)
        k = bucket.lookup('notthere')
        assert k == None
        for k in all:
            bucket.delete_key(k)
        # now delete bucket
        c.delete_bucket(bucket)
        print '--- tests completed ---'
