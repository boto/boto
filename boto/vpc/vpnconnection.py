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
Represents a VPN Connectionn
"""

from boto.ec2.ec2object import EC2Object

class VpnConnection(EC2Object):

    def __init__(self, connection=None):
        EC2Object.__init__(self, connection)
        self.id = None
        self.state = None
        self.customer_gateway_configuration = None
        self.type = None
        self.customer_gateway_id = None
        self.vpn_gateway_id = None

    def __repr__(self):
        return 'VpnConnection:%s' % self.id
    
    def endElement(self, name, value, connection):
        if name == 'vpnConnectionId':
            self.id = value
        elif name == 'state':
            self.state = value
        elif name == 'customerGatewayConfiguration':
            self.customer_gateway_configuration = value
        elif name == 'type':
            self.type = value
        elif name == 'customerGatewayId':
            self.customer_gateway_id = value
        elif name == 'vpnGatewayId':
            self.vpn_gateway_id = value
        else:
            setattr(self, name, value)

    def delete(self):
        return self.connection.delete_vpn_connection(self.id)

