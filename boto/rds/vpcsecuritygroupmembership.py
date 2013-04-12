# Copyright (c) 2009 Mitch Garnaat http://garnaat.org/
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
Represents a VPCSecurityGroupMembership
"""

class VPCSecurityGroupMembership(object):
    """
    Represents VPC Security Group and RDS database is a member of

    Properties reference available from the AWS documentation at
    http://docs.aws.amazon.com/AmazonRDS/latest/APIReference/API_VpcSecurityGroupMembership.html

    :ivar connection: :py:class:`boto.rds.RDSConnection` associated with the current object
    :ivar name: Name of the VPC security group membership
    :ivar status: Status of the VPC security group membership
    :ivar vpc_groups: List of :py:class:`VPC Security Group
        <boto.ec2.securitygroup.SecurityGroup>` objects that this RDS Instance is a member of
    """
    def __init__(self, connection=None, name=None, status=None):
        self.connection = connection
        self.name = name
        self.status = status
        self.vpc_groups = []

    def __repr__(self):
        return 'VPCSecurityGroupMembership:%s' % self.name

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'VpcSecurityGroupId':
            vpc_grp = value
            self.vpc_groups.append(vpc_grp)
        elif name == 'Status':
            self.status = value
        else:
            setattr(self, name, value)
