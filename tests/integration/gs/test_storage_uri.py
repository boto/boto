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

import time
from boto import storage_uri
from boto.gs.connection import GSConnection
from boto.gs.key import Key
from tests.integration.gs.util import has_google_credentials
from tests.unit import unittest


@unittest.skipUnless(has_google_credentials(),
                     "Google credentials are required to run the Google "
                     "Cloud Storage tests.  Update your boto.cfg to run "
                     "these tests.")
class GSStorageUriTest(unittest.TestCase):
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

    def testHasVersion(self):
        uri = storage_uri("gs://bucket/obj")
        self.assertFalse(uri.has_version())
        uri.version_id = "versionid"
        self.assertTrue(uri.has_version())

        uri = storage_uri("gs://bucket/obj")
        # Generation triggers versioning.
        uri.generation = 12345
        self.assertTrue(uri.has_version())
        # Meta-generation is permitted.
        uri.meta_generation = 1
        self.assertTrue(uri.has_version())
        # Meta-generation is insufficient for versioning.
        uri.generation = None
        self.assertFalse(uri.has_version())

        # Zero-generation counts as a version.
        uri = storage_uri("gs://bucket/obj")
        uri.generation = 0
        self.assertTrue(uri.has_version())

    def testVersionUriStr(self):
        uri_str = "gs://bucket/obj"
        uri = storage_uri(uri_str)
        uri.version_id = "versionid"
        self.assertEquals(uri_str + "#versionid", uri.versioned_uri_str())

        uri = storage_uri(uri_str)
        self.assertEquals(uri_str, uri.versioned_uri_str())

        uri.generation = 12345
        self.assertEquals(uri_str + "#12345", uri.versioned_uri_str())
        uri.generation = 0
        self.assertEquals(uri_str + "#0", uri.versioned_uri_str())

        uri.meta_generation = 1
        self.assertEquals(uri_str + "#0.1", uri.versioned_uri_str())
        uri.meta_generation = 0
        self.assertEquals(uri_str + "#0.0", uri.versioned_uri_str())

    def testCloneReplaceKey(self):
        b = self.conn.create_bucket(self._MakeBucketName())
        k = b.new_key("obj")
        k.set_contents_from_string("stringdata")

        orig_uri = storage_uri("gs://%s/" % b.name)

        uri = orig_uri.clone_replace_key(k)
        self.assertTrue(uri.has_version())
        self.assertRegexpMatches(str(uri.generation), r'[0-9]+')
        self.assertEquals(uri.meta_generation, 1)
