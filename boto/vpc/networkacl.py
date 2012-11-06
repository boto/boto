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
Represents a Route Table
"""

from boto.ec2.ec2object import TaggedEC2Object
from boto.resultset import ResultSet

class NetworkAcl(TaggedEC2Object):

    def __init__(self, connection=None):
        TaggedEC2Object.__init__(self, connection)
        self.id = None
        self.vpc_id = None
        self.network_acl_entries = []
        self.associations = []

    def __repr__(self):
        return 'NetworkAcl:%s' % self.id

    def startElement(self, name, attrs, connection):
        result = super(NetworkAcl, self).startElement(name, attrs, connection)

        if result is not None:
            # Parent found an interested element, just return it
            return result

        if name == 'entrySet':
            self.network_acl_entries = ResultSet([('item', NetworkAcl)])
            return self.network_acl_entries
        elif name == 'associationSet':
            self.associations = ResultSet([('item', NetworkAclAssociation)])
            return self.associations
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'networkAclId':
            self.id = value
        elif name == 'vpcId':
            self.vpc_id = value
        else:
            setattr(self, name, value)

class NetworkAclEntry(object):
    def __init__(self, connection=None):
        self.rule_number = None
        self.protocol = None
        self.rule_action = None
        self.egress = None
        self.cidr_block = None


    def __repr__(self):
        return 'Acl:%s' % self.ruleNumber

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'CidrBlock':
            self.cidr_block = value
        elif name == 'egress':
            self.egress = value
        elif name == 'protocol':
            self.protocol = value
        elif name == 'ruleAction':
            self.rule_action = value
        elif name == 'ruleNumber':
            self.rule_number = value



class NetworkAclAssociation(object):
    def __init__(self, connection=None):
        self.id = None
        self.subnet_id = None
        self.network_acl_id = None
        self.main = False

    def __repr__(self):
        return 'NetworkAclAssociation:%s' % self.id

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'NetworkAclAssociationId':
            self.id = value
        elif name == 'NetworkAclId':
            self.route_table_id = value
        elif name == 'subnetId':
            self.subnet_id = value
        elif name == 'main':
            self.main = value == 'true'
