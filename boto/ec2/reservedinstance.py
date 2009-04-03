# Copyright (c) 2006-2009 Mitch Garnaat http://garnaat.org/
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

from boto.ec2.ec2object import EC2Object

class ReservedInstancesOffering(EC2Object):
    
    def __init__(self, connection=None, id=None, instance_type=None,
                 availability_zone=None, duration=None, fixed_price=None,
                 usage_price=None, description=None):
        EC2Object.__init__(self, connection)
        self.id = id
        self.instance_type = instance_type
        self.availability_zone = availability_zone
        self.duration = duration
        self.fixed_price = fixed_price
        self.usage_price = usage_price
        self.description = description

    def __repr__(self):
        return 'ReservedInstanceOffering:%s' % self.id

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'reservedInstancesOfferingId':
            self.id = value
        elif name == 'instanceType':
            self.instance_type = value
        elif name == 'availabilityZone':
            self.availability_zone = value
        elif name == 'duration':
            self.duration = value
        elif name == 'fixedPrice':
            self.fixed_price = value
        elif name == 'usagePrice':
            self.usage_price = value
        elif name == 'productDescription':
            self.description = value
        else:
            setattr(self, name, value)

    def describe(self):
        print 'ID=%s' % self.id
        print '\tInstance Type=%s' % self.instance_type
        print '\tZone=%s' % self.availability_zone
        print '\tDuration=%s' % self.duration
        print '\tFixed Price=%s' % self.fixed_price
        print '\tUsage Price=%s' % self.usage_price
        print '\tDescription=%s' % self.description

    def purchase(self, instance_count=1):
        return self.connection.purchase_reserved_instance_offering(self.id, instance_count)

class ReservedInstance(ReservedInstancesOffering):

    def __init__(self, connection=None, id=None, instance_type=None,
                 availability_zone=None, duration=None, fixed_price=None,
                 usage_price=None, description=None,
                 instance_count=None, state=None):
        ReservedInstancesOffering.__init__(self, connection, id, instance_type,
                                           availability_zone, duration, fixed_price,
                                           usage_price, description)
        self.instance_count = instance_count
        self.state = state

    def __repr__(self):
        return 'ReservedInstance:%s' % self.id

    def endElement(self, name, value, connection):
        if name == 'reservedInstancesId':
            self.id = value
        if name == 'instanceCount':
            self.instance_count = int(value)
        elif name == 'state':
            self.state = value
        else:
            ReservedInstancesOffering.endElement(self, name, value, connection)
