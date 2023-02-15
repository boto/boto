# Copyright (c) 2009-2010 Mitch Garnaat http://garnaat.org/
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
Represents a NAT Gateway
"""

from boto.ec2.ec2object import TaggedEC2Object
from boto.resultset import ResultSet


class NatGateway(TaggedEC2Object):
    def __init__(self, connection=None):
        super(NatGateway, self).__init__(connection)
        self.id = None
        self.vpc_id = None
        self.subnet_id = None
        self.state = None
        self.addresses = []

    def __repr__(self):
        return 'NatGateway:%s' % self.id

    def startElement(self, name, attrs, connection):
        result = super(NatGateway, self).startElement(name, attrs, connection)

        if result is not None:
            # Parent found an interested element, just return it
            return result

        if name == 'natGatewayAddressSet':
            self.addresses = ResultSet([('item', NatGatewayAddress)])
            return self.addresses
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'natGatewayId':
            self.id = value
        elif name == 'vpcId':
            self.vpc_id = value
        elif name == 'subnetId':
            self.subnet_id = value
        elif name == 'state':
            self.state = value
        else:
            setattr(self, name, value)


class NatGatewayAddress(object):
    def __init__(self, connection=None):
        self.interface_id = None
        self.allocation_id = None
        self.ip_public = None
        self.ip_private = None

    def __repr__(self):
        return 'NatGatewayAddress:%s' % self.interface_id

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'networkInterfaceId':
            self.interface_id = value
        elif name == 'publicIp':
            self.ip_public = value
        elif name == 'allocationId':
            self.allocation_id = value
        elif name == 'privateIp':
            self.ip_private = value