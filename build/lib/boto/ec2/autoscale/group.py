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

import weakref

from boto.ec2.elb.listelement import ListElement
from boto.resultset import ResultSet
from boto.ec2.autoscale.trigger import Trigger
from boto.ec2.autoscale.request import Request

class Instance(object):
    def __init__(self, connection=None):
        self.connection = connection
        self.instance_id = ''

    def __repr__(self):
        return 'Instance:%s' % self.instance_id

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'InstanceId':
            self.instance_id = value
        else:
            setattr(self, name, value)


class AutoScalingGroup(object):
    def __init__(self, connection=None, group_name=None,
                 availability_zone=None, launch_config=None,
                 availability_zones=None,
                 load_balancers=None, cooldown=0,
                 min_size=None, max_size=None):
        """
        Creates a new AutoScalingGroup with the specified name.

        You must not have already used up your entire quota of
        AutoScalingGroups in order for this call to be successful. Once the
        creation request is completed, the AutoScalingGroup is ready to be
        used in other calls.

        :type name: str
        :param name: Name of autoscaling group.

        :type availability_zone: str
        :param availability_zone: An availability zone. DEPRECATED - use the
                                  availability_zones parameter, which expects
                                  a list of availability zone
                                  strings

        :type availability_zone: list
        :param availability_zone: List of availability zones.

        :type launch_config: str
        :param launch_config: Name of launch configuration name.

        :type load_balancers: list
        :param load_balancers: List of load balancers.

        :type minsize: int
        :param minsize: Minimum size of group

        :type maxsize: int
        :param maxsize: Maximum size of group

        :type cooldown: int
        :param cooldown: Amount of time after a Scaling Activity completes
                         before any further scaling activities can start.

        :rtype: tuple
        :return: Updated healthcheck for the instances.
        """
        self.name = group_name
        self.connection = connection
        self.min_size = min_size
        self.max_size = max_size
        self.created_time = None
        self.cooldown = cooldown
        self.launch_config = launch_config
        if self.launch_config:
            self.launch_config_name = self.launch_config.name
        else:
            self.launch_config_name = None
        self.desired_capacity = None
        lbs = load_balancers or []
        self.load_balancers = ListElement(lbs)
        zones = availability_zones or []
        self.availability_zone = availability_zone
        self.availability_zones = ListElement(zones)
        self.instances = None

    def __repr__(self):
        return 'AutoScalingGroup:%s' % self.name

    def startElement(self, name, attrs, connection):
        if name == 'Instances':
            self.instances = ResultSet([('member', Instance)])
            return self.instances
        elif name == 'LoadBalancerNames':
            return self.load_balancers
        elif name == 'AvailabilityZones':
            return self.availability_zones
        else:
            return

    def endElement(self, name, value, connection):
        if name == 'MinSize':
            self.min_size = value
        elif name == 'CreatedTime':
            self.created_time = value
        elif name == 'Cooldown':
            self.cooldown = value
        elif name == 'LaunchConfigurationName':
            self.launch_config_name = value
        elif name == 'DesiredCapacity':
            self.desired_capacity = value
        elif name == 'MaxSize':
            self.max_size = value
        elif name == 'AutoScalingGroupName':
            self.name = value
        else:
            setattr(self, name, value)

    def set_capacity(self, capacity):
        """ Set the desired capacity for the group. """
        params = {
                  'AutoScalingGroupName' : self.name,
                  'DesiredCapacity'      : capacity,
                 }
        req = self.connection.get_object('SetDesiredCapacity', params,
                                            Request)
        self.connection.last_request = req
        return req

    def update(self):
        """ Sync local changes with AutoScaling group. """
        return self.connection._update_group('UpdateAutoScalingGroup', self)

    def shutdown_instances(self):
        """ Convenience method which shuts down all instances associated with
        this group.
        """
        self.min_size = 0
        self.max_size = 0
        self.update()

    def get_all_triggers(self):
        """ Get all triggers for this auto scaling group. """
        params = {'AutoScalingGroupName' : self.name}
        triggers = self.connection.get_list('DescribeTriggers', params,
                                            [('member', Trigger)])

        # allow triggers to be able to access the autoscale group
        for tr in triggers:
            tr.autoscale_group = weakref.proxy(self)

        return triggers

    def delete(self):
        """ Delete this auto-scaling group. """
        params = {'AutoScalingGroupName' : self.name}
        return self.connection.get_object('DeleteAutoScalingGroup', params,
                                          Request)

    def get_activities(self, activity_ids=None, max_records=100):
        """
        Get all activies for this group.
        """
        return self.connection.get_all_activities(self, activity_ids, max_records)

