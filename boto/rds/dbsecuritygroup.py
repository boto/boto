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
Represents an DBSecurityGroup
"""
from boto.ec2.securitygroup import SecurityGroup

class DBSecurityGroup(object):
    
    def __init__(self, connection=None, owner_id=None,
                 name=None, description=None):
        self.connection = connection
        self.owner_id = owner_id
        self.name = name
        self.description = description
        self.ec2_groups = []
        self.ip_ranges = []

    def __repr__(self):
        return 'DBSecurityGroup:%s' % self.name

    def startElement(self, name, attrs, connection):
        if name == 'IPRange':
            cidr = IPRange(self)
            self.ip_ranges.append(cidr)
            return cidr
        elif name == 'EC2SecurityGroup':
            ec2_grp = EC2SecurityGroup(self)
            self.ec2_groups.append(ec2_grp)
            return ec2_grp
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'OwnerId':
            self.owner_id = value
        elif name == 'DBSecurityGroupName':
            self.name = value
        elif name == 'DBSecurityGroupDescription':
            self.description = value
        elif name == 'IPRanges':
            pass
        else:
            setattr(self, name, value)

    def delete(self):
        return self.connection.delete_dbsecurity_group(self.name)

    def authorize(self, cidr_ip=None, ec2_group=None):
        """
        Add a new rule to this DBSecurity group.
        You need to pass in either a CIDR block to authorize or
        and EC2 SecurityGroup.
        
        @type cidr_ip: string
        @param cidr_ip: A valid CIDR IP range to authorize

        @type ec2_group: :class:`boto.ec2.securitygroup.SecurityGroup>`
                         
        @rtype: bool
        @return: True if successful.
        """
        if isinstance(ec2_group, SecurityGroup):
            group_name = ec2_group.name
            group_owner_id = ec2_group.owner_id
        else:
            group_name = None
            group_owner_id = None
        return self.connection.authorize_dbsecurity_group(self.name,
                                                          cidr_ip,
                                                          group_name,
                                                          group_owner_id)

    def revoke(self, cidr_ip=None, ec2_group=None):
        """
        Revoke access to a CIDR range or EC2 SecurityGroup
        You need to pass in either a CIDR block to authorize or
        and EC2 SecurityGroup.
        
        @type cidr_ip: string
        @param cidr_ip: A valid CIDR IP range to authorize

        @type ec2_group: :class:`boto.ec2.securitygroup.SecurityGroup>`
                         
        @rtype: bool
        @return: True if successful.
        """
        if isinstance(ec2_group, SecurityGroup):
            group_name = ec2_group.name
            group_owner_id = ec2_group.owner_id
        else:
            group_name = None
            group_owner_id = None
        return self.connection.revoke_dbsecurity_group(self.name,
                                                       cidr_ip,
                                                       group_name,
                                                       group_owner_id)

class IPRange(object):

    def __init__(self, parent=None):
        self.parent = parent
        self.cidr_ip = None
        self.status = None

    def __repr__(self):
        return 'IPRange:%s' % self.cidr_ip

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'CIDRIP':
            self.cidr_ip = value
        elif name == 'Status':
            self.status = value
        else:
            setattr(self, name, value)

class EC2SecurityGroup(object):

    def __init__(self, parent=None):
        self.parent = parent
        self.name = None
        self.owner_id = None

    def __repr__(self):
        return 'EC2SecurityGroup:%s' % self.name

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'EC2SecurityGroupName':
            self.name = value
        elif name == 'EC2SecurityGroupOwnerId':
            self.owner_id = value
        else:
            setattr(self, name, value)

