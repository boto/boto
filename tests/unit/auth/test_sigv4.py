# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
#
from mock import Mock
from tests.unit import unittest

from boto.auth import HmacAuthV4Handler
from boto.connection import HTTPRequest


class TestSigV4Handler(unittest.TestCase):
    def setUp(self):
        self.provider = Mock()
        self.provider.access_key = 'access_key'
        self.provider.secret_key = 'secret_key'
        self.request = HTTPRequest(
            'POST', 'https', 'glacier.us-east-1.amazonaws.com', 443,
            '/-/vaults/foo/archives', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')

    def test_inner_whitespace_is_collapsed(self):
        auth = HmacAuthV4Handler('glacier.us-east-1.amazonaws.com',
                                 Mock(), self.provider)
        self.request.headers['x-amz-archive-description'] = 'two  spaces'
        headers = auth.headers_to_sign(self.request)
        self.assertEqual(headers, {'Host': 'glacier.us-east-1.amazonaws.com',
                                   'x-amz-archive-description': 'two  spaces',
                                   'x-amz-glacier-version': '2012-06-01'})
        # Note the single space between the "two spaces".
        self.assertEqual(auth.canonical_headers(headers),
                         'host:glacier.us-east-1.amazonaws.com\n'
                         'x-amz-archive-description:two spaces\n'
                         'x-amz-glacier-version:2012-06-01')

    def test_canonical_query_string(self):
        auth = HmacAuthV4Handler('glacier.us-east-1.amazonaws.com',
                                 Mock(), self.provider)
        request = HTTPRequest(
            'GET', 'https', 'glacier.us-east-1.amazonaws.com', 443,
            '/-/vaults/foo/archives', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')
        request.params['Foo.1'] = 'aaa'
        request.params['Foo.10'] = 'zzz'
        query_string = auth.canonical_query_string(request)
        self.assertEqual(query_string, 'Foo.1=aaa&Foo.10=zzz')

    def test_canonical_uri(self):
        auth = HmacAuthV4Handler('glacier.us-east-1.amazonaws.com',
                                 Mock(), self.provider)
        request = HTTPRequest(
            'GET', 'https', 'glacier.us-east-1.amazonaws.com', 443,
            'x/./././x .html', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')
        canonical_uri = auth.canonical_uri(request)
        # This should be both normalized & urlencoded.
        self.assertEqual(canonical_uri, 'x/x%20.html')

    def test_region_and_service_can_be_overriden(self):
        auth = HmacAuthV4Handler('queue.amazonaws.com',
                                 Mock(), self.provider)
        self.request.headers['X-Amz-Date'] = '20121121000000'

        auth.region_name = 'us-west-2'
        auth.service_name = 'sqs'
        scope = auth.credential_scope(self.request)
        self.assertEqual(scope, '20121121/us-west-2/sqs/aws4_request')
