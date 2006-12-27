# Copyright (c) 2006 Mitch Garnaat http://garnaat.org/
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
Represents an EC2 Security Group
"""

class SecurityGroup:
    
    def __init__(self, connection=None, owner_id=None,
                 name=None, description=None):
        self.connection = connection
        self.owner_id = owner_id
        self.name = name
        self.description = description
        self.ip_permissions = []

    def startElement(self, name, attrs, connection):
        if name == 'item':
            self.ip_permissions.append(IPPermissions(self))
            return self.ip_permissions[-1]
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'ownerId':
            self.owner_id = value
        elif name == 'groupName':
            self.name = value
        elif name == 'groupDescription':
            self.description = value
        elif name == 'ipRanges':
            pass
        elif name == 'return':
            self.status = bool(value)
        else:
            setattr(self, name, value)

class IPPermissions:

    def __init__(self, parent=None):
        self.parent = parent
        self.ip_protocol = None
        self.from_port = None
        self.to_port = None
        self.ip_ranges = []

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'ipProtocol':
            self.ip_protocol = value
        elif name == 'fromPort':
            self.from_port = value
        elif name == 'toPort':
            self.to_port = value
        elif name == 'cidrIp':
            self.ip_ranges.append(value)
        else:
            setattr(self, name, value)

        
