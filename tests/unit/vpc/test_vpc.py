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


class TestReplaceRouteTableAssociation(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return """
            <ReplaceRouteTableAssociationResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-01/">
               <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
               <newAssociationId>rtbassoc-faad4893</newAssociationId>
            </ReplaceRouteTableAssociationResponse>
        """

    def test_replace_route_table_association(self):
        self.set_http_response(status_code=200)
        self.service_connection.replace_route_table_assocation('rtbassoc-faad4893', 'rtb-f9ad4890')
        self.assert_request_parameters({
            'Action': 'ReplaceRouteTableAssociation',
            'AssociationId': 'rtbassoc-faad4893',
            'RouteTableId': 'rtb-f9ad4890'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])


class TestCreateVPCs(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return """
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
        self.service_connection.create_vpc('10.0.0.0/16', 'default')
        self.assert_request_parameters({
            'Action': 'CreateVpc',
            'InstanceTenancy': 'default',
            'CidrBlock': '10.0.0.0/16'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])


class TestDescribeDhcpOptions(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return """
            <DescribeDhcpOptionsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-01/">
              <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
              <dhcpOptionsSet>
                <item>
                  <dhcpOptionsId>dopt-7a8b9c2d</dhcpOptionsId>
                  <dhcpConfigurationSet>
                    <item>
                      <key>domain-name</key>
                      <valueSet>
                        <item>
                          <value>example.com</value>
                        </item>
                      </valueSet>
                    </item>
                    <item>
                      <key>domain-name-servers</key>
                      <valueSet>
                        <item>
                          <value>10.2.5.1</value>
                      </item>
                      </valueSet>
                    </item>
                    <item>
                      <key>domain-name-servers</key>
                      <valueSet>
                        <item>
                          <value>10.2.5.2</value>
                          </item>
                      </valueSet>
                    </item>
                  </dhcpConfigurationSet>
                  <tagSet/>
                </item>
              </dhcpOptionsSet>
            </DescribeDhcpOptionsResponse>
        """

    def test_get_all_dhcp_options(self):
        self.set_http_response(status_code=200)
        self.service_connection.get_all_dhcp_options(['dopt-7a8b9c2d'],
                                                     [('key', 'domain-name')])
        self.assert_request_parameters({
            'Action': 'DescribeDhcpOptions',
            'DhcpOptionsId.1': 'dopt-7a8b9c2d',
            'Filter.1.Name': 'key',
            'Filter.1.Value.1': 'domain-name'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])


if __name__ == '__main__':
    unittest.main()
