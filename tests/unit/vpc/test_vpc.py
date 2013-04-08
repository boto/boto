"""
Test module for VPC
"""
from boto.vpc import VPCConnection
import unittest


class TestVPCConnection(unittest.TestCase):
    """
    Test class for `boto.vpc.VPCConnection`
    """

    def setUp(self):
        unittest.TestCase.setUp(self)
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
