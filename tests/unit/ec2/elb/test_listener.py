#!/usr/bin/env python
import xml.sax
from tests.unit import unittest

import boto.resultset
from boto.ec2.elb.loadbalancer import LoadBalancer


LISTENERS_RESPONSE = r"""<?xml version="1.0" encoding="UTF-8"?>
<DescribeLoadBalancersResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeLoadBalancersResult>
    <LoadBalancerDescriptions>
      <member>
        <SecurityGroups/>
        <CreatedTime>2013-07-09T19:18:00.520Z</CreatedTime>
        <LoadBalancerName>elb-boto-unit-test</LoadBalancerName>
        <HealthCheck>
          <Interval>30</Interval>
          <Target>TCP:8000</Target>
          <HealthyThreshold>10</HealthyThreshold>
          <Timeout>5</Timeout>
          <UnhealthyThreshold>2</UnhealthyThreshold>
        </HealthCheck>
        <ListenerDescriptions>
          <member>
            <PolicyNames/>
            <Listener>
              <Protocol>HTTP</Protocol>
              <LoadBalancerPort>80</LoadBalancerPort>
              <InstanceProtocol>HTTP</InstanceProtocol>
              <InstancePort>8000</InstancePort>
            </Listener>
          </member>
          <member>
            <PolicyNames/>
            <Listener>
              <Protocol>HTTP</Protocol>
              <LoadBalancerPort>8080</LoadBalancerPort>
              <InstanceProtocol>HTTP</InstanceProtocol>
              <InstancePort>80</InstancePort>
            </Listener>
          </member>
          <member>
            <PolicyNames/>
            <Listener>
              <Protocol>TCP</Protocol>
              <LoadBalancerPort>2525</LoadBalancerPort>
              <InstanceProtocol>TCP</InstanceProtocol>
              <InstancePort>25</InstancePort>
            </Listener>
          </member>
        </ListenerDescriptions>
        <Instances/>
        <Policies>
          <AppCookieStickinessPolicies/>
          <OtherPolicies/>
          <LBCookieStickinessPolicies/>
        </Policies>
        <AvailabilityZones>
          <member>us-east-1a</member>
        </AvailabilityZones>
        <CanonicalHostedZoneName>elb-boto-unit-test-408121642.us-east-1.elb.amazonaws.com</CanonicalHostedZoneName>
        <CanonicalHostedZoneNameID>Z3DZXE0Q79N41H</CanonicalHostedZoneNameID>
        <Scheme>internet-facing</Scheme>
        <SourceSecurityGroup>
          <OwnerAlias>amazon-elb</OwnerAlias>
          <GroupName>amazon-elb-sg</GroupName>
        </SourceSecurityGroup>
        <DNSName>elb-boto-unit-test-408121642.us-east-1.elb.amazonaws.com</DNSName>
        <BackendServerDescriptions/>
        <Subnets/>
      </member>
    </LoadBalancerDescriptions>
  </DescribeLoadBalancersResult>
  <ResponseMetadata>
    <RequestId>5763d932-e8cc-11e2-a940-11136cceffb8</RequestId>
  </ResponseMetadata>
</DescribeLoadBalancersResponse>
"""


class TestListenerResponseParsing(unittest.TestCase):
    def test_parse_complex(self):
        rs = boto.resultset.ResultSet([
          ('member', LoadBalancer)
        ])
        h = boto.handler.XmlHandler(rs, None)
        xml.sax.parseString(LISTENERS_RESPONSE, h)
        listeners = rs[0].listeners
        self.assertEqual(
            sorted([l.get_complex_tuple() for l in listeners]),
            [
                (80, 8000, 'HTTP', 'HTTP'),
                (2525, 25, 'TCP', 'TCP'),
                (8080, 80, 'HTTP', 'HTTP'),
            ]
        )


if __name__ == '__main__':
    unittest.main()
