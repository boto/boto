#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2006-2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010, Eucalyptus Systems, Inc.
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
Some unit tests for the GSConnection
"""

import unittest
import time
import os
from boto.gs.connection import GSConnection

class GSConnectionTest (unittest.TestCase):

    def test_1_basic(self):
        print '--- running GSConnection tests ---'
        c = GSConnection()
        # create a new, empty bucket
        bucket_name = 'test-%d' % int(time.time())
        bucket = c.create_bucket(bucket_name)
        # now try a get_bucket call and see if it's really there
        bucket = c.get_bucket(bucket_name)
        k = bucket.new_key()
        k.name = 'foobar'
        s1 = 'This is a test of file upload and download'
        s2 = 'This is a second string to test file upload and download'
        k.set_contents_from_string(s1)
        fp = open('foobar', 'wb')
        # now get the contents from s3 to a local file
        k.get_contents_to_file(fp)
        fp.close()
        fp = open('foobar')
        # check to make sure content read from s3 is identical to original
        assert s1 == fp.read(), 'corrupted file'
        fp.close()
        bucket.delete_key(k)
        # test a few variations on get_all_keys - first load some data
        # for the first one, let's override the content type
        phony_mimetype = 'application/x-boto-test'
        headers = {'Content-Type': phony_mimetype}
        k.name = 'foo/bar'
        k.set_contents_from_string(s1, headers)
        k.name = 'foo/bas'
        k.set_contents_from_filename('foobar')
        k.name = 'foo/bat'
        k.set_contents_from_string(s1)
        k.name = 'fie/bar'
        k.set_contents_from_string(s1)
        k.name = 'fie/bas'
        k.set_contents_from_string(s1)
        k.name = 'fie/bat'
        k.set_contents_from_string(s1)
        # try resetting the contents to another value
        md5 = k.md5
        k.set_contents_from_string(s2)
        assert k.md5 != md5
        os.unlink('foobar')
        all = bucket.get_all_keys()
        assert len(all) == 6
        rs = bucket.get_all_keys(prefix='foo')
        assert len(rs) == 3
        rs = bucket.get_all_keys(prefix='', delimiter='/')
        assert len(rs) == 2
        rs = bucket.get_all_keys(maxkeys=5)
        assert len(rs) == 5
        # test the lookup method
        k = bucket.lookup('foo/bar')
        assert isinstance(k, bucket.key_class)
        assert k.content_type == phony_mimetype
        k = bucket.lookup('notthere')
        assert k == None
        # try some metadata stuff
        k = bucket.new_key()
        k.name = 'has_metadata'
        mdkey1 = 'meta1'
        mdval1 = 'This is the first metadata value'
        k.set_metadata(mdkey1, mdval1)
        mdkey2 = 'meta2'
        mdval2 = 'This is the second metadata value'
        k.set_metadata(mdkey2, mdval2)
        # try a unicode metadata value
        
        mdval3 = u'föö'
        mdkey3 = 'meta3'
        k.set_metadata(mdkey3, mdval3)
        k.set_contents_from_string(s1)
        
        k = bucket.lookup('has_metadata')
        assert k.get_metadata(mdkey1) == mdval1
        assert k.get_metadata(mdkey2) == mdval2
        assert k.get_metadata(mdkey3) == mdval3
        k = bucket.new_key()
        k.name = 'has_metadata'
        k.get_contents_as_string()
        assert k.get_metadata(mdkey1) == mdval1
        assert k.get_metadata(mdkey2) == mdval2
        assert k.get_metadata(mdkey3) == mdval3
        bucket.delete_key(k)
        # test list and iterator
        rs1 = bucket.list()
        num_iter = 0
        for r in rs1:
            num_iter = num_iter + 1
        rs = bucket.get_all_keys()
        num_keys = len(rs)
        assert num_iter == num_keys
        # try some acl stuff
        bucket.set_acl('public-read')
        acl = bucket.get_acl()
        assert len(acl.entries.entry_list) == 2
        bucket.set_acl('private')
        acl = bucket.get_acl()
        assert len(acl.entries.entry_list) == 1
        k = bucket.lookup('foo/bar')
        k.set_acl('public-read')
        acl = k.get_acl()
        assert len(acl.entries.entry_list) == 2
        k.set_acl('private')
        acl = k.get_acl()
        assert len(acl.entries.entry_list) == 1
        # now delete all keys in bucket
        for k in bucket:
            bucket.delete_key(k)
        # now delete bucket
        time.sleep(5)
        c.delete_bucket(bucket)
        print '--- tests completed ---'
