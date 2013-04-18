# -*- coding: UTF-8 -*-
from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.vpc import VPCConnection

DESCRIBE_VPCS = r'''<?xml version="1.0" encoding="UTF-8"?>
<DescribeVpcsResponse xmlns="http://ec2.amazonaws.com/doc/2013-02-01/">
    <requestId>623040d1-b51c-40bc-8080-93486f38d03d</requestId>
    <vpcSet>
        <item>
            <vpcId>vpc-12345678</vpcId>
            <state>available</state>
            <cidrBlock>172.16.0.0/16</cidrBlock>
            <dhcpOptionsId>dopt-12345678</dhcpOptionsId>
            <instanceTenancy>default</instanceTenancy>
            <isDefault>false</isDefault>
        </item>
    </vpcSet>
</DescribeVpcsResponse>'''

class TestDescriveVPCs(AWSMockServiceTestCase):

    connection_class = VPCConnection
    
    def default_body(self):
        return DESCRIBE_VPCS
    
    def test_get_vpcs(self):
        self.set_http_response(status_code=200)

        api_response = self.service_connection.get_all_vpcs()
        self.assertEqual(len(api_response), 1)

        vpc = api_response[0]
        self.assertFalse(vpc.is_default)
        self.assertEqual(vpc.instance_tenancy,'default')

if __name__ == '__main__':
    unittest.main()