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
Represents a VPC endpoint
"""
from boto.ec2.ec2object import TaggedEC2Object
from boto.vpc.routetable import RouteTable, RouteTableListElement
from boto.resultset import ResultSet

class Endpoint(TaggedEC2Object):
    """
    Represents a VPC Endpoint
    """
    def __init__(self, connection=None): 
        super(Endpoint, self).__init__(connection)
        self.id = None
        self.state = None
        self.service_name = None 
        self.policy_document = None 
        self.routetables = RouteTableListElement()

    def __repr__(self):
        return 'VpcEndpoint:%s' % self.id

    def startElement(self, name, attrs, connection):
        result = super(Endpoint, self).startElement(name, attrs, connection)

        if result is not None:
          return result
        if name == 'routeTableIdSet':
            return self.routetables
        else:
          return None

    def endElement(self, name, value, connection):
        if name == 'vpcEndpointId':
            self.id = value
        if name == 'policyDocument':
            self.policy_document = value
        if name == 'state':
            self.state = str(value)
        else:
            setattr(self, name, value)

class EndpointService(object):
    """
    Respresents a VPC Endpoint Service
    """

    def __init__(self, id=None, service_name=None):
        self.id = id

    def __repr__(self):
      return 'EndpointService'

    def startElement(self, name, value, connection):
        pass

    def endElement(self, name, value, connection):
        pass
        if name == 'item':
            self.service_name = str(value)

