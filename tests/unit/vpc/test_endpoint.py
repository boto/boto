from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.vpc import VPCConnection, Endpoint

class TestCreateEndpoint(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return b"""
            <CreateVpcEndpointResponse xmlns="http://ec2.amazonaws.com/doc/2015-04-15/">
                <requestId>fb034913-9f96-45d6-acf6-3cb703860ac9</requestId>
                <vpcEndpoint>
                    <vpcId>vpc-12b0b677</vpcId>
                    <state>available</state>
                    <routeTableIdSet>
                         <item>rtb-11aa22bb</item>
                    </routeTableIdSet>
                    <vpcEndpointId>vpce-0213f76b</vpcEndpointId>
                    <creationTimestamp>2015-06-13T22:51:16Z</creationTimestamp>
                    <policyDocument>{"Version":"2008-10-17","Statement":[{"Sid":"","Effect":"Allow","Principal":"*","Action":"*","Resource":"*"}]}</policyDocument>
                    <serviceName>com.amazonaws.us-east-1.s3</serviceName>
                </vpcEndpoint>
            </CreateVpcEndpointResponse>
        """

    def test_create_endpoint(self):
        self.set_http_response(status_code=200)
        api_response = self.service_connection.create_endpoint('vpc-12b0b677', 'com.amazonaws.us-east-1.s3')
        self.assert_request_parameters({
            'Action': 'CreateVpcEndpoint',
            'ServiceName': 'com.amazonaws.us-east-1.s3',
            'VpcId': 'vpc-12b0b677'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertIsInstance(api_response, Endpoint)
        self.assertEquals(api_response.id, 'vpce-0213f76b')
        self.assertEquals(api_response.policy_document, '{"Version":"2008-10-17","Statement":[{"Sid":"","Effect":"Allow","Principal":"*","Action":"*","Resource":"*"}]}')


class TestModifyEndoint(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return b"""
            <ModifyVpcEndpointResponse xmlns="http://ec2.amazonaws.com/doc/2015-04-15/">
                <return>true</return>
                <requestId>125acea6-ba5c-4c6e-8e17-example</requestId>
            </ModifyVpcEndpointResponse>
        """
    def test_modify_endpoint(self):
        self.set_http_response(status_code=200)
        api_response = self.service_connection.modify_endpoint('vpce-0213f76b')
        self.assert_request_parameters({
            'Action': 'ModifyVpcEndpoint',
            'VpcEndpointId': 'vpce-0213f76b'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertNotEquals(api_response, 'true')

class TestGetAllEndpoints(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return b"""
            <DescribeVpcEndpointsResponse xmlns="http://ec2.amazonaws.com/doc/2015-04-15/">
                <vpcEndpointSet>
                    <item>
                        <vpcId>vpc-1a2b3c4d</vpcId>
                        <state>available</state>
                        <routeTableIdSet>
                            <item>rtb-123abc12</item>
                            <item>rtb-abc123ab</item>
                        </routeTableIdSet>
                        <vpcEndpointId>vpce-abc12345</vpcEndpointId>
                        <creationTimestamp>2015-02-20T15:30:56Z</creationTimestamp>
                        <policyDocument>{"Version":"2012-10-17","Statement":[{"Sid":"","Effect":"Deny","Principal":"*","Action":"*","Resource":"*"}]}</policyDocument>
                        <serviceName>com.amazonaws.us-west-1.s3</serviceName>
                    </item>
            `    </vpcEndpointSet>
                <requestId>176371a7-3307-4516-95eb-example</requestId>
            </DescribeVpcEndpointsResponse>
        """

    def test_get_all_vpc_endpoints(self):
        self.set_http_response(status_code=200)
        api_response = self.service_connection.get_all_endpoints()
        self.assert_request_parameters({
            'Action': 'DescribeVpcEndpoints'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertEquals(len(api_response), 1)
        self.assertIsInstance(api_response[0], Endpoint)
        self.assertEquals(api_response[0].id, 'vpce-abc12345')
        self.assertEquals(api_response[0].state, 'available')
        self.assertEquals(len(api_response[0].routetables), 2) 
        self.assertEquals(api_response[0].routetables[0], 'rtb-123abc12')
        self.assertEquals(api_response[0].routetables[1], 'rtb-abc123ab')
        self.assertEquals(api_response[0].id, 'vpce-abc12345')
 
class TestDeleteEndpoint(AWSMockServiceTestCase):

    connection_class = VPCConnection

    def default_body(self):
        return b"""
          <DeleteVpcEndpointsResponse xmlns="http://ec2.amazonaws.com/doc/2015-04-15/">
            <unsuccessful/>
            <requestId>b59c2643-789a-4bf7-aac4-example</requestId>
          </DeleteVpcEndpointsResponse>
        """
    def test_destroy_endpoint(self):
        self.set_http_response(status_code=200)
        api_response = self.service_connection.delete_endpoints('vpce-0213f76b')
        self.assert_request_parameters({
            'Action': 'DeleteVpcEndpoints',
            'VpcEndpointId.1': 'vpce-0213f76b'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertNotEquals(api_response, 'true')

if __name__ == '__main__':
    unittest.main()
