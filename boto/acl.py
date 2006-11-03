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

CannedACLStrings = ['private', 'public-read',
                    'public-read-write', 'authenticated-read']

class Policy:

    def __init__(self, parent=None, xml_attrs=None):
        self.parent = parent
        self.acl = None

    def add_acl(self, acl):
        self.acl = acl
        
    # This allows the XMLHandler to set the attributes as they are named
    # in the XML response but have the capitalized names converted to
    # more conventional looking python variables names automatically
    def __setattr__(self, key, value):
        if key == 'AccessControlPolicy':
            pass
        else:
            self.__dict__[key] = value

class ACL:

    def __init__(self, policy=None, xml_attrs=None):
        if policy:
            policy.add_acl(self)
        self.grants = []

    def add_grant(self, grant):
        self.grants.append(grant)

    # This allows the XMLHandler to set the attributes as they are named
    # in the XML response but have the capitalized names converted to
    # more conventional looking python variables names automatically
    def __setattr__(self, key, value):
        if key == 'AccessControlList':
            pass
        else:
            self.__dict__[key] = value

class Grant:

    def __init__(self, acl=None, xml_attrs=None):
        if acl:
            acl.add_grant(self)

    # This allows the XMLHandler to set the attributes as they are named
    # in the XML response but have the capitalized names converted to
    # more conventional looking python variables names automatically
    def __setattr__(self, key, value):
        if key == 'Permission':
            self.__dict__['permission'] = value
        elif key == 'owner':
            self.__dict__['grantee'] = value
        elif key == 'Grant':
            pass
        else:
            self.__dict__[key] = value

            
