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
import json
from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase
from mock import Mock

from boto.sns.connection import SNSConnection

QUEUE_POLICY = {
    u'Policy':
        (u'{"Version":"2008-10-17","Id":"arn:aws:sqs:us-east-1:'
         'idnum:testqueuepolicy/SQSDefaultPolicy","Statement":'
         '[{"Sid":"sidnum","Effect":"Allow","Principal":{"AWS":"*"},'
         '"Action":"SQS:GetQueueUrl","Resource":'
         '"arn:aws:sqs:us-east-1:idnum:testqueuepolicy"}]}')}


class TestSNSConnection(AWSMockServiceTestCase):
    connection_class = SNSConnection

    def setUp(self):
        super(TestSNSConnection, self).setUp()

    def default_body(self):
        return "{}"

    def test_sqs_with_existing_policy(self):
        self.set_http_response(status_code=200)

        queue = Mock()
        queue.get_attributes.return_value = QUEUE_POLICY
        queue.arn = 'arn:aws:sqs:us-east-1:idnum:queuename'

        self.service_connection.subscribe_sqs_queue('topic_arn', queue)
        self.assert_request_parameters({
               'Action': 'Subscribe',
               'ContentType': 'JSON',
               'Endpoint': 'arn:aws:sqs:us-east-1:idnum:queuename',
               'Protocol': 'sqs',
               'SignatureMethod': 'HmacSHA256',
               'SignatureVersion': 2,
               'TopicArn': 'topic_arn',
               'Version': '2010-03-31',
        }, ignore_params_values=['AWSAccessKeyId', 'Timestamp'])

        # Verify that the queue policy was properly updated.
        actual_policy = json.loads(queue.set_attribute.call_args[0][1])
        self.assertEqual(actual_policy['Version'], '2008-10-17')
        # A new statement should be appended to the end of the statement list.
        self.assertEqual(len(actual_policy['Statement']), 2)
        self.assertEqual(actual_policy['Statement'][1]['Action'],
                         'SQS:SendMessage')

    def test_sqs_with_no_previous_policy(self):
        self.set_http_response(status_code=200)

        queue = Mock()
        queue.get_attributes.return_value = {}
        queue.arn = 'arn:aws:sqs:us-east-1:idnum:queuename'

        self.service_connection.subscribe_sqs_queue('topic_arn', queue)
        self.assert_request_parameters({
               'Action': 'Subscribe',
               'ContentType': 'JSON',
               'Endpoint': 'arn:aws:sqs:us-east-1:idnum:queuename',
               'Protocol': 'sqs',
               'SignatureMethod': 'HmacSHA256',
               'SignatureVersion': 2,
               'TopicArn': 'topic_arn',
               'Version': '2010-03-31',
        }, ignore_params_values=['AWSAccessKeyId', 'Timestamp'])
        actual_policy = json.loads(queue.set_attribute.call_args[0][1])
        # Only a single statement should be part of the policy.
        self.assertEqual(len(actual_policy['Statement']), 1)


if __name__ == '__main__':
    unittest.main()
