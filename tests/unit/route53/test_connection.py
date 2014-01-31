#!/usr/bin/env python
# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
import mock

from boto.exception import BotoServerError
from boto.route53.connection import Route53Connection
from boto.route53.exception import DNSServerError

from nose.plugins.attrib import attr
from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase


@attr(route53=True)
class TestRoute53Connection(AWSMockServiceTestCase):
    connection_class = Route53Connection

    def setUp(self):
        super(TestRoute53Connection, self).setUp()
        self.calls = {
            'count': 0,
        }

    def default_body(self):
        return """<Route53Result>
    <Message>It failed.</Message>
</Route53Result>
"""
    def test_typical_400(self):
        self.set_http_response(status_code=400, header=[
            ['Code', 'Throttling'],
        ])

        with self.assertRaises(DNSServerError) as err:
            self.service_connection.get_all_hosted_zones()

        self.assertTrue('It failed.' in str(err.exception))

    @mock.patch('time.sleep')
    def test_retryable_400(self, sleep_mock):
        self.set_http_response(status_code=400, header=[
            ['Code', 'PriorRequestNotComplete'],
        ])

        def incr_retry_handler(func):
            def _wrapper(*args, **kwargs):
                self.calls['count'] += 1
                return func(*args, **kwargs)
            return _wrapper

        # Patch.
        orig_retry = self.service_connection._retry_handler
        self.service_connection._retry_handler = incr_retry_handler(
            orig_retry
        )
        self.assertEqual(self.calls['count'], 0)

        # Retries get exhausted.
        with self.assertRaises(BotoServerError):
            self.service_connection.get_all_hosted_zones()

        self.assertEqual(self.calls['count'], 7)

        # Unpatch.
        self.service_connection._retry_handler = orig_retry
