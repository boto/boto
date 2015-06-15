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
                    <routeTableIdSet/>
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

if __name__ == '__main__':
    unittest.main()
