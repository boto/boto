# Copyright (c) 2009 Reza Lotun http://reza.lotun.name/
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

"""
This module provides an interface to the Elastic Compute Cloud (EC2)
Auto Scaling service.
"""

import boto
from boto.connection import AWSQueryConnection
from boto.ec2.regioninfo import RegionInfo
from boto.ec2.autoscale.request import Request
from boto.ec2.autoscale.trigger import Trigger
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.autoscale.group import AutoScalingGroup
from boto.ec2.autoscale.activity import Activity


class AutoScaleConnection(AWSQueryConnection):
    APIVersion = boto.config.get('Boto', 'autoscale_version', '2009-05-15')
    Endpoint = boto.config.get('Boto', 'autoscale_endpoint',
                               'autoscaling.amazonaws.com')
    DefaultRegionName = 'us-east-1'
    DefaultRegionEndpoint = 'autoscaling.amazonaws.com'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=1,
                 https_connection_factory=None, region=None, path='/'):
        """
        Init method to create a new connection to the AutoScaling service.

        B{Note:} The host argument is overridden by the host specified in the
                 boto configuration file.
        """
        if not region:
            region = RegionInfo(self, self.DefaultRegionName,
                                self.DefaultRegionEndpoint,
                                AutoScaleConnection)
        self.region = region
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
                                    proxy_user, proxy_pass,
                                    self.region.endpoint, debug,
                                    https_connection_factory, path=path)

    def _required_auth_capability(self):
        return ['ec2']

    def build_list_params(self, params, items, label):
        """ items is a list of dictionaries or strings:
                [{'Protocol' : 'HTTP',
                 'LoadBalancerPort' : '80',
                 'InstancePort' : '80'},..] etc.
             or
                ['us-east-1b',...]
        """
        # different from EC2 list params
        for i in xrange(1, len(items)+1):
            if isinstance(items[i-1], dict):
                for k, v in items[i-1].iteritems():
                    params['%s.member.%d.%s' % (label, i, k)] = v
            elif isinstance(items[i-1], basestring):
                params['%s.member.%d' % (label, i)] = items[i-1]

    def _update_group(self, op, as_group):
        params = {
                  'AutoScalingGroupName'    : as_group.name,
                  'Cooldown'                : as_group.cooldown,
                  'LaunchConfigurationName' : as_group.launch_config_name,
                  'MinSize'                 : as_group.min_size,
                  'MaxSize'                 : as_group.max_size,
                  }
        if op.startswith('Create'):
            if as_group.availability_zones:
                zones = as_group.availability_zones
            else:
                zones = [as_group.availability_zone]
            self.build_list_params(params, as_group.load_balancers,
                                   'LoadBalancerNames')
            self.build_list_params(params, zones,
                                    'AvailabilityZones')
        return self.get_object(op, params, Request)

    def create_auto_scaling_group(self, as_group):
        """
        Create auto scaling group.
        """
        return self._update_group('CreateAutoScalingGroup', as_group)

    def create_launch_configuration(self, launch_config):
        """
        Creates a new Launch Configuration.

        :type launch_config: boto.ec2.autoscale.launchconfig.LaunchConfiguration
        :param launch_config: LaunchConfiguraiton object.

        """
        params = {
                  'ImageId'                 : launch_config.image_id,
                  'KeyName'                 : launch_config.key_name,
                  'LaunchConfigurationName' : launch_config.name,
                  'InstanceType'            : launch_config.instance_type,
                 }
        if launch_config.user_data:
            params['UserData'] = launch_config.user_data
        if launch_config.kernel_id:
            params['KernelId'] = launch_config.kernel_id
        if launch_config.ramdisk_id:
            params['RamdiskId'] = launch_config.ramdisk_id
        if launch_config.block_device_mappings:
            self.build_list_params(params, launch_config.block_device_mappings,
                                   'BlockDeviceMappings')
        self.build_list_params(params, launch_config.security_groups,
                               'SecurityGroups')
        return self.get_object('CreateLaunchConfiguration', params,
                                  Request)

    def create_trigger(self, trigger):
        """

        """
        params = {'TriggerName'                 : trigger.name,
                  'AutoScalingGroupName'        : trigger.autoscale_group.name,
                  'MeasureName'                 : trigger.measure_name,
                  'Statistic'                   : trigger.statistic,
                  'Period'                      : trigger.period,
                  'Unit'                        : trigger.unit,
                  'LowerThreshold'              : trigger.lower_threshold,
                  'LowerBreachScaleIncrement'   : trigger.lower_breach_scale_increment,
                  'UpperThreshold'              : trigger.upper_threshold,
                  'UpperBreachScaleIncrement'   : trigger.upper_breach_scale_increment,
                  'BreachDuration'              : trigger.breach_duration}
        # dimensions should be a list of tuples
        dimensions = []
        for dim in trigger.dimensions:
            name, value = dim
            dimensions.append(dict(Name=name, Value=value))
        self.build_list_params(params, dimensions, 'Dimensions')

        req = self.get_object('CreateOrUpdateScalingTrigger', params,
                               Request)
        return req

    def get_all_groups(self, names=None):
        """
        """
        params = {}
        if names:
            self.build_list_params(params, names, 'AutoScalingGroupNames')
        return self.get_list('DescribeAutoScalingGroups', params,
                             [('member', AutoScalingGroup)])

    def get_all_launch_configurations(self, names=None):
        """
        """
        params = {}
        if names:
            self.build_list_params(params, names, 'LaunchConfigurationNames')
        return self.get_list('DescribeLaunchConfigurations', params,
                             [('member', LaunchConfiguration)])

    def get_all_activities(self, autoscale_group,
                           activity_ids=None,
                           max_records=100):
        """
        Get all activities for the given autoscaling group.

        :type autoscale_group: str or AutoScalingGroup object
        :param autoscale_group: The auto scaling group to get activities on.

        @max_records: int
        :param max_records: Maximum amount of activities to return.
        """
        name = autoscale_group
        if isinstance(autoscale_group, AutoScalingGroup):
            name = autoscale_group.name
        params = {'AutoScalingGroupName' : name}
        if activity_ids:
            self.build_list_params(params, activity_ids, 'ActivityIds')
        return self.get_list('DescribeScalingActivities', params,
                             [('member', Activity)])

    def get_all_triggers(self, autoscale_group):
        params = {'AutoScalingGroupName' : autoscale_group}
        return self.get_list('DescribeTriggers', params,
                             [('member', Trigger)])

    def terminate_instance(self, instance_id, decrement_capacity=True):
        params = {
                  'InstanceId' : instance_id,
                  'ShouldDecrementDesiredCapacity' : decrement_capacity
                  }
        return self.get_object('TerminateInstanceInAutoScalingGroup', params,
                               Activity)

    def set_instance_health(self, instance_id, health_status,
                            should_respect_grace_period=True):
        """
        Explicitly set the health status of an instance.

        :type instance_id: str
        :param instance_id: The identifier of the EC2 instance.

        :type health_status: str
        :param health_status: The health status of the instance.
                              "Healthy" means that the instance is
                              healthy and should remain in service.
                              "Unhealthy" means that the instance is
                              unhealthy. Auto Scaling should terminate
                              and replace it.

        :type should_respect_grace_period: bool
        :param should_respect_grace_period: If True, this call should
                                            respect the grace period
                                            associated with the group.
        """
        params = {'InstanceId' : instance_id,
                  'HealthStatus' : health_status}
        if should_respect_grace_period:
            params['ShouldRespectGracePeriod'] = 'true'
        else:
            params['ShouldRespectGracePeriod'] = 'false'
        return self.get_status('SetInstanceHealth', params)

