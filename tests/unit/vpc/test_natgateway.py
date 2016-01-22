from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.vpc import VPCConnection, NatGateway


class TestDescribeNatGateway(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return b"""
            <DescribeNatGatewaysResponse xmlns="http://ec2.amazonaws.com/doc/2015-10-01/">
                <requestId>bfed02c6-dae9-47c0-86a2-example</requestId>
                <natGatewaySet>
                     <item>
                        <subnetId>subnet-1a2a3a4a</subnetId>
                        <natGatewayAddressSet>
                            <item>
                                <networkInterfaceId>eni-00e37850</networkInterfaceId>
                                <publicIp>198.18.125.129</publicIp>
                                <allocationId>eipalloc-37fc1a52</allocationId>
                                <privateIp>10.0.2.147</privateIp>
                            </item>
                        </natGatewayAddressSet>
                        <createTime>2015-11-25T14:00:55.416Z</createTime>
                        <vpcId>vpc-4e20d42b</vpcId>
                        <natGatewayId>nat-04e77a5e9c34432f9</natGatewayId>
                        <state>available</state>
                    </item>
                </natGatewaySet>
            </DescribeNatGatewaysResponse>
        """

    def test_describe_nat_gateway(self):
        self.set_http_response(status_code=200)
        api_response = self.service_connection.get_all_nat_gateways(
            'nat-04e77a5e9c34432f9', filters=[('natGatewayAddress.allocationId', ['eipalloc-37fc1a52'])])
        self.assert_request_parameters({
            'Action': 'DescribeNatGateways',
            'NatGatewayId.1': 'nat-04e77a5e9c34432f9',
            'Filter.1.Name': 'natGatewayAddress.allocationId',
            'Filter.1.Value.1': 'eipalloc-37fc1a52'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertEquals(len(api_response), 1)
        self.assertIsInstance(api_response[0], NatGateway)
        self.assertEqual(api_response[0].id, 'nat-04e77a5e9c34432f9')


class TestCreateNatGateway(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return b"""
            <CreateNatGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2015-10-01/">
                <requestId>1b74dc5c-bcda-403f-867d-example</requestId>
                <natGateway>
                    <subnetId>subnet-1a2b3c4d</subnetId>
                    <natGatewayAddressSet>
                        <item>
                            <allocationId>eipalloc-37fc1a52</allocationId>
                        </item>
                    </natGatewayAddressSet>
                    <createTime>2015-11-25T14:00:55.416Z</createTime>
                    <vpcId>vpc-4e20d42b</vpcId>
                    <natGatewayId>nat-04e77a5e9c34432f9</natGatewayId>
                    <state>pending</state>
                </natGateway>
            </CreateNatGatewayResponse>
        """

    def test_create_nat_gateway(self):
        self.set_http_response(status_code=200)
        api_response = self.service_connection.create_nat_gateway('subnet-1a2b3c4d', 'eipalloc-37fc1a52')
        self.assert_request_parameters({
            'Action': 'CreateNatGateway',
            'SubnetId': 'subnet-1a2b3c4d',
            'AllocationId': 'eipalloc-37fc1a52'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertIsInstance(api_response, NatGateway)
        self.assertEqual(api_response.id, 'nat-04e77a5e9c34432f9')


class TestDeleteNatGateway(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return b"""
            <DeleteNatGatewayResponse xmlns="http://ec2.amazonaws.com/doc/2015-10-01/">
                <requestId>741fc8ab-6ebe-452b-b92b-example</requestId>
                <natGatewayId>nat-04ae55e711cec5680</natGatewayId>
            </DeleteNatGatewayResponse>
        """

    def test_delete_nat_gateway(self):
        self.set_http_response(status_code=200)
        api_response = self.service_connection.delete_nat_gateway('nat-04ae55e711cec5680')
        self.assert_request_parameters({
            'Action': 'DeleteNatGateway',
            'NatGatewayId': 'nat-04ae55e711cec5680'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertEquals(api_response, True)

if __name__ == '__main__':
    unittest.main()
