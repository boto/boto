#!/usr/bin/env python
# Copyright (c) 2014 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
from tests.unit import AWSMockServiceTestCase
from boto.route53.connection import Route53Connection
from boto.route53.zone import Zone
from nose.plugins.attrib import attr
from boto.compat import six

@attr(route53=True)
class TestUpdateZoneCommentRoute53(AWSMockServiceTestCase):
    connection_class = Route53Connection

    def setUp(self):
        super(TestUpdateZoneCommentRoute53, self).setUp()

    def default_body(self):
        return b"""
<UpdateHostedZoneCommentResponse xmlns="https://route53.amazonaws.com/doc/2013-04-01/">
    <HostedZone>
        <Id>/hostedzone/Z11111</Id>
        <Name>example.com.</Name>
        <CallerReference>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</CallerReference>
        <Config>
            <Comment>My fancy new comment</Comment>
            <PrivateZone>false</PrivateZone>
        </Config>
        <ResourceRecordSetCount>2</ResourceRecordSetCount>
    </HostedZone>
</UpdateHostedZoneCommentResponse>
        """

    def test_update_hosted_zone_comment(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.update_hosted_zone_comment("Z11111","My fancy new comment")

        self.assertEqual(response['Id'], "Z11111")
        self.assertEqual(response['Name'], "example.com.")
        self.assertEqual(response['Config']['Comment'], "My fancy new comment")
