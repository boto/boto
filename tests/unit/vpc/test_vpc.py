# -*- coding: UTF-8 -*-
from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.vpc import VPCConnection, VPC


DESCRIBE_VPCS = b'''<?xml version="1.0" encoding="UTF-8"?>
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


class TestDescribeVPCs(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return DESCRIBE_VPCS

    def test_get_vpcs(self):
        self.set_http_response(status_code=200)

        api_response = self.service_connection.get_all_vpcs()
        self.assertEqual(len(api_response), 1)

        vpc = api_response[0]
        self.assertFalse(vpc.is_default)
        self.assertEqual(vpc.instance_tenancy, 'default')


class TestCreateVpc(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return b"""
            <CreateVpcResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-01/">
               <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
               <vpc>
                  <vpcId>vpc-1a2b3c4d</vpcId>
                  <state>pending</state>
                  <cidrBlock>10.0.0.0/16</cidrBlock>
                  <dhcpOptionsId>dopt-1a2b3c4d2</dhcpOptionsId>
                  <instanceTenancy>default</instanceTenancy>
                  <tagSet/>
               </vpc>
            </CreateVpcResponse>
        """

    def test_create_vpc(self):
        self.set_http_response(status_code=200)
        api_response = self.service_connection.create_vpc('10.0.0.0/16', 'default')
        self.assert_request_parameters({
            'Action': 'CreateVpc',
            'InstanceTenancy': 'default',
            'CidrBlock': '10.0.0.0/16'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertIsInstance(api_response, VPC)
        self.assertEquals(api_response.id, 'vpc-1a2b3c4d')
        self.assertEquals(api_response.state, 'pending')
        self.assertEquals(api_response.cidr_block, '10.0.0.0/16')
        self.assertEquals(api_response.dhcp_options_id, 'dopt-1a2b3c4d2')
        self.assertEquals(api_response.instance_tenancy, 'default')


class TestDeleteVpc(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return b"""
            <DeleteVpcResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-01/">
               <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
               <return>true</return>
            </DeleteVpcResponse>
        """

    def test_delete_vpc(self):
        self.set_http_response(status_code=200)
        api_response = self.service_connection.delete_vpc('vpc-1a2b3c4d')
        self.assert_request_parameters({
            'Action': 'DeleteVpc',
            'VpcId': 'vpc-1a2b3c4d'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertEquals(api_response, True)


class TestModifyVpcAttribute(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return b"""
            <ModifyVpcAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-01/">
               <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
               <return>true</return>
            </ModifyVpcAttributeResponse>
        """

    def test_modify_vpc_attribute_dns_support(self):
        self.set_http_response(status_code=200)
        api_response = self.service_connection.modify_vpc_attribute(
            'vpc-1a2b3c4d', enable_dns_support=True)
        self.assert_request_parameters({
            'Action': 'ModifyVpcAttribute',
            'VpcId': 'vpc-1a2b3c4d',
            'EnableDnsSupport.Value': 'true'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertEquals(api_response, True)

    def test_modify_vpc_attribute_dns_hostnames(self):
        self.set_http_response(status_code=200)
        api_response = self.service_connection.modify_vpc_attribute(
            'vpc-1a2b3c4d', enable_dns_hostnames=True)
        self.assert_request_parameters({
            'Action': 'ModifyVpcAttribute',
            'VpcId': 'vpc-1a2b3c4d',
            'EnableDnsHostnames.Value': 'true'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertEquals(api_response, True)

if __name__ == '__main__':
    unittest.main()
