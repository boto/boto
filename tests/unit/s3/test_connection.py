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

from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.s3.connection import S3Connection, HostRequiredError


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


class TestSigV4HostError(AWSMockServiceTestCase):
    connection_class = S3Connection

    def setUp(self):
        super(TestSigV4HostError, self).setUp()
        self.config = {}
        self.config_patch = mock.patch('boto.provider.config.get',
                                       self.get_config)
        self.has_config_patch = mock.patch('boto.provider.config.has_option',
                                           self.has_config)
        self.config_patch.start()
        self.has_config_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        self.has_config_patch.stop()

    def has_config(self, section_name, key):
        try:
            self.config[section_name][key]
            return True
        except KeyError:
            return False

    def get_config(self, section_name, key, default=None):
        try:
            return self.config[section_name][key]
        except KeyError:
            return None

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


if __name__ == "__main__":
    unittest.main()
