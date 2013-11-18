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

from datetime import datetime

from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale.group import AutoScalingGroup
from boto.ec2.autoscale.policy import ScalingPolicy
from boto.ec2.autoscale.tag import Tag

from boto.ec2.blockdevicemapping import EBSBlockDeviceType, BlockDeviceMapping

from boto.ec2.autoscale import launchconfig

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

class TestScheduledGroup(AWSMockServiceTestCase):
    connection_class = AutoScaleConnection

    def setUp(self):
        super(TestScheduledGroup, self).setUp()

    def default_body(self):
        return """
            <PutScheduledUpdateGroupActionResponse>
                <ResponseMetadata>
                  <RequestId>requestid</RequestId>
                </ResponseMetadata>
            </PutScheduledUpdateGroupActionResponse>
        """

    def test_scheduled_group_creation(self):
        self.set_http_response(status_code=200)
        self.service_connection.create_scheduled_group_action('foo',
                                                              'scheduled-foo',
                                                              desired_capacity=1,
                                                              start_time=datetime(2013, 1, 1, 22, 55, 31),
                                                              end_time=datetime(2013, 2, 1, 22, 55, 31),
                                                              min_size=1,
                                                              max_size=2,
                                                              recurrence='0 10 * * *')
        self.assert_request_parameters({
            'Action': 'PutScheduledUpdateGroupAction',
            'AutoScalingGroupName': 'foo',
            'ScheduledActionName': 'scheduled-foo',
            'MaxSize': 2,
            'MinSize': 1,
            'DesiredCapacity': 1,
            'EndTime': '2013-02-01T22:55:31',
            'StartTime': '2013-01-01T22:55:31',
            'Recurrence': '0 10 * * *',
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

class TestLaunchConfiguration(AWSMockServiceTestCase):
    connection_class = AutoScaleConnection

    def default_body(self):
        # This is a dummy response
        return """
        <DescribeLaunchConfigurationsResponse>
        </DescribeLaunchConfigurationsResponse>
        """

    def test_launch_config(self):
        # This unit test is based on #753 and #1343
        self.set_http_response(status_code=200)
        dev_sdf = EBSBlockDeviceType(snapshot_id='snap-12345')
        dev_sdg = EBSBlockDeviceType(snapshot_id='snap-12346')

        bdm = BlockDeviceMapping()
        bdm['/dev/sdf'] = dev_sdf
        bdm['/dev/sdg'] = dev_sdg

        lc = launchconfig.LaunchConfiguration(
                connection=self.service_connection,
                name='launch_config',
                image_id='123456',
                instance_type = 'm1.large',
                security_groups = ['group1', 'group2'],
                spot_price='price',
                block_device_mappings = [bdm],
                associate_public_ip_address = True
                )

        response = self.service_connection.create_launch_configuration(lc)

        self.assert_request_parameters({
            'Action': 'CreateLaunchConfiguration',
            'BlockDeviceMappings.member.1.DeviceName': '/dev/sdf',
            'BlockDeviceMappings.member.1.Ebs.DeleteOnTermination': 'false',
            'BlockDeviceMappings.member.1.Ebs.SnapshotId': 'snap-12345',
            'BlockDeviceMappings.member.2.DeviceName': '/dev/sdg',
            'BlockDeviceMappings.member.2.Ebs.DeleteOnTermination': 'false',
            'BlockDeviceMappings.member.2.Ebs.SnapshotId': 'snap-12346',
            'EbsOptimized': 'false',
            'LaunchConfigurationName': 'launch_config',
            'ImageId': '123456',
            'InstanceMonitoring.Enabled': 'false',
            'InstanceType': 'm1.large',
            'SecurityGroups.member.1': 'group1',
            'SecurityGroups.member.2': 'group2',
            'SpotPrice': 'price',
            'AssociatePublicIpAddress' : 'true'
        }, ignore_params_values=['Version'])


class TestCreateAutoScalePolicy(AWSMockServiceTestCase):
    connection_class = AutoScaleConnection

    def setUp(self):
        super(TestCreateAutoScalePolicy, self).setUp()

    def default_body(self):
        return """
            <PutScalingPolicyResponse xmlns="http://autoscaling.amazonaws.com\
            /doc/2011-01-01/">
              <PutScalingPolicyResult>
                <PolicyARN>arn:aws:autoscaling:us-east-1:803981987763:scaling\
                Policy:b0dcf5e8
            -02e6-4e31-9719-0675d0dc31ae:autoScalingGroupName/my-test-asg:\
            policyName/my-scal
            eout-policy</PolicyARN>
              </PutScalingPolicyResult>
              <ResponseMetadata>
                <RequestId>3cfc6fef-c08b-11e2-a697-2922EXAMPLE</RequestId>
              </ResponseMetadata>
            </PutScalingPolicyResponse>
        """

    def test_scaling_policy_with_min_adjustment_step(self):
        self.set_http_response(status_code=200)

        policy = ScalingPolicy(
            name='foo', as_name='bar',
            adjustment_type='PercentChangeInCapacity', scaling_adjustment=50,
            min_adjustment_step=30)
        self.service_connection.create_scaling_policy(policy)

        self.assert_request_parameters({
            'Action': 'PutScalingPolicy',
            'PolicyName': 'foo',
            'AutoScalingGroupName': 'bar',
            'AdjustmentType': 'PercentChangeInCapacity',
            'ScalingAdjustment': 50,
            'MinAdjustmentStep': 30
        }, ignore_params_values=['Version'])

    def test_scaling_policy_with_wrong_adjustment_type(self):
        self.set_http_response(status_code=200)

        policy = ScalingPolicy(
            name='foo', as_name='bar',
            adjustment_type='ChangeInCapacity', scaling_adjustment=50,
            min_adjustment_step=30)
        self.service_connection.create_scaling_policy(policy)

        self.assert_request_parameters({
            'Action': 'PutScalingPolicy',
            'PolicyName': 'foo',
            'AutoScalingGroupName': 'bar',
            'AdjustmentType': 'ChangeInCapacity',
            'ScalingAdjustment': 50
        }, ignore_params_values=['Version'])

    def test_scaling_policy_without_min_adjustment_step(self):
        self.set_http_response(status_code=200)

        policy = ScalingPolicy(
            name='foo', as_name='bar',
            adjustment_type='PercentChangeInCapacity', scaling_adjustment=50)
        self.service_connection.create_scaling_policy(policy)

        self.assert_request_parameters({
            'Action': 'PutScalingPolicy',
            'PolicyName': 'foo',
            'AutoScalingGroupName': 'bar',
            'AdjustmentType': 'PercentChangeInCapacity',
            'ScalingAdjustment': 50
        }, ignore_params_values=['Version'])


class TestPutNotificationConfiguration(AWSMockServiceTestCase):
    connection_class = AutoScaleConnection

    def setUp(self):
        super(TestPutNotificationConfiguration, self).setUp()

    def default_body(self):
        return """
            <PutNotificationConfigurationResponse>
              <ResponseMetadata>
                <RequestId>requestid</RequestId>
              </ResponseMetadata>
            </PutNotificationConfigurationResponse>
        """

    def test_autoscaling_group_put_notification_configuration(self):
        self.set_http_response(status_code=200)
        autoscale = AutoScalingGroup(
            name='ana', launch_config='lauch_config',
            min_size=1, max_size=2,
            termination_policies=['OldestInstance', 'OldestLaunchConfiguration'])
        self.service_connection.put_notification_configuration(autoscale, 'arn:aws:sns:us-east-1:19890506:AutoScaling-Up', ['autoscaling:EC2_INSTANCE_LAUNCH'])
        self.assert_request_parameters({
            'Action': 'PutNotificationConfiguration',
            'AutoScalingGroupName': 'ana',
            'NotificationTypes.member.1': 'autoscaling:EC2_INSTANCE_LAUNCH',
            'TopicARN': 'arn:aws:sns:us-east-1:19890506:AutoScaling-Up',
        }, ignore_params_values=['Version'])


class TestDeleteNotificationConfiguration(AWSMockServiceTestCase):
    connection_class = AutoScaleConnection

    def setUp(self):
        super(TestDeleteNotificationConfiguration, self).setUp()

    def default_body(self):
        return """
            <DeleteNotificationConfigurationResponse>
              <ResponseMetadata>
                <RequestId>requestid</RequestId>
              </ResponseMetadata>
            </DeleteNotificationConfigurationResponse>
        """

    def test_autoscaling_group_put_notification_configuration(self):
        self.set_http_response(status_code=200)
        autoscale = AutoScalingGroup(
            name='ana', launch_config='lauch_config',
            min_size=1, max_size=2,
            termination_policies=['OldestInstance', 'OldestLaunchConfiguration'])
        self.service_connection.delete_notification_configuration(autoscale, 'arn:aws:sns:us-east-1:19890506:AutoScaling-Up')
        self.assert_request_parameters({
            'Action': 'DeleteNotificationConfiguration',
            'AutoScalingGroupName': 'ana',
            'TopicARN': 'arn:aws:sns:us-east-1:19890506:AutoScaling-Up',
        }, ignore_params_values=['Version'])

class TestAutoScalingTag(AWSMockServiceTestCase):
    connection_class = AutoScaleConnection

    def default_body(self):
        return """
        <CreateOrUpdateTagsResponse>
            <ResponseMetadata>
                <RequestId>requestId</RequestId>
            </ResponseMetadata>
        </CreateOrUpdateTagsResponse>
        """

    def test_create_or_update_tags(self):
        self.set_http_response(status_code=200)

        tags = [
            Tag(
                connection=self.service_connection,
                key='alpha',
                value='tango',
                resource_id='sg-00000000',
                resource_type='auto-scaling-group',
                propagate_at_launch=True
                ),
            Tag(
                connection=self.service_connection,
                key='bravo',
                value='sierra',
                resource_id='sg-00000000',
                resource_type='auto-scaling-group',
                propagate_at_launch=False
                )]
               

        response = self.service_connection.create_or_update_tags(tags)

        self.assert_request_parameters({
            'Action': 'CreateOrUpdateTags',
            'Tags.member.1.ResourceType': 'auto-scaling-group',
            'Tags.member.1.ResourceId': 'sg-00000000',
            'Tags.member.1.Key': 'alpha',
            'Tags.member.1.Value': 'tango',
            'Tags.member.1.PropagateAtLaunch': 'true',
            'Tags.member.2.ResourceType': 'auto-scaling-group',
            'Tags.member.2.ResourceId': 'sg-00000000',
            'Tags.member.2.Key': 'bravo',
            'Tags.member.2.Value': 'sierra',
            'Tags.member.2.PropagateAtLaunch': 'false'
        }, ignore_params_values=['Version'])

    def test_endElement(self):
        for i in [
            ('Key', 'mykey', 'key'),
            ('Value', 'myvalue', 'value'),
            ('ResourceType', 'auto-scaling-group', 'resource_type'),
            ('ResourceId', 'sg-01234567', 'resource_id'),
            ('PropagateAtLaunch', 'true', 'propagate_at_launch')]:
                self.check_tag_attributes_set(i[0], i[1], i[2])
            
             
    def check_tag_attributes_set(self, name, value, attr):
        tag = Tag()
        tag.endElement(name, value, None)
        if value == 'true':
            self.assertEqual(getattr(tag, attr), True)
        else:
            self.assertEqual(getattr(tag, attr), value)
>>>>>>> upstream/develop

if __name__ == '__main__':
    unittest.main()
