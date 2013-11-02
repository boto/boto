from tests.unit import AWSMockServiceTestCase

from boto.ec2.connection import EC2Connection


class TestCancelSpotInstanceRequests(AWSMockServiceTestCase):

    connection_class = EC2Connection

    def default_body(self):
        return """
            <CancelSpotInstanceRequestsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-01/">
              <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
              <spotInstanceRequestSet>
                <item>
                  <spotInstanceRequestId>sir-1a2b3c4d</spotInstanceRequestId>
                  <state>cancelled</state>
                </item>
                <item>
                  <spotInstanceRequestId>sir-9f8e7d6c</spotInstanceRequestId>
                  <state>cancelled</state>
                </item>
              </spotInstanceRequestSet>
            </CancelSpotInstanceRequestsResponse>
        """

    def test_cancel_spot_instance_requests(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.cancel_spot_instance_requests(['sir-1a2b3c4d',
                                                                          'sir-9f8e7d6c'])
        self.assert_request_parameters({
            'Action': 'CancelSpotInstanceRequests',
            'SpotInstanceRequestId.1': 'sir-1a2b3c4d',
            'SpotInstanceRequestId.2': 'sir-9f8e7d6c'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])
        self.assertEqual(len(response), 2)
        self.assertEqual(response[0].id, 'sir-1a2b3c4d')
        self.assertEqual(response[0].state, 'cancelled')
        self.assertEqual(response[1].id, 'sir-9f8e7d6c')
        self.assertEqual(response[1].state, 'cancelled')
