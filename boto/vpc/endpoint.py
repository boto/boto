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
class Endpoint(object):
    """
    Represents a VPC Endpoint
    """
    def __init__(self, id=None, service_name=None, policy_document=None):
        self.id = id
        self.service_name = service_name
        self.policy_document = policy_document

    def __repr__(self):
        return 'VpcEndpoint'

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'vpcEndpointId':
            self.id = str(value)
        elif name == 'policyDocument':
            self.policy_document = value

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

