# -*- coding: utf-8 -*-
# Copyright (c) 2012, Google, Inc.
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

"""Unit tests for GS versioning support."""

import time
from boto.gs import acl
from boto.gs.connection import GSConnection
from tests.integration.gs.util import has_google_credentials
from tests.unit import unittest


@unittest.skipUnless(has_google_credentials(),
                     "Google credentials are required to run the Google "
                     "Cloud Storage tests.  Update your boto.cfg to run "
                     "these tests.")
class GSVersioningTest(unittest.TestCase):
    gs = True

    def setUp(self):
        self.conn = GSConnection()
        self.buckets = []

    def tearDown(self):
        for b in self.buckets:
            bucket = self.conn.get_bucket(b)
            while len(list(bucket.list_versions())) > 0:
                for k in bucket.list_versions():
                    bucket.delete_key(k.name, generation=k.generation)
            bucket.delete()

    def _MakeBucketName(self):
        b = "boto-gs-test-%s" % repr(time.time()).replace(".", "-")
        self.buckets.append(b)
        return b

    def _MakeVersionedBucket(self):
        b = self.conn.create_bucket(self._MakeBucketName())
        b.configure_versioning(True)
        return b

    def testVersioningToggle(self):
        b = self.conn.create_bucket(self._MakeBucketName())
        self.assertFalse(b.get_versioning_status())
        b.configure_versioning(True)
        self.assertTrue(b.get_versioning_status())
        b.configure_versioning(False)
        self.assertFalse(b.get_versioning_status())

    def testDeleteVersionedKey(self):
        b = self._MakeVersionedBucket()
        k = b.new_key("foo")
        s1 = "test1"
        k.set_contents_from_string(s1)

        k = b.get_key("foo")
        g1 = k.generation

        s2 = "test2"
        k.set_contents_from_string(s2)
        k = b.get_key("foo")
        g2 = k.generation

        versions = list(b.list_versions())
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].name, "foo")
        self.assertEqual(versions[1].name, "foo")
        generations = [k.generation for k in versions]
        self.assertIn(g1, generations)
        self.assertIn(g2, generations)

        # Delete "current" version and make sure that version is no longer
        # visible from a basic GET call.
        k = b.get_key("foo")
        k.delete()
        self.assertIsNone(b.get_key("foo"))

        # Both old versions should still be there when listed using the versions
        # query parameter.
        versions = list(b.list_versions())
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0].name, "foo")
        self.assertEqual(versions[1].name, "foo")
        generations = [k.generation for k in versions]
        self.assertIn(g1, generations)
        self.assertIn(g2, generations)

        # Delete generation 2 and make sure it's gone.
        b.delete_key("foo", generation=g2)
        versions = list(b.list_versions())
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].name, "foo")
        self.assertEqual(versions[0].generation, g1)

        # Delete generation 1 and make sure it's gone.
        b.delete_key("foo", generation=g1)
        versions = list(b.list_versions())
        self.assertEqual(len(versions), 0)

    def testGetVersionedKey(self):
        b = self._MakeVersionedBucket()
        k = b.new_key("foo")
        s1 = "test1"
        k.set_contents_from_string(s1)

        k = b.get_key("foo")
        g1 = k.generation
        o1 = k.get_contents_as_string()
        self.assertEqual(o1, s1)

        s2 = "test2"
        k.set_contents_from_string(s2)
        k = b.get_key("foo")
        g2 = k.generation
        self.assertNotEqual(g2, g1)
        o2 = k.get_contents_as_string()
        self.assertEqual(o2, s2)

        k = b.get_key("foo", generation=g1)
        self.assertEqual(k.get_contents_as_string(), s1)
        k = b.get_key("foo", generation=g2)
        self.assertEqual(k.get_contents_as_string(), s2)

    def testVersionedAcl(self):
        b = self._MakeVersionedBucket()
        k = b.new_key("foo")
        s1 = "test1"
        k.set_contents_from_string(s1)

        k = b.get_key("foo")
        g1 = k.generation

        s2 = "test2"
        k.set_contents_from_string(s2)
        k = b.get_key("foo")
        g2 = k.generation

        acl1g1 = b.get_acl("foo", generation=g1)
        acl1g2 = b.get_acl("foo", generation=g2)
        owner1g1 = acl1g1.owner.id
        owner1g2 = acl1g2.owner.id
        self.assertEqual(owner1g1, owner1g2)
        entries1g1 = acl1g1.entries.entry_list
        entries1g2 = acl1g2.entries.entry_list
        self.assertEqual(len(entries1g1), len(entries1g2))

        b.set_acl("public-read", key_name="foo", generation=g1)

        acl2g1 = b.get_acl("foo", generation=g1)
        acl2g2 = b.get_acl("foo", generation=g2)
        entries2g1 = acl2g1.entries.entry_list
        entries2g2 = acl2g2.entries.entry_list
        self.assertEqual(len(entries2g2), len(entries1g2))
        public_read_entries1 = [e for e in entries2g1 if e.permission == "READ"
                                and e.scope.type == acl.ALL_USERS]
        public_read_entries2 = [e for e in entries2g2 if e.permission == "READ"
                                and e.scope.type == acl.ALL_USERS]
        self.assertEqual(len(public_read_entries1), 1)
        self.assertEqual(len(public_read_entries2), 0)

    def testCopyVersionedKey(self):
        b = self._MakeVersionedBucket()
        k = b.new_key("foo")
        s1 = "test1"
        k.set_contents_from_string(s1)

        k = b.get_key("foo")
        g1 = k.generation

        s2 = "test2"
        k.set_contents_from_string(s2)

        b2 = self._MakeVersionedBucket()
        b2.copy_key("foo2", b.name, "foo", src_generation=g1)

        k2 = b2.get_key("foo2")
        s3 = k2.get_contents_as_string()
        self.assertEqual(s3, s1)
