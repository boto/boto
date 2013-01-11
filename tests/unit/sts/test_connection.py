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
from boto.sts.connection import STSConnection
from tests.unit import AWSMockServiceTestCase


class TestSTSConnection(AWSMockServiceTestCase):
    connection_class = STSConnection

    def setUp(self):
        super(TestSTSConnection, self).setUp()

    def default_body(self):
        return """
            <AssumeRoleResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
              <AssumeRoleResult>
                <AssumedRoleUser>
                  <Arn>arn:role</Arn>
                  <AssumedRoleId>roleid:myrolesession</AssumedRoleId>
                </AssumedRoleUser>
                <Credentials>
                  <SessionToken>session_token</SessionToken>
                  <SecretAccessKey>secretkey</SecretAccessKey>
                  <Expiration>2012-10-18T10:18:14.789Z</Expiration>
                  <AccessKeyId>accesskey</AccessKeyId>
                </Credentials>
              </AssumeRoleResult>
              <ResponseMetadata>
                <RequestId>8b7418cb-18a8-11e2-a706-4bd22ca68ab7</RequestId>
              </ResponseMetadata>
            </AssumeRoleResponse>
        """

    def test_assume_role(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.assume_role('arn:role', 'mysession')
        self.assert_request_parameters(
            {'Action': 'AssumeRole',
             'RoleArn': 'arn:role',
             'RoleSessionName': 'mysession'},
            ignore_params_values=['Timestamp', 'AWSAccessKeyId',
                                  'SignatureMethod', 'SignatureVersion',
                                  'Version'])
        self.assertEqual(response.credentials.access_key, 'accesskey')
        self.assertEqual(response.credentials.secret_key, 'secretkey')
        self.assertEqual(response.credentials.session_token, 'session_token')
        self.assertEqual(response.user.arn, 'arn:role')
        self.assertEqual(response.user.assume_role_id, 'roleid:myrolesession')


if __name__ == '__main__':
    unittest.main()
