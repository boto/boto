# Copyright (c) 2009-2010 Reza Lotun http://reza.lotun.name/
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


from boto.resultset import ResultSet
from boto.ec2.autoscale.request import Request
from boto.ec2.elb.listelement import ListElement


class Alarm(object):
    def __init__(self, connection=None):
        self.connection = connection
        self.name = None
        self.alarm_arn = None

    def __repr__(self):
        return 'Alarm:%s' % self.name

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'AlarmName':
            self.name = value
        elif name == 'AlarmARN':
            self.alarm_arn = value
        else:
            setattr(self, name, value)


class ScalingPolicy(object):
    def __init__(self, connection=None, name=None):
        """
        Scaling Policy

        :type name: str
        :param name: Name of scaling policy
        """
        self.connection = connection
        self.name = name
        self.group_name = None
        self.policy_arn = None
        self.scaling_adjustment = None
        self.cooldown = None
        self.adjustment_type = None
        self.alarms = None

    def __repr__(self):
        return 'ScalingPolicy(%s group:%s adjustment:%s)' % (self.name,
                                                            self.group_name,
                                                            self.adjustment_type)

    def startElement(self, name, attrs, connection):
        if name == 'Alarms':
            self.alrams = ResultSet([('member', Alarm)])
            return self.alarms

    def endElement(self, name, value, connection):
        if name == 'PolicyName':
            self.name = value
        elif name == 'AutoScalingGroupName':
            self.group_name = value
        elif name == 'PolicyARN':
            self.policy_arn = value
        elif name == 'ScalingAdjustment':
            self.scaling_adjustment = value
        elif name == 'Cooldown':
            self.cooldown = int(value)
        elif name == 'AdjustmentType':
            self.adjustment_type = int(value)

