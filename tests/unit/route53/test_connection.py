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
from boto.route53.record import ResourceRecordSets, Record
from boto.route53.zone import Zone

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


class TestCreateZoneRoute53(AWSMockServiceTestCase):
    connection_class = Route53Connection

    def setUp(self):
        super(TestCreateZoneRoute53, self).setUp()

    def default_body(self):
        return """
<CreateHostedZoneResponse xmlns="https://route53.amazonaws.com/doc/2012-02-29/">
    <HostedZone>
        <Id>/hostedzone/Z11111</Id>
        <Name>example.com.</Name>
        <CallerReference>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</CallerReference>
        <Config>
            <Comment></Comment>
        </Config>
        <ResourceRecordSetCount>2</ResourceRecordSetCount>
    </HostedZone>
    <ChangeInfo>
        <Id>/change/C1111111111111</Id>
        <Status>PENDING</Status>
        <SubmittedAt>2014-02-02T10:19:29.928Z</SubmittedAt>
    </ChangeInfo>
    <DelegationSet>
        <NameServers>
            <NameServer>ns-100.awsdns-01.com</NameServer>
            <NameServer>ns-1000.awsdns-01.co.uk</NameServer>
            <NameServer>ns-1000.awsdns-01.org</NameServer>
            <NameServer>ns-900.awsdns-01.net</NameServer>
        </NameServers>
    </DelegationSet>
</CreateHostedZoneResponse>
        """

    def test_create_zone(self):
        self.set_http_response(status_code=201)
        response = self.service_connection.create_zone("example.com.")

        self.assertTrue(isinstance(response, Zone))
        self.assertEqual(response.id, "Z11111")
        self.assertEqual(response.name, "example.com.")

    def test_create_hosted_zone(self):
        self.set_http_response(status_code=201)
        response = self.service_connection.create_hosted_zone("example.com.", "my_ref", "this is a comment")

        self.assertEqual(response['CreateHostedZoneResponse']['DelegationSet']['NameServers'],
                         ['ns-100.awsdns-01.com', 'ns-1000.awsdns-01.co.uk', 'ns-1000.awsdns-01.org', 'ns-900.awsdns-01.net'])


class TestGetZoneRoute53(AWSMockServiceTestCase):
    connection_class = Route53Connection

    def setUp(self):
        super(TestGetZoneRoute53, self).setUp()

    def default_body(self):
        return """
<ListHostedZonesResponse xmlns="https://route53.amazonaws.com/doc/2012-02-29/">
    <HostedZones>
        <HostedZone>
            <Id>/hostedzone/Z1111</Id>
            <Name>example2.com.</Name>
            <CallerReference>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</CallerReference>
            <Config/>
            <ResourceRecordSetCount>3</ResourceRecordSetCount>
        </HostedZone>
        <HostedZone>
            <Id>/hostedzone/Z2222</Id>
            <Name>example1.com.</Name>
            <CallerReference>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeef</CallerReference>
            <Config/>
            <ResourceRecordSetCount>6</ResourceRecordSetCount>
        </HostedZone>
        <HostedZone>
            <Id>/hostedzone/Z3333</Id>
            <Name>example.com.</Name>
            <CallerReference>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeeg</CallerReference>
            <Config/>
            <ResourceRecordSetCount>6</ResourceRecordSetCount>
        </HostedZone>
    </HostedZones>
    <IsTruncated>false</IsTruncated>
    <MaxItems>100</MaxItems>
</ListHostedZonesResponse>
        """

    def test_list_zones(self):
        self.set_http_response(status_code=201)
        response = self.service_connection.get_all_hosted_zones()

        domains = ['example2.com.', 'example1.com.', 'example.com.']
        print response['ListHostedZonesResponse']['HostedZones'][0]
        for d in response['ListHostedZonesResponse']['HostedZones']:
            print "Removing: %s" % d['Name']
            domains.remove(d['Name'])

        self.assertEqual(domains, [])

    def test_get_zone(self):
        self.set_http_response(status_code=201)
        response = self.service_connection.get_zone('example.com.')

        self.assertTrue(isinstance(response, Zone))
        self.assertEqual(response.name, "example.com.")


class TestGetHostedZoneRoute53(AWSMockServiceTestCase):
    connection_class = Route53Connection

    def setUp(self):
        super(TestGetHostedZoneRoute53, self).setUp()

    def default_body(self):
        return """
<GetHostedZoneResponse xmlns="https://route53.amazonaws.com/doc/2012-02-29/">
    <HostedZone>
        <Id>/hostedzone/Z1111</Id>
        <Name>example.com.</Name>
        <CallerReference>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</CallerReference>
        <Config/>
        <ResourceRecordSetCount>3</ResourceRecordSetCount>
    </HostedZone>
    <DelegationSet>
        <NameServers>
            <NameServer>ns-1000.awsdns-40.org</NameServer>
            <NameServer>ns-200.awsdns-30.com</NameServer>
            <NameServer>ns-900.awsdns-50.net</NameServer>
            <NameServer>ns-1000.awsdns-00.co.uk</NameServer>
        </NameServers>
    </DelegationSet>
</GetHostedZoneResponse>
"""

    def test_list_zones(self):
        self.set_http_response(status_code=201)
        response = self.service_connection.get_hosted_zone("Z1111")

        self.assertEqual(response['GetHostedZoneResponse']['HostedZone']['Id'], '/hostedzone/Z1111')
        self.assertEqual(response['GetHostedZoneResponse']['HostedZone']['Name'], 'example.com.')
        self.assertEqual(response['GetHostedZoneResponse']['DelegationSet']['NameServers'],
                         ['ns-1000.awsdns-40.org', 'ns-200.awsdns-30.com', 'ns-900.awsdns-50.net', 'ns-1000.awsdns-00.co.uk'])


class TestGetAllRRSetsRoute53(AWSMockServiceTestCase):
    connection_class = Route53Connection

    def setUp(self):
        super(TestGetAllRRSetsRoute53, self).setUp()

    def default_body(self):
        return """
<ListResourceRecordSetsResponse xmlns="https://route53.amazonaws.com/doc/2012-02-29/">
    <ResourceRecordSets>
        <ResourceRecordSet>
            <Name>test.example.com.</Name>
            <Type>A</Type>
            <TTL>60</TTL>
            <ResourceRecords>
                <ResourceRecord>
                    <Value>10.0.0.1</Value>
                </ResourceRecord>
            </ResourceRecords>
        </ResourceRecordSet>
        <ResourceRecordSet>
            <Name>www.example.com.</Name>
            <Type>A</Type>
            <TTL>60</TTL>
            <ResourceRecords>
                <ResourceRecord>
                    <Value>10.0.0.2</Value>
                </ResourceRecord>
            </ResourceRecords>
        </ResourceRecordSet>
        <ResourceRecordSet>
            <Name>us-west-2.example.com.</Name>
            <Type>A</Type>
            <SetIdentifier>latency-example-us-west-2</SetIdentifier>
            <Region>us-west-2</Region>
            <AliasTarget>
                <HostedZoneId>ABCDEFG123456</HostedZoneId>
                <EvaluateTargetHealth>true</EvaluateTargetHealth>
                <DNSName>example-123456.us-west-2.elb.amazonaws.com.</DNSName>
            </AliasTarget>
        </ResourceRecordSet>
    </ResourceRecordSets>
    <IsTruncated>false</IsTruncated>
    <MaxItems>100</MaxItems>
</ListResourceRecordSetsResponse>
        """

    def test_get_all_rr_sets(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.get_all_rrsets("Z1111", "A", "example.com.")

        self.assertEqual(self.actual_request.path,
                         "/2013-04-01/hostedzone/Z1111/rrset?type=A&name=example.com.")

        self.assertTrue(isinstance(response, ResourceRecordSets))
        self.assertEqual(response.hosted_zone_id, "Z1111")
        self.assertTrue(isinstance(response[0], Record))

        self.assertTrue(response[0].name, "test.example.com.")
        self.assertTrue(response[0].ttl, "60")
        self.assertTrue(response[0].type, "A")

        latency_record = response[2]
        self.assertEqual(latency_record.name, 'us-west-2.example.com.')
        self.assertEqual(latency_record.type, 'A')
        self.assertEqual(latency_record.identifier, 'latency-example-us-west-2')
        self.assertEqual(latency_record.region, 'us-west-2')
        self.assertEqual(latency_record.alias_hosted_zone_id, 'ABCDEFG123456')
        self.assertEqual(latency_record.alias_evaluate_target_health, 'true')
        self.assertEqual(latency_record.alias_dns_name, 'example-123456.us-west-2.elb.amazonaws.com.')
