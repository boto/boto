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
from boto.mws.connection import MWSConnection, api_call_map, destructure_object
from boto.mws.response import (ResponseElement, GetFeedSubmissionListResult,
                               ResponseFactory)

from tests.unit import AWSMockServiceTestCase


class TestMWSConnection(AWSMockServiceTestCase):
    connection_class = MWSConnection
    mws = True

    def default_body(self):
        return """<?xml version="1.0"?>
<GetFeedSubmissionListResponse xmlns="http://mws.amazonservices.com/
doc/2009-01-01/">
  <GetFeedSubmissionListResult>
    <NextToken>2YgYW55IGNhcm5hbCBwbGVhc3VyZS4=</NextToken>
    <HasNext>true</HasNext>
    <FeedSubmissionInfo>
      <FeedSubmissionId>2291326430</FeedSubmissionId>
      <FeedType>_POST_PRODUCT_DATA_</FeedType>
      <SubmittedDate>2009-02-20T02:10:35+00:00</SubmittedDate>
      <FeedProcessingStatus>_SUBMITTED_</FeedProcessingStatus>
    </FeedSubmissionInfo>
  </GetFeedSubmissionListResult>
  <ResponseMetadata>
    <RequestId>1105b931-6f1c-4480-8e97-f3b467840a9e</RequestId>
  </ResponseMetadata>
</GetFeedSubmissionListResponse>"""

    def test_destructure_object(self):
        # Test that parsing of user input to Amazon input works.
        response = ResponseElement()
        response.C = 'four'
        response.D = 'five'
        inputs = [
            ('A', 'B'), ['B', 'A'], set(['C']),
            False, 'String', {'A': 'one', 'B': 'two'},
            response,
            {'A': 'one', 'B': 'two',
             'C': [{'D': 'four', 'E': 'five'},
                   {'F': 'six', 'G': 'seven'}]},
        ]
        outputs = [
            {'Prefix.1': 'A', 'Prefix.2': 'B'},
            {'Prefix.1': 'B', 'Prefix.2': 'A'},
            {'Prefix.1': 'C'},
            {'Prefix': 'false'}, {'Prefix': 'String'},
            {'Prefix.A': 'one', 'Prefix.B': 'two'},
            {'Prefix.C': 'four', 'Prefix.D': 'five'},
            {'Prefix.A': 'one', 'Prefix.B': 'two',
             'Prefix.C.member.1.D': 'four',
             'Prefix.C.member.1.E': 'five',
             'Prefix.C.member.2.F': 'six',
             'Prefix.C.member.2.G': 'seven'}
        ]
        for user, amazon in zip(inputs, outputs):
            result = {}
            members = user is inputs[-1]
            destructure_object(user, result, prefix='Prefix', members=members)
            self.assertEqual(result, amazon)

    def test_built_api_call_map(self):
        # Ensure that the map is populated.
        # It starts empty, but the decorators should add to it as they're
        # applied. As of 2013/10/21, there were 52 calls (with more likely
        # to be added), so let's simply ensure there are enough there.
        self.assertTrue(len(api_call_map.keys()) > 50)

    def test_method_for(self):
        # First, ensure that the map is in "right enough" state.
        self.assertTrue('GetFeedSubmissionList' in api_call_map)

        # Make sure we can find the correct method.
        func = self.service_connection.method_for('GetFeedSubmissionList')
        # Ensure the right name was found.
        self.assertTrue(callable(func))
        ideal = self.service_connection.get_feed_submission_list
        self.assertEqual(func, ideal)

        # Check a non-existent action.
        func = self.service_connection.method_for('NotHereNorThere')
        self.assertEqual(func, None)

    def test_response_factory(self):
        connection = self.service_connection
        body = self.default_body()
        action = 'GetFeedSubmissionList'
        parser = connection._response_factory(action, connection=connection)
        response = connection._parse_response(parser, 'text/xml', body)
        self.assertEqual(response._action, action)
        self.assertEqual(response.__class__.__name__, action + 'Response')
        self.assertEqual(response._result.__class__,
                         GetFeedSubmissionListResult)

        class MyResult(GetFeedSubmissionListResult):
            _hello = '_world'

        scope = {'GetFeedSubmissionListResult': MyResult}
        connection._setup_factories([scope])

        parser = connection._response_factory(action, connection=connection)
        response = connection._parse_response(parser, 'text/xml', body)
        self.assertEqual(response._action, action)
        self.assertEqual(response.__class__.__name__, action + 'Response')
        self.assertEqual(response._result.__class__, MyResult)
        self.assertEqual(response._result._hello, '_world')
        self.assertEqual(response._result.HasNext, 'true')

    def test_get_service_status(self):
        with self.assertRaises(AttributeError) as err:
            self.service_connection.get_service_status()

        self.assertTrue('products,' in str(err.exception))
        self.assertTrue('inventory,' in str(err.exception))
        self.assertTrue('feeds,' in str(err.exception))


if __name__ == '__main__':
    unittest.main()
