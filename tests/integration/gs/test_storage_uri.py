# -*- coding: utf-8 -*-
# Copyright (c) 2013, Google, Inc.
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

"""Unit tests for StorageUri interface."""

import re
import StringIO

from boto import storage_uri
from boto.gs.acl import SupportedPermissions as perms
from tests.integration.gs.testcase import GSTestCase


class GSStorageUriTest(GSTestCase):

    def testHasVersion(self):
        uri = storage_uri("gs://bucket/obj")
        self.assertFalse(uri.has_version())
        uri.version_id = "versionid"
        self.assertTrue(uri.has_version())

        uri = storage_uri("gs://bucket/obj")
        # Generation triggers versioning.
        uri.generation = 12345
        self.assertTrue(uri.has_version())
        uri.generation = None
        self.assertFalse(uri.has_version())

        # Zero-generation counts as a version.
        uri = storage_uri("gs://bucket/obj")
        uri.generation = 0
        self.assertTrue(uri.has_version())

    def testCloneReplaceKey(self):
        b = self._MakeBucket()
        k = b.new_key("obj")
        k.set_contents_from_string("stringdata")

        orig_uri = storage_uri("gs://%s/" % b.name)

        uri = orig_uri.clone_replace_key(k)
        self.assertTrue(uri.has_version())
        self.assertRegexpMatches(str(uri.generation), r"[0-9]+")

    def testSetAclXml(self):
        """Ensures that calls to the set_xml_acl functions succeed."""
        b = self._MakeBucket()
        k = b.new_key("obj")
        k.set_contents_from_string("stringdata")
        bucket_uri = storage_uri("gs://%s/" % b.name)

        # Get a valid ACL for an object.
        bucket_uri.object_name = "obj"
        bucket_acl = bucket_uri.get_acl()
        bucket_uri.object_name = None

        # Add a permission to the ACL.
        all_users_read_permission = ("<Entry><Scope type='AllUsers'/>"
                                     "<Permission>READ</Permission></Entry>")
        acl_string = re.sub(r"</Entries>",
                           all_users_read_permission + "</Entries>",
                           bucket_acl.to_xml())        

        # Test-generated owner IDs are not currently valid for buckets
        acl_no_owner_string = re.sub(r"<Owner>.*</Owner>", "", acl_string)

        # Set ACL on an object.
        bucket_uri.set_xml_acl(acl_string, "obj")
        # Set ACL on a bucket.
        bucket_uri.set_xml_acl(acl_no_owner_string)
        # Set the default ACL for a bucket.
        bucket_uri.set_def_xml_acl(acl_no_owner_string)

        # Verify all the ACLs were successfully applied.
        new_obj_acl_string = k.get_acl().to_xml()
        new_bucket_acl_string = bucket_uri.get_acl().to_xml()
        new_bucket_def_acl_string = bucket_uri.get_def_acl().to_xml()
        self.assertRegexpMatches(new_obj_acl_string, r"AllUsers")
        self.assertRegexpMatches(new_bucket_acl_string, r"AllUsers")
        self.assertRegexpMatches(new_bucket_def_acl_string, r"AllUsers")

    def testPropertiesUpdated(self):
        b = self._MakeBucket()
        bucket_uri = storage_uri("gs://%s" % b.name)
        key_uri = bucket_uri.clone_replace_name("obj")
        key_uri.set_contents_from_string("data1")

        self.assertRegexpMatches(str(key_uri.generation), r"[0-9]+")
        k = b.get_key("obj")
        self.assertEqual(k.generation, key_uri.generation)
        self.assertEquals(k.get_contents_as_string(), "data1")

        key_uri.set_contents_from_stream(StringIO.StringIO("data2"))
        self.assertRegexpMatches(str(key_uri.generation), r"[0-9]+")
        self.assertGreater(key_uri.generation, k.generation)
        k = b.get_key("obj")
        self.assertEqual(k.generation, key_uri.generation)
        self.assertEquals(k.get_contents_as_string(), "data2")

        key_uri.set_contents_from_file(StringIO.StringIO("data3"))
        self.assertRegexpMatches(str(key_uri.generation), r"[0-9]+")
        self.assertGreater(key_uri.generation, k.generation)
        k = b.get_key("obj")
        self.assertEqual(k.generation, key_uri.generation)
        self.assertEquals(k.get_contents_as_string(), "data3")
