# -*- coding: utf-8 -*-

# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
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
Some unit tests for S3 Key
"""

import unittest
import time
import StringIO
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.exception import S3ResponseError

class S3KeyTest (unittest.TestCase):

    def setUp(self):
        self.conn = S3Connection()
        self.bucket_name = 'keytest-%d' % int(time.time())
        self.bucket = self.conn.create_bucket(self.bucket_name)

    def tearDown(self):
        for key in self.bucket:
            key.delete()
        self.bucket.delete()

    def test_set_contents_as_file(self):
        content="01234567890123456789"
        sfp = StringIO.StringIO(content)

        # fp is set at 0 for just opened (for read) files. 
        # set_contents should write full content to key.
        k = self.bucket.new_key("k")
        k.set_contents_from_file(sfp)
        self.assertEqual(k.size, 20)
        kn = self.bucket.new_key("k")
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, content)

        # set fp to 5 and set contents. this should
        # set "567890123456789" to the key
        sfp.seek(5)
        k = self.bucket.new_key("k")
        k.set_contents_from_file(sfp)
        self.assertEqual(k.size, 15)
        kn = self.bucket.new_key("k")
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, content[5:])

        # set fp to 5 and only set 5 bytes. this should
        # write the value "56789" to the key.
        sfp.seek(5)
        k = self.bucket.new_key("k")
        k.set_contents_from_file(sfp, size=5)
        self.assertEqual(k.size, 5)
        self.assertEqual(sfp.tell(), 10)
        kn = self.bucket.new_key("k")
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, content[5:10])

    def test_set_contents_with_md5(self):
        content="01234567890123456789"
        sfp = StringIO.StringIO(content)

        # fp is set at 0 for just opened (for read) files. 
        # set_contents should write full content to key.
        k = self.bucket.new_key("k")
        good_md5 = k.compute_md5(sfp)
        k.set_contents_from_file(sfp, md5=good_md5)
        kn = self.bucket.new_key("k")
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, content)

        # set fp to 5 and only set 5 bytes. this should
        # write the value "56789" to the key.
        sfp.seek(5)
        k = self.bucket.new_key("k")
        good_md5 = k.compute_md5(sfp, size=5)
        k.set_contents_from_file(sfp, size=5, md5=good_md5)
        self.assertEqual(sfp.tell(), 10)
        kn = self.bucket.new_key("k")
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, content[5:10])

        # let's try a wrong md5 by just altering it.
        k = self.bucket.new_key("k")
        sfp.seek(0)
        hexdig,base64 = k.compute_md5(sfp)
        bad_md5 = (hexdig, base64[3:])
        try:
            k.set_contents_from_file(sfp, md5=bad_md5)
            self.fail("should fail with bad md5")
        except S3ResponseError:
            pass

    def test_get_contents_with_md5(self):
        content="01234567890123456789"
        sfp = StringIO.StringIO(content)

        k = self.bucket.new_key("k")
        k.set_contents_from_file(sfp)
        kn = self.bucket.new_key("k")
        s = kn.get_contents_as_string()
        self.assertEqual(kn.md5, k.md5)       
        self.assertEqual(s, content)

    def test_file_callback(self):
        def callback(wrote, total):
            self.my_cb_cnt += 1
            self.assertNotEqual(wrote, self.my_cb_last, "called twice with same value")
            self.my_cb_last = wrote

        # Zero bytes written => 1 call
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.BufferSize = 2
        sfp = StringIO.StringIO("")
        k.set_contents_from_file(sfp, cb=callback, num_cb=10)
        self.assertEqual(self.my_cb_cnt, 1)
        self.assertEqual(self.my_cb_last, 0)
        sfp.close()

        # Read back zero bytes => 1 call
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback)
        self.assertEqual(self.my_cb_cnt, 1)
        self.assertEqual(self.my_cb_last, 0)

        content="01234567890123456789"
        sfp = StringIO.StringIO(content)

        # expect 2 calls due start/finish
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.set_contents_from_file(sfp, cb=callback, num_cb=10)
        self.assertEqual(self.my_cb_cnt, 2)
        self.assertEqual(self.my_cb_last, 20)

        # Read back all bytes => 2 calls
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback)
        self.assertEqual(self.my_cb_cnt, 2)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # rewind sfp and try upload again. -1 should call
        # for every read/write so that should make 11 when bs=2
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=-1)
        self.assertEqual(self.my_cb_cnt, 11)
        self.assertEqual(self.my_cb_last, 20)

        # Read back all bytes => 11 calls
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=-1)
        self.assertEqual(self.my_cb_cnt, 11)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 1 times => 2 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=1)
        self.assertTrue(self.my_cb_cnt <= 2)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 1 times => 2 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=1)
        self.assertTrue(self.my_cb_cnt <= 2)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 2 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=2)
        self.assertTrue(self.my_cb_cnt <= 2)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 2 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=2)
        self.assertTrue(self.my_cb_cnt <= 2)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 3 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=3)
        self.assertTrue(self.my_cb_cnt <= 3)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 3 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=3)
        self.assertTrue(self.my_cb_cnt <= 3)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 4 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=4)
        self.assertTrue(self.my_cb_cnt <= 4)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 4 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=4)
        self.assertTrue(self.my_cb_cnt <= 4)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 6 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=6)
        self.assertTrue(self.my_cb_cnt <= 6)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 6 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=6)
        self.assertTrue(self.my_cb_cnt <= 6)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 10 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0 
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=10)
        self.assertTrue(self.my_cb_cnt <= 10)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 10 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=10)
        self.assertTrue(self.my_cb_cnt <= 10)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 1000 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0 
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=1000)
        self.assertTrue(self.my_cb_cnt <= 1000)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 1000 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=1000)
        self.assertTrue(self.my_cb_cnt <= 1000)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)
