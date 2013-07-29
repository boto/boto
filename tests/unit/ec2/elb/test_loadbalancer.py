#!/usr/bin/env python

from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

import mock

from boto.ec2.elb import ELBConnection

DISABLE_RESPONSE = r"""<?xml version="1.0" encoding="UTF-8"?>
<DisableAvailabilityZonesForLoadBalancerResult xmlns="http://ec2.amazonaws.com/doc/2013-02-01/">
    <requestId>3be1508e-c444-4fef-89cc-0b1223c4f02fEXAMPLE</requestId>
    <AvailabilityZones>
        <member>sample-zone</member>
    </AvailabilityZones>
</DisableAvailabilityZonesForLoadBalancerResult>
"""


class TestInstanceStatusResponseParsing(unittest.TestCase):
    def test_next_token(self):
        elb = ELBConnection(aws_access_key_id='aws_access_key_id',
                            aws_secret_access_key='aws_secret_access_key')
        mock_response = mock.Mock()
        mock_response.read.return_value = DISABLE_RESPONSE
        mock_response.status = 200
        elb.make_request = mock.Mock(return_value=mock_response)
        disabled = elb.disable_availability_zones('mine', ['sample-zone'])
        self.assertEqual(disabled, ['sample-zone'])


if __name__ == '__main__':
    unittest.main()
