# Copyright (c) 2010 Spotify AB
# Copyright (c) 2010 Jeremy Thurgood <firxen+boto@gmail.com>
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
This module contains EMR response objects
"""

from boto.resultset import ResultSet


class EmrObject(object):
    Fields = set()

    def __init__(self, connection=None):
        self.connection = connection

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name in self.Fields:
            setattr(self, name.lower(), value)


class RunJobFlowResponse(EmrObject):
    Fields = set(['JobFlowId'])


class Arg(EmrObject):
    def __init__(self, connection=None):
        self.value = None

    def endElement(self, name, value, connection):
        self.value = value


class BootstrapAction(EmrObject):
    Fields = set(['Name',
                  'Args',
                  'Path'])


class Step(EmrObject):
    Fields = set(['Name',
                  'ActionOnFailure',
                  'CreationDateTime',
                  'StartDateTime',
                  'EndDateTime',
                  'LastStateChangeReason',
                  'State'])

    def __init__(self, connection=None):
        self.connection = connection
        self.args = None

    def startElement(self, name, attrs, connection):
        if name == 'Args':
            self.args = ResultSet([('member', Arg)])
            return self.args


class InstanceGroup(EmrObject):
    Fields = set(['Name',
                  'CreationDateTime',
                  'InstanceRunningCount',
                  'StartDateTime',
                  'ReadyDateTime',
                  'State',
                  'EndDateTime',
                  'InstanceRequestCount',
                  'InstanceType',
                  'Market',
                  'LastStateChangeReason',
                  'InstanceRole',
                  'InstanceGroupId',
                  'LaunchGroup',
                  'SpotPrice'])


class JobFlow(EmrObject):
    Fields = set(['CreationDateTime',
                  'StartDateTime',
                  'State',
                  'EndDateTime',
                  'Id',
                  'InstanceCount',
                  'JobFlowId',
                  'LogUri',
                  'MasterPublicDnsName',
                  'MasterInstanceId',
                  'Name',
                  'Placement',
                  'RequestId',
                  'Type',
                  'Value',
                  'AvailabilityZone',
                  'SlaveInstanceType',
                  'MasterInstanceType',
                  'Ec2KeyName',
                  'InstanceCount',
                  'KeepJobFlowAliveWhenNoSteps',
                  'LastStateChangeReason'])

    def __init__(self, connection=None):
        self.connection = connection
        self.steps = None
        self.instancegroups = None
        self.bootstrapactions = None

    def startElement(self, name, attrs, connection):
        if name == 'Steps':
            self.steps = ResultSet([('member', Step)])
            return self.steps
        elif name == 'InstanceGroups':
            self.instancegroups = ResultSet([('member', InstanceGroup)])
            return self.instancegroups
        elif name == 'BootstrapActions':
            self.bootstrapactions = ResultSet([('member', BootstrapAction)])
            return self.bootstrapactions
        else:
            return None

