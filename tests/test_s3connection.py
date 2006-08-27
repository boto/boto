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
import StringIO
from boto.connection import S3Connection
from boto.key import Key

class S3ConnectionTest (unittest.TestCase):

    def test_1_basic(self):
        print '--- running S3Connection tests ---'
        c = S3Connection()
        #c.set_debug(1)
        bucket_name = 'test-%d' % int(time.time())
        bucket = c.create_bucket(bucket_name)
        k = Key(bucket)
        k.key = 'foobar'
        s = 'This is a test of file upload and download'
        fp = StringIO.StringIO(s)
        k.set_contents_from_file(fp)
        fp = open('foobar', 'wb')
        k.get_contents_to_file(fp)
        fp.close()
        fp = open('foobar')
        assert s == fp.read(), 'corrupted file'
        fp.close()
        bucket.delete_contents(k)
        c.delete_bucket(bucket)
        print '--- tests completed ---'
