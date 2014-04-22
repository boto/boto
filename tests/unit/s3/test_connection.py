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
from mock import patch
import time

from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase
from tests.unit import MockServiceWithConfigTestCase

from boto.s3.connection import S3Connection, HostRequiredError
from boto.s3.connection import S3ResponseError, Bucket


class TestSignatureAlteration(AWSMockServiceTestCase):
    connection_class = S3Connection

    def test_unchanged(self):
        self.assertEqual(
            self.service_connection._required_auth_capability(),
            ['s3']
        )

    def test_switched(self):
        conn = self.connection_class(
            aws_access_key_id='less',
            aws_secret_access_key='more',
            host='s3.cn-north-1.amazonaws.com.cn'
        )
        self.assertEqual(
            conn._required_auth_capability(),
            ['hmac-v4-s3']
        )


class TestSigV4HostError(MockServiceWithConfigTestCase):
    connection_class = S3Connection

    def test_historical_behavior(self):
        self.assertEqual(
            self.service_connection._required_auth_capability(),
            ['s3']
        )
        self.assertEqual(self.service_connection.host, 's3.amazonaws.com')

    def test_sigv4_opt_in(self):
        # Switch it at the config, so we can check to see how the host is
        # handled.
        self.config = {
            's3': {
                'use-sigv4': True,
            }
        }

        with self.assertRaises(HostRequiredError):
            # No host+SigV4 == KABOOM
            self.connection_class(
                aws_access_key_id='less',
                aws_secret_access_key='more'
            )

        # Ensure passing a ``host`` still works.
        conn = self.connection_class(
            aws_access_key_id='less',
            aws_secret_access_key='more',
            host='s3.cn-north-1.amazonaws.com.cn'
        )
        self.assertEqual(
            conn._required_auth_capability(),
            ['hmac-v4-s3']
        )
        self.assertEqual(
            conn.host,
            's3.cn-north-1.amazonaws.com.cn'
        )



class TestUnicodeCallingFormat(AWSMockServiceTestCase):
    connection_class = S3Connection

    def default_body(self):
        return """<?xml version="1.0" encoding="UTF-8"?>
<ListAllMyBucketsResult xmlns="http://doc.s3.amazonaws.com/2006-03-01">
  <Owner>
    <ID>bcaf1ffd86f461ca5fb16fd081034f</ID>
    <DisplayName>webfile</DisplayName>
  </Owner>
  <Buckets>
    <Bucket>
      <Name>quotes</Name>
      <CreationDate>2006-02-03T16:45:09.000Z</CreationDate>
    </Bucket>
    <Bucket>
      <Name>samples</Name>
      <CreationDate>2006-02-03T16:41:58.000Z</CreationDate>
    </Bucket>
  </Buckets>
</ListAllMyBucketsResult>"""

    def create_service_connection(self, **kwargs):
        kwargs['calling_format'] = u'boto.s3.connection.OrdinaryCallingFormat'
        return super(TestUnicodeCallingFormat,
                     self).create_service_connection(**kwargs)

    def test_unicode_calling_format(self):
        self.set_http_response(status_code=200)
        self.service_connection.get_all_buckets()


class TestHeadBucket(AWSMockServiceTestCase):
    connection_class = S3Connection

    def default_body(self):
        # HEAD requests always have an empty body.
        return ""

    def test_head_bucket_success(self):
        self.set_http_response(status_code=200)
        buck = self.service_connection.head_bucket('my-test-bucket')
        self.assertTrue(isinstance(buck, Bucket))
        self.assertEqual(buck.name, 'my-test-bucket')

    def test_head_bucket_forbidden(self):
        self.set_http_response(status_code=403)

        with self.assertRaises(S3ResponseError) as cm:
            self.service_connection.head_bucket('cant-touch-this')

        err = cm.exception
        self.assertEqual(err.status, 403)
        self.assertEqual(err.error_code, 'AccessDenied')
        self.assertEqual(err.message, 'Access Denied')

    def test_head_bucket_notfound(self):
        self.set_http_response(status_code=404)

        with self.assertRaises(S3ResponseError) as cm:
            self.service_connection.head_bucket('totally-doesnt-exist')

        err = cm.exception
        self.assertEqual(err.status, 404)
        self.assertEqual(err.error_code, 'NoSuchBucket')
        self.assertEqual(err.message, 'The specified bucket does not exist')

    def test_head_bucket_other(self):
        self.set_http_response(status_code=405)

        with self.assertRaises(S3ResponseError) as cm:
            self.service_connection.head_bucket('you-broke-it')

        err = cm.exception
        self.assertEqual(err.status, 405)
        # We don't have special-cases for this error status.
        self.assertEqual(err.error_code, None)
        self.assertEqual(err.message, '')

class TestLookup(AWSMockServiceTestCase):
    connection_class = S3Connection

    def test_lookup_bucket_success(self):
        self.set_http_response(status_code=200)
        buck = self.service_connection.lookup('my-test-bucket')
        self.assertTrue(isinstance(buck, Bucket))
        self.assertEqual(buck.name, 'my-test-bucket')

    def test_lookup_bucket_notfound(self):
        self.set_http_response(status_code=404)
        buck = self.service_connection.lookup('doesnt-exist')
        self.assertEqual(buck, None)

    @patch.object(S3Connection, 'lookup')
    def test_lookup_bucket_exception(self, mock_lookup):
        # Any exception that's not a storage response error should be re-raised
        mock_lookup.side_effect = Exception('Something went wrong')

        with self.assertRaises(Exception) as cm:
            self.service_connection.lookup('doesnt-matter')

        err = cm.exception
        self.assertEqual(err.message, 'Something went wrong')

        # Any storage response error with status != 404 should be re-raised
        mock_lookup.reset_mock()
        mock_lookup.side_effect = S3ResponseError(403, 'Forbidden')

        with self.assertRaises(S3ResponseError) as cm:
            self.service_connection.lookup('doesnt-matter')

        err = cm.exception
        self.assertEqual(err.status, 403)
        self.assertEqual(err.reason, 'Forbidden')


if __name__ == "__main__":
    unittest.main()
