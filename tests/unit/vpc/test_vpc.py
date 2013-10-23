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


class TestVPCConnection(unittest.TestCase):
    """
    Test class for `boto.vpc.VPCConnection`
    """

    def setUp(self):
        """
        Setup method to initialize vpc_connection objectq
        """
        super(TestVPCConnection, self).setUp()
        self.vpc_connection = VPCConnection(
            aws_access_key_id='aws_access_key_id',
            aws_secret_access_key='aws_secret_access_key')

    def test_detach_internet_gateway(self):
        """
        Tests detach_internet_gateway with all valid parameters
        """
        internet_gateway_id = 'mock_gateway_id'
        vpc_id = 'mock_vpc_id'

        def get_status(status, params):
            if status == "DetachInternetGateway" and \
                params["InternetGatewayId"] == internet_gateway_id and \
                    params["VpcId"] == vpc_id:
                return True
            else:
                return False

        self.vpc_connection.get_status = get_status
        status = self.vpc_connection.detach_internet_gateway(
            internet_gateway_id, vpc_id)
        self.assertEquals(True, status)

    def test_replace_route_table_association(self):
        """
        Tests replace_route_table_assocation with all valid parameters
        """
        association_id = 'mock_association_id'
        route_table_id = 'mock_route_table_id'

        def get_status(status, params):
            if status == "ReplaceRouteTableAssociation" and \
                params["AssociationId"] == association_id and \
                    params["RouteTableId"] == route_table_id:
                return True
            else:
                return False

        self.vpc_connection.get_status = get_status
        status = self.vpc_connection.replace_route_table_assocation(
            association_id, route_table_id)
        self.assertEquals(True, status)


if __name__ == '__main__':
    unittest.main()
