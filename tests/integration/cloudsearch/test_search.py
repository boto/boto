# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.
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
Tests for Search of Cloudsearch
"""
import mock
import requests
import time

from tests.unit import unittest
from boto.cloudsearch.search import SearchConnection, SearchServiceException

try:
    import json
except ImportError:
    import simplejson as json


class FakeResponse(object):
    status_code = 405
    content = ''


class CloudSearchConnectionTest(unittest.TestCase):
    cloudsearch = True

    def setUp(self):
        super(CloudSearchConnectionTest, self).setUp()
        self.conn = SearchConnection(
            endpoint='test-domain.cloudsearch.amazonaws.com'
        )

    def test_expose_additional_error_info(self):
        mpo = mock.patch.object
        fake = FakeResponse()
        fake.content = 'Nopenopenope'

        # First, in the case of a non-JSON, non-403 error.
        with mpo(requests, 'get', return_value=fake) as mock_request:
            with self.assertRaises(SearchServiceException) as cm:
                self.conn.search(q='not_gonna_happen')

            self.assertTrue('non-json response' in str(cm.exception))
            self.assertTrue('Nopenopenope' in str(cm.exception))

        # Then with JSON & an 'error' key within.
        fake.content = json.dumps({
            'error': "Something went wrong. Oops."
        })

        with mpo(requests, 'get', return_value=fake) as mock_request:
            with self.assertRaises(SearchServiceException) as cm:
                self.conn.search(q='no_luck_here')

            self.assertTrue('Unknown error' in str(cm.exception))
            self.assertTrue('went wrong. Oops' in str(cm.exception))

