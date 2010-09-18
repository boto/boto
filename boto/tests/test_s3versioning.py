#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010 Mitch Garnaat http://garnaat.org/
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
Some unit tests for the S3 Versioning and MfaDelete
"""

import unittest
import time
from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError
from boto.s3.deletemarker import DeleteMarker

class S3VersionTest (unittest.TestCase):

    def test_1_versions(self):
        print '--- running S3Version tests ---'
        c = S3Connection()
        # create a new, empty bucket
        bucket_name = 'version-%d' % int(time.time())
        bucket = c.create_bucket(bucket_name)
        
        # now try a get_bucket call and see if it's really there
        bucket = c.get_bucket(bucket_name)
        
        # enable versions
        d = bucket.get_versioning_status()
        assert not d.has_key('Versioning')
        bucket.configure_versioning(versioning=True)
        time.sleep(5)
        d = bucket.get_versioning_status()
        assert d['Versioning'] == 'Enabled'
        
        # create a new key in the versioned bucket
        k = bucket.new_key()
        k.name = 'foobar'
        s1 = 'This is a test of s3 versioning'
        s2 = 'This is the second test of s3 versioning'
        k.set_contents_from_string(s1)
        time.sleep(5)
        
        # remember the version id of this object
        v1 = k.version_id
        
        # now get the contents from s3 
        o1 = k.get_contents_as_string()
        
        # check to make sure content read from s3 is identical to original
        assert o1 == s1
        
        # now overwrite that same key with new data
        k.set_contents_from_string(s2)
        v2 = k.version_id
        time.sleep(5)
        
        # now retrieve the contents as a string and compare
        s3 = k.get_contents_as_string(version_id=v2)
        assert s3 == s2
        
        # Now list all versions and compare to what we have
        rs = bucket.get_all_versions()
        assert rs[0].version_id == v2
        assert rs[1].version_id == v1
        
        # Now do a regular list command and make sure only the new key shows up
        rs = bucket.get_all_keys()
        assert len(rs) == 1
        
        # Now do regular delete
        bucket.delete_key('foobar')
        time.sleep(5)
        
        # Now list versions and make sure old versions are there
        # plus the DeleteMarker
        rs = bucket.get_all_versions()
        assert len(rs) == 3
        assert isinstance(rs[0], DeleteMarker)
        
        # Now delete v1 of the key
        bucket.delete_key('foobar', version_id=v1)
        time.sleep(5)
        
        # Now list versions again and make sure v1 is not there
        rs = bucket.get_all_versions()
        versions = [k.version_id for k in rs]
        assert v1 not in versions
        assert v2 in versions
        
        # Now try to enable MfaDelete
        mfa_sn = raw_input('MFA S/N: ')
        mfa_code = raw_input('MFA Code: ')
        bucket.configure_versioning(True, mfa_delete=True, mfa_token=(mfa_sn, mfa_code))
        i = 0
        for i in range(1,8):
            time.sleep(2**i)
            d = bucket.get_versioning_status()
            if d['Versioning'] == 'Enabled' and d['MfaDelete'] == 'Enabled':
                break
        assert d['Versioning'] == 'Enabled'
        assert d['MfaDelete'] == 'Enabled'
        
        # Now try to delete v2 without the MFA token
        try:
            bucket.delete_key('foobar', version_id=v2)
        except S3ResponseError:
            pass
        
        # Now try to delete v2 with the MFA token
        mfa_code = raw_input('MFA Code: ')
        bucket.delete_key('foobar', version_id=v2, mfa_token=(mfa_sn, mfa_code))

        # Now disable MfaDelete on the bucket
        mfa_code = raw_input('MFA Code: ')
        bucket.configure_versioning(True, mfa_delete=False, mfa_token=(mfa_sn, mfa_code))

        # Now suspend Versioning on the bucket
        bucket.configure_versioning(False)
        
        # now delete all keys and deletemarkers in bucket
        for k in bucket.list_versions():
            bucket.delete_key(k.name, version_id=k.version_id)

        # now delete bucket
        c.delete_bucket(bucket)
        print '--- tests completed ---'
