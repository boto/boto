from tests.unit import unittest
from tests.compat import mock

from boto.ec2.elb import ELBConnection
from boto.ec2.elb import LoadBalancer
from boto.ec2.elb.tag import LbTagSet


TAG_GET_TRUE_RESPONSE = b"""
<DescribeTagsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeTagsResult>
    <TagDescriptions>
      <member>
        <Tags>
          <member>
            <Value>lima</Value>
            <Key>project</Key>
          </member>
          <member>
            <Value>digital-media</Value>
            <Key>department</Key>
          </member>
        </Tags>
        <LoadBalancerName>my-test-loadbalancer</LoadBalancerName>
      </member>
    </TagDescriptions>
  </DescribeTagsResult>
  <ResponseMetadata>
    <RequestId>07b1ecbc-1100-11e3-acaf-dd7edEXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeTagsResponse>
"""

TAG_GET_TRUE_EMPTY_RESPONSE = b"""
<DescribeTagsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeTagsResult>
    <TagDescriptions>
      <member>
        <Tags/>
        <LoadBalancerName>my-test-loadbalancer</LoadBalancerName>
      </member>
    </TagDescriptions>
  </DescribeTagsResult>
  <ResponseMetadata>
    <RequestId>07b1ecbc-1100-11e3-acaf-dd7edEXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeTagsResponse>
"""


TAGS_TEST = [
    (TAG_GET_TRUE_RESPONSE,
    [('project', 'lima'), ('department', 'digital-media')]),
    (TAG_GET_TRUE_EMPTY_RESPONSE,
    [])
]

class TestLbTag(unittest.TestCase):
    """Tests LB Attributes."""
    def _setup_mock(self):
        """Sets up a mock elb request.
        Returns: response, elb connection and LoadBalancer
        """
        mock_response = mock.Mock()
        mock_response.status = 200
        elb = ELBConnection(aws_access_key_id='aws_access_key_id',
                            aws_secret_access_key='aws_secret_access_key')
        elb.make_request = mock.Mock(return_value=mock_response)
        return mock_response, elb, LoadBalancer(elb, 'test_elb')

    def test_get_all_lb_tags(self):
        """Tests getting LbAttribute from elb.connection."""
        mock_response, elb, _ = self._setup_mock()

        for response, tags_test in TAGS_TEST:
            mock_response.read.return_value = response
            #import pdb; pdb.set_trace()
            tags = elb.get_all_lb_tags('test_elb')
            self.assertTrue(isinstance(tags, LbTagSet))
            self.assertEqual(tags.items(), tags_test)

    def test_lb_get_tags(self):
        """Tests getting LbTagSet from ELB object."""
        mock_response, _, lb = self._setup_mock()

        for response, tags_test in TAGS_TEST:
            mock_response.read.return_value = response
            tags = lb.get_tags(force=True)
            self.assertTrue(isinstance(tags, LbTagSet))
            self.assertEqual(tags.items(), tags_test)

if __name__ == '__main__':
    unittest.main()
