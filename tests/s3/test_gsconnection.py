# -*- coding: utf-8 -*-
# Copyright (c) 2006-2011 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010, Eucalyptus Systems, Inc.
# Copyright (c) 2011, Nexenta Systems, Inc.
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
import re
from boto.gs.connection import GSConnection
from boto import storage_uri

class GSConnectionTest (unittest.TestCase):

    def test_1_basic(self):
        """basic regression test for Google Cloud Storage"""
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
        # Test for stream API
        fp2 = open('foobar', 'rb')
        k.md5 = None
        k.base64md5 = None
        k.set_contents_from_stream(fp2, headers=headers)
        fp = open('foobar1', 'wb')
        k.get_contents_to_file(fp)
        fp.close()
        fp2.seek(0,0)
        fp = open('foobar1', 'rb')
        assert (fp2.read() == fp.read()), 'Chunked Transfer corrupted the Data'
        fp.close()
        fp2.close()
        os.unlink('foobar1')
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
        # try set/get raw logging subresource
        empty_logging_str="<?xml version='1.0' encoding='UTF-8'?><Logging/>"
        logging_str = (
            "<?xml version='1.0' encoding='UTF-8'?><Logging>"
            "<LogBucket>log-bucket</LogBucket>" +
            "<LogObjectPrefix>example</LogObjectPrefix>" +
            "</Logging>")
        bucket.set_subresource('logging', logging_str);
        assert bucket.get_subresource('logging') == logging_str;
        # try disable/enable logging
        bucket.disable_logging()
        assert bucket.get_subresource('logging') == empty_logging_str
        bucket.enable_logging('log-bucket', 'example')
        assert bucket.get_subresource('logging') == logging_str;
        # now delete all keys in bucket
        for k in bucket:
            bucket.delete_key(k)
        # now delete bucket
        time.sleep(5)
        c.delete_bucket(bucket)

    def test_2_copy_key(self):
        """test copying a key from one bucket to another"""
        c = GSConnection()
        # create two new, empty buckets
        bucket_name_1 = 'test1-%d' % int(time.time())
        bucket_name_2 = 'test2-%d' % int(time.time())
        bucket1 = c.create_bucket(bucket_name_1)
        bucket2 = c.create_bucket(bucket_name_2)
        # verify buckets got created 
        bucket1 = c.get_bucket(bucket_name_1)
        bucket2 = c.get_bucket(bucket_name_2)
        # create a key in bucket1 and give it some content
        k1 = bucket1.new_key()
        assert isinstance(k1, bucket1.key_class)
        key_name = 'foobar'
        k1.name = key_name
        s = 'This is a test.'
        k1.set_contents_from_string(s)
        # copy the new key from bucket1 to bucket2
        k1.copy(bucket_name_2, key_name) 
        # now copy the contents from bucket2 to a local file
        k2 = bucket2.lookup(key_name)
        assert isinstance(k2, bucket2.key_class)
        fp = open('foobar', 'wb')
        k2.get_contents_to_file(fp)
        fp.close()
        fp = open('foobar')
        # check to make sure content read is identical to original
        assert s == fp.read(), 'move test failed!'
        fp.close()
        # delete keys
        bucket1.delete_key(k1)
        bucket2.delete_key(k2)
        # delete test buckets
        c.delete_bucket(bucket1)
        c.delete_bucket(bucket2)

    def test_3_default_object_acls(self):
        """test default object acls"""
        # regexp for matching project-private default object ACL
        project_private_re = '\s*<AccessControlList>\s*<Entries>\s*<Entry>' \
          '\s*<Scope type="GroupById"><ID>[0-9a-fA-F]+</ID></Scope>'        \
          '\s*<Permission>FULL_CONTROL</Permission>\s*</Entry>\s*<Entry>'   \
          '\s*<Scope type="GroupById"><ID>[0-9a-fA-F]+</ID></Scope>'        \
          '\s*<Permission>FULL_CONTROL</Permission>\s*</Entry>\s*<Entry>'   \
          '\s*<Scope type="GroupById"><ID>[0-9a-fA-F]+</ID></Scope>'        \
          '\s*<Permission>READ</Permission></Entry>\s*</Entries>'           \
          '\s*</AccessControlList>\s*'
        c = GSConnection()
        # create a new bucket
        bucket_name = 'test-%d' % int(time.time())
        bucket = c.create_bucket(bucket_name)
        # now call get_bucket to see if it's really there
        bucket = c.get_bucket(bucket_name)
        # get default acl and make sure it's project-private
        acl = bucket.get_def_acl()
        assert re.search(project_private_re, acl.to_xml())
        # set default acl to a canned acl and verify it gets set
        bucket.set_def_acl('public-read')
        acl = bucket.get_def_acl()
        # save public-read acl for later test
        public_read_acl = acl
        assert acl.to_xml() == ('<AccessControlList><Entries><Entry>'    +
          '<Scope type="AllUsers"></Scope><Permission>READ</Permission>' +
          '</Entry></Entries></AccessControlList>')
        # back to private acl
        bucket.set_def_acl('private')
        acl = bucket.get_def_acl()
        assert acl.to_xml() == '<AccessControlList></AccessControlList>'
        # set default acl to an xml acl and verify it gets set
        bucket.set_def_acl(public_read_acl)
        acl = bucket.get_def_acl()
        assert acl.to_xml() == ('<AccessControlList><Entries><Entry>'    +
          '<Scope type="AllUsers"></Scope><Permission>READ</Permission>' +
          '</Entry></Entries></AccessControlList>')
        # back to private acl
        bucket.set_def_acl('private')
        acl = bucket.get_def_acl()
        assert acl.to_xml() == '<AccessControlList></AccessControlList>'
        # delete bucket
        c.delete_bucket(bucket)
        # repeat default acl tests using boto's storage_uri interface
        # create a new bucket
        bucket_name = 'test-%d' % int(time.time())
        uri = storage_uri('gs://' + bucket_name)
        uri.create_bucket()
        # get default acl and make sure it's project-private
        acl = uri.get_def_acl()
        assert re.search(project_private_re, acl.to_xml())
        # set default acl to a canned acl and verify it gets set
        uri.set_def_acl('public-read')
        acl = uri.get_def_acl()
        # save public-read acl for later test
        public_read_acl = acl
        assert acl.to_xml() == ('<AccessControlList><Entries><Entry>'    +
          '<Scope type="AllUsers"></Scope><Permission>READ</Permission>' +
          '</Entry></Entries></AccessControlList>')
        # back to private acl
        uri.set_def_acl('private')
        acl = uri.get_def_acl()
        assert acl.to_xml() == '<AccessControlList></AccessControlList>'
        # set default acl to an xml acl and verify it gets set
        uri.set_def_acl(public_read_acl)
        acl = uri.get_def_acl()
        assert acl.to_xml() == ('<AccessControlList><Entries><Entry>'    +
          '<Scope type="AllUsers"></Scope><Permission>READ</Permission>' +
          '</Entry></Entries></AccessControlList>')
        # back to private acl
        uri.set_def_acl('private')
        acl = uri.get_def_acl()
        assert acl.to_xml() == '<AccessControlList></AccessControlList>'
        # delete bucket
        uri.delete_bucket()
        
        print '--- tests completed ---'
