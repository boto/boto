from tests.unit import unittest
from tests.compat import mock

from boto.ec2.connection import EC2Connection, Instance

ATTRIBUTE_GET_TRUE_EBSOPTIMIZED_RESPONSE = b"""
<DescribeInstanceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2014-10-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instanceId>i-10a64379</instanceId>
  <ebsOptimized>
    <value>true</value>
  </ebsOptimized>
</DescribeInstanceAttributeResponse>
"""

ATTRIBUTE_GET_FALSE_EBSOPTIMIZED_RESPONSE = b"""
<DescribeInstanceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2014-10-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instanceId>i-10a64379</instanceId>
  <ebsOptimized>
    <value>false</value>
  </ebsOptimized>
</DescribeInstanceAttributeResponse>
"""

ATTRIBUTE_GET_EMPTY_PRODUCTCODES_RESPONSE = b"""
<DescribeInstanceAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2014-10-01/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <instanceId>i-10a64379</instanceId>
  <productCodes/>
</DescribeInstanceAttributeResponse>
"""

# Tests to be run on an InstanceAttributes
# Format:
# (EC2_RESPONSE_STRING, (string_of_attribute_to_test, value) )
ATTRIBUTE_TESTS = [
    (ATTRIBUTE_GET_TRUE_EBSOPTIMIZED_RESPONSE,
     ('ebsOptimized', True)),
    (ATTRIBUTE_GET_FALSE_EBSOPTIMIZED_RESPONSE,
     ('ebsOptimized', False)),
    (ATTRIBUTE_GET_EMPTY_PRODUCTCODES_RESPONSE,
     ('productCodes', None)),
]


class TestInstanceAttributes(unittest.TestCase):
    """Tests Instance Attributes."""
    def _setup_mock(self):
        """Sets up a mock ec2 request.
        Returns: response, ec2 connection and Instance
        """
        mock_response = mock.Mock()
        mock_response.status = 200
        ec2 = EC2Connection(aws_access_key_id='aws_access_key_id',
                            aws_secret_access_key='aws_secret_access_key')
        ec2.make_request = mock.Mock(return_value=mock_response)
        return mock_response, ec2, Instance(ec2)

    def test_instance_get_attributes(self):
        """Tests the InstanceAttributes from the EC2 object."""
        mock_response, _, instance = self._setup_mock()

        for response, attr_test in ATTRIBUTE_TESTS:
            mock_response.read.return_value = response
            expected_value = dict([attr_test])
            actual_value = instance.get_attribute(attr_test[0])
            self.assertEqual(expected_value, actual_value)


if __name__ == '__main__':
    unittest.main()
