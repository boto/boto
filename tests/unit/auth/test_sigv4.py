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
