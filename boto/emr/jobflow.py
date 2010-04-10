# Copyright (c) 2010 Spotify AB
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

from boto.emr.emrobject import EmrObject
from boto.resultset import ResultSet

class RunJobFlowResponse(EmrObject):
    Fields = set(['JobFlowId'])

class Arg(EmrObject):
    def __init__(self, connection=None):
        self.value = None

    def endElement(self, name, value, connection):
        self.value = value


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
 

class JobFlow(EmrObject):
    Fields = set(['CreationDateTime',
                  'StartDateTime',
                  'State',
                  'EndDateTime',
                  'Id',
                  'InstanceCount',
                  'JobFlowId',
                  'KeepJobAliveWhenNoSteps',
                  'LogURI',
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
                  'KeepJobFlowAliveWhenNoSteps'])

    def __init__(self, connection=None):
        self.connection = connection
        self.steps = None

    def startElement(self, name, attrs, connection):
        if name == 'Steps':
            self.steps = ResultSet([('member', Step)])
            return self.steps
        else:
            return None

