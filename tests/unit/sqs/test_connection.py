#!/usr/bin/env python
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

from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.sqs.connection import SQSConnection
from boto.sqs.regioninfo import SQSRegionInfo


class SQSAuthParams(AWSMockServiceTestCase):
    connection_class = SQSConnection

    def setUp(self):
        super(SQSAuthParams, self).setUp()

    def default_body(self):
        return """<?xml version="1.0"?>
            <CreateQueueResponse>
              <CreateQueueResult>
                <QueueUrl>
                  https://queue.amazonaws.com/599169622985/myqueue1
                </QueueUrl>
              </CreateQueueResult>
              <ResponseMetadata>
                <RequestId>54d4c94d-2307-54a8-bb27-806a682a5abd</RequestId>
              </ResponseMetadata>
            </CreateQueueResponse>"""

    def test_auth_service_name_override(self):
        self.set_http_response(status_code=200)
        # We can use the auth_service_name to change what service
        # name to use for the credential scope for sigv4.
        self.service_connection.auth_service_name = 'service_override'

        self.service_connection.create_queue('my_queue')
        # Note the service_override value instead.
        self.assertIn('us-east-1/service_override/aws4_request',
                      self.actual_request.headers['Authorization'])

    def test_class_attribute_can_set_service_name(self):
        self.set_http_response(status_code=200)
        # The SQS class has an 'AuthServiceName' param of 'sqs':
        self.assertEqual(self.service_connection.AuthServiceName, 'sqs')

        self.service_connection.create_queue('my_queue')
        # And because of this, the value of 'sqs' will be used instead of
        # 'queue' for the credential scope:
        self.assertIn('us-east-1/sqs/aws4_request',
                      self.actual_request.headers['Authorization'])

    def test_auth_region_name_is_automatically_updated(self):
        region = SQSRegionInfo(name='us-west-2',
                               endpoint='us-west-2.queue.amazonaws.com')
        self.service_connection = SQSConnection(
            https_connection_factory=self.https_connection_factory,
            aws_access_key_id='aws_access_key_id',
            aws_secret_access_key='aws_secret_access_key',
            region=region)
        self.initialize_service_connection()
        self.set_http_response(status_code=200)
        self.service_connection.create_queue('my_queue')
        
        # Note the region name below is 'us-west-2'.
        self.assertIn('us-west-2/sqs/aws4_request',
                      self.actual_request.headers['Authorization'])
        
    def test_set_get_auth_service_and_region_names(self):
        self.service_connection.auth_service_name = 'service_name'
        self.service_connection.auth_region_name = 'region_name'

        self.assertEqual(self.service_connection.auth_service_name,
                         'service_name')
        self.assertEqual(self.service_connection.auth_region_name, 'region_name')

    def test_get_queue_with_owner_account_id_returns_queue(self):
        
        self.set_http_response(status_code=200)
        self.service_connection.create_queue('my_queue')
        
        self.service_connection.get_queue('my_queue', '599169622985')

        assert 'QueueOwnerAWSAccountId' in self.actual_request.params.keys()
        self.assertEquals(self.actual_request.params['QueueOwnerAWSAccountId'], '599169622985')
        

if __name__ == '__main__':
    unittest.main()
