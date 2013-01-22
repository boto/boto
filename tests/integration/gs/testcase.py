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

"""Base TestCase class for gs integration tests."""

import time

from boto.exception import GSResponseError
from boto.gs.connection import GSConnection
from tests.integration.gs.util import has_google_credentials
from tests.integration.gs.util import retry
from tests.unit import unittest

@unittest.skipUnless(has_google_credentials(),
                     "Google credentials are required to run the Google "
                     "Cloud Storage tests.  Update your boto.cfg to run "
                     "these tests.")
class GSTestCase(unittest.TestCase):
    gs = True

    def setUp(self):
        self.conn = GSConnection()
        self.buckets = []

    # Retry with an exponential backoff if a server error is received. This
    # ensures that we try *really* hard to clean up after ourselves.
    @retry(GSResponseError)
    def tearDown(self):
        while(len(self.buckets)):
            b = self.buckets[-1]
            bucket = self.conn.get_bucket(b)
            while len(list(bucket.list_versions())) > 0:
                for k in bucket.list_versions():
                    bucket.delete_key(k.name, generation=k.generation)
            bucket.delete()
            self.buckets.pop()

    def _MakeBucketName(self):
        b = "boto-gs-test-%s" % repr(time.time()).replace(".", "-")
        self.buckets.append(b)
        return b

    def _MakeBucket(self):
        b = self.conn.create_bucket(self._MakeBucketName())
        return b

    def _MakeVersionedBucket(self):
        b = self._MakeBucket()
        b.configure_versioning(True)
        return b
