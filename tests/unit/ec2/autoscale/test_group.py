#!/usr/bin/env python
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#

from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale.group import AutoScalingGroup


class TestAutoScaleGroup(AWSMockServiceTestCase):
    connection_class = AutoScaleConnection

    def setUp(self):
        super(TestAutoScaleGroup, self).setUp()

    def default_body(self):
        return """
            <CreateLaunchConfigurationResponse>
              <ResponseMetadata>
                <RequestId>requestid</RequestId>
              </ResponseMetadata>
            </CreateLaunchConfigurationResponse>
        """

    def test_autoscaling_group_with_termination_policies(self):
        self.set_http_response(status_code=200)
        autoscale = AutoScalingGroup(
            name='foo', launch_config='lauch_config',
            min_size=1, max_size=2,
            termination_policies=['OldestInstance', 'OldestLaunchConfiguration'])
        self.service_connection.create_auto_scaling_group(autoscale)
        self.assert_request_parameters({
            'Action': 'CreateAutoScalingGroup',
            'AutoScalingGroupName': 'foo',
            'LaunchConfigurationName': 'lauch_config',
            'MaxSize': 2,
            'MinSize': 1,
            'TerminationPolicies.member.1': 'OldestInstance',
            'TerminationPolicies.member.2': 'OldestLaunchConfiguration',
        }, ignore_params_values=['Version'])


class TestParseAutoScaleGroupResponse(AWSMockServiceTestCase):
    connection_class = AutoScaleConnection

    def default_body(self):
        return """
          <DescribeAutoScalingGroupsResult>
             <AutoScalingGroups>
               <member>
                 <Tags/>
                 <SuspendedProcesses/>
                 <AutoScalingGroupName>test_group</AutoScalingGroupName>
                 <HealthCheckType>EC2</HealthCheckType>
                 <CreatedTime>2012-09-27T20:19:47.082Z</CreatedTime>
                 <EnabledMetrics/>
                 <LaunchConfigurationName>test_launchconfig</LaunchConfigurationName>
                 <Instances>
                   <member>
                     <HealthStatus>Healthy</HealthStatus>
                     <AvailabilityZone>us-east-1a</AvailabilityZone>
                     <InstanceId>i-z118d054</InstanceId>
                     <LaunchConfigurationName>test_launchconfig</LaunchConfigurationName>
                     <LifecycleState>InService</LifecycleState>
                   </member>
                 </Instances>
                 <DesiredCapacity>1</DesiredCapacity>
                 <AvailabilityZones>
                   <member>us-east-1c</member>
                   <member>us-east-1a</member>
                 </AvailabilityZones>
                 <LoadBalancerNames/>
                 <MinSize>1</MinSize>
                 <VPCZoneIdentifier/>
                 <HealthCheckGracePeriod>0</HealthCheckGracePeriod>
                 <DefaultCooldown>300</DefaultCooldown>
                 <AutoScalingGroupARN>myarn</AutoScalingGroupARN>
                 <TerminationPolicies>
                   <member>OldestInstance</member>
                   <member>OldestLaunchConfiguration</member>
                 </TerminationPolicies>
                 <MaxSize>2</MaxSize>
               </member>
             </AutoScalingGroups>
          </DescribeAutoScalingGroupsResult>
        """

    def test_get_all_groups_is_parsed_correctly(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.get_all_groups(names=['test_group'])
        self.assertEqual(len(response), 1, response)
        as_group = response[0]
        self.assertEqual(as_group.availability_zones, ['us-east-1c', 'us-east-1a'])
        self.assertEqual(as_group.default_cooldown, 300)
        self.assertEqual(as_group.desired_capacity, 1)
        self.assertEqual(as_group.enabled_metrics, [])
        self.assertEqual(as_group.health_check_period, 0)
        self.assertEqual(as_group.health_check_type, 'EC2')
        self.assertEqual(as_group.launch_config_name, 'test_launchconfig')
        self.assertEqual(as_group.load_balancers, [])
        self.assertEqual(as_group.min_size, 1)
        self.assertEqual(as_group.max_size, 2)
        self.assertEqual(as_group.name, 'test_group')
        self.assertEqual(as_group.suspended_processes, [])
        self.assertEqual(as_group.tags, [])
        self.assertEqual(as_group.termination_policies,
                         ['OldestInstance', 'OldestLaunchConfiguration'])


class TestDescribeTerminationPolicies(AWSMockServiceTestCase):
    connection_class = AutoScaleConnection

    def default_body(self):
        return """
          <DescribeTerminationPolicyTypesResponse>
            <DescribeTerminationPolicyTypesResult>
              <TerminationPolicyTypes>
                <member>ClosestToNextInstanceHour</member>
                <member>Default</member>
                <member>NewestInstance</member>
                <member>OldestInstance</member>
                <member>OldestLaunchConfiguration</member>
              </TerminationPolicyTypes>
            </DescribeTerminationPolicyTypesResult>
            <ResponseMetadata>
              <RequestId>requestid</RequestId>
            </ResponseMetadata>
          </DescribeTerminationPolicyTypesResponse>
        """

    def test_autoscaling_group_with_termination_policies(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.get_termination_policies()
        self.assertListEqual(
            response,
            ['ClosestToNextInstanceHour', 'Default',
             'NewestInstance', 'OldestInstance', 'OldestLaunchConfiguration'])


if __name__ == '__main__':
    unittest.main()
