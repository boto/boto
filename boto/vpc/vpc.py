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
Represents a Virtual Private Cloud.
"""

from boto.ec2.ec2object import TaggedEC2Object

class VPC(TaggedEC2Object):

    def __init__(self, connection=None):
        TaggedEC2Object.__init__(self, connection)
        self.id = None
        self.dhcp_options_id = None
        self.state = None
        self.cidr_block = None

    def __repr__(self):
        return 'VPC:%s' % self.id
    
    def endElement(self, name, value, connection):
        if name == 'vpcId':
            self.id = value
        elif name == 'dhcpOptionsId':
            self.dhcp_options_id = value
        elif name == 'state':
            self.state = value
        elif name == 'cidrBlock':
            self.cidr_block = value
        else:
            setattr(self, name, value)

    def delete(self):
        return self.connection.delete_vpc(self.id)

    def _update(self, updated):
        self.__dict__.update(updated.__dict__)

    def update(self, validate=False):
        vpc_list = self.connection.get_all_vpcs([self.id])
        if len(vpc_list):
            updated_vpc = vpc_list[0]
            self._update(updated_vpc)
        elif validate:
            raise ValueError('%s is not a valid VPC ID' % (self.id,))
        return self.state
