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
Some unit tests for the S3 MultiDelete
"""

import unittest
import time
from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError

class S3MultiDeleteTest (unittest.TestCase):

    def test_1(self):
        print '--- running S3MultiDelete tests ---'
        c = S3Connection()
        # create a new, empty bucket
        bucket_name = 'multidelete-%d' % int(time.time())
        bucket = c.create_bucket(bucket_name)

        nkeys = 100
        
        # create a bunch of keynames
        key_names = ['key-%03d' % i for i in range(0,nkeys)]

        # create the corresponding keys
        for key_name in key_names:
            key = bucket.new_key(key_name)
            key.set_contents_from_string('this is a test')

        # now count keys in bucket
        n = 0
        for key in bucket:
            n += 1

        assert n == nkeys

        # now delete them all
        result = bucket.delete_keys(key_names)

        assert len(result.deleted) == nkeys
        assert len(result.errors) == 0
        
        time.sleep(5)
        
        # now count keys in bucket
        n = 0
        for key in bucket:
            n += 1

        assert n == 0

        # now delete bucket
        bucket.delete()
        print '--- tests completed ---'
