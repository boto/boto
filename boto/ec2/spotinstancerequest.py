# Copyright (c) 2006-2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010, Eucalyptus Systems, Inc.
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
Represents an EC2 Spot Instance Request
"""

from boto.ec2.ec2object import TaggedEC2Object
from boto.ec2.launchspecification import LaunchSpecification


class SpotInstanceStateFault(object):

    def __init__(self, code=None, message=None):
        self.code = code
        self.message = message

    def __repr__(self):
        return '(%s, %s)' % (self.code, self.message)

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'code':
            self.code = value
        elif name == 'message':
            self.message = value
        setattr(self, name, value)


class SpotInstanceRequest(TaggedEC2Object):

    def __init__(self, connection=None):
        TaggedEC2Object.__init__(self, connection)
        self.id = None
        self.price = None
        self.type = None
        self.state = None
        self.fault = None
        self.valid_from = None
        self.valid_until = None
        self.launch_group = None
        self.launched_availability_zone = None
        self.product_description = None
        self.availability_zone_group = None
        self.create_time = None
        self.launch_specification = None
        self.instance_id = None

    def __repr__(self):
        return 'SpotInstanceRequest:%s' % self.id

    def startElement(self, name, attrs, connection):
        retval = TaggedEC2Object.startElement(self, name, attrs, connection)
        if retval is not None:
            return retval
        if name == 'launchSpecification':
            self.launch_specification = LaunchSpecification(connection)
            return self.launch_specification
        elif name == 'fault':
            self.fault = SpotInstanceStateFault()
            return self.fault
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'spotInstanceRequestId':
            self.id = value
        elif name == 'spotPrice':
            self.price = float(value)
        elif name == 'type':
            self.type = value
        elif name == 'state':
            self.state = value
        elif name == 'validFrom':
            self.valid_from = value
        elif name == 'validUntil':
            self.valid_until = value
        elif name == 'launchGroup':
            self.launch_group = value
        elif name == 'availabilityZoneGroup':
            self.availability_zone_group = value
        elif name == 'launchedAvailabilityZone':
            self.launched_availability_zone = value
        elif name == 'instanceId':
            self.instance_id = value
        elif name == 'createTime':
            self.create_time = value
        elif name == 'productDescription':
            self.product_description = value
        else:
            setattr(self, name, value)

    def cancel(self):
        self.connection.cancel_spot_instance_requests([self.id])
