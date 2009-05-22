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
                 min_size=None, max_size=None):
        """
        Creates a new AutoScalingGroup with the specified name.

        You must not have already used up your entire quota of
        AutoScalingGroups in order for this call to be successful. Once the
        creation request is completed, the AutoScalingGroup is ready to be
        used in other calls.

        @type name: str
        @param name: Name of autoscaling group.

        @type availability_zone: str
        @param availability_zone: An availability zone.

        @type launch_config: str
        @param launch_config: Name of launch configuration name.

        @type load_balancers: list
        @param load_balancers: List of load balancers.

        @type minsize: int
        @param minsize: Minimum size of group

        @type maxsize: int
        @param maxsize: Maximum size of group

        @type cooldown: int
        @param cooldown: Amount of time after a Scaling Activity completes
                         before any further scaling activities can start.

        @rtype: tuple
        @return: Updated healthcheck for the instances.
        """
        self.name = group_name
        self.connection = connection
        self.min_size = None
        self.max_size = None
        self.created_time = None
        self.cooldown = None
        self.launch_config = None
        self.desired_capacity = None
        self.availability_zone = None
        self.instances = None

    def __repr__(self):
        return 'AutoScalingGroup:%s' % self.name

    def startElement(self, name, attrs, connection):
        if name == 'Instances':
            self.instances = ResultSet([('member', Instance)])
            return self.instances
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
        self.last_request = req

    def update(self):
        """ Sync local changes with AutoScaling group. """
        return self._update_group('UpdateAutoScalingGroup', self)

    def get_all_triggers(self):
        """ Get all triggers for this auto scaling group. """
        params = {'AutoScalingGroupName' : self.name}
        triggers = self.get_list('DescribeTriggers', params,
                                 [('member', Trigger)])
        self.triggers = triggers
        return triggers

    def delete(self):
        """ Delete this auto-scaling group. """
        params = {'AutoScalingGroupName' : self.name}
        return self.connection.get_object('DeleteAutoScalingGroup', params,
                                          Request)
