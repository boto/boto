# Copyright (c) 2006-2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010, Eucalyptus Systems, Inc.
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
Represents an EC2 Instance
"""
import boto
from boto.ec2.ec2object import EC2Object, TaggedEC2Object
from boto.resultset import ResultSet
from boto.ec2.address import Address
from boto.ec2.blockdevicemapping import BlockDeviceMapping
from boto.ec2.image import ProductCodes
import base64

class Reservation(EC2Object):
    """
    Represents a Reservation response object.

    :ivar id: The unique ID of the Reservation.
    :ivar owner_id: The unique ID of the owner of the Reservation.
    :ivar groups: A list of Group objects representing the security
                  groups associated with launched instances.
    :ivar instances: A list of Instance objects launched in this
                     Reservation.
    """
    
    def __init__(self, connection=None):
        EC2Object.__init__(self, connection)
        self.id = None
        self.owner_id = None
        self.groups = []
        self.instances = []

    def __repr__(self):
        return 'Reservation:%s' % self.id

    def startElement(self, name, attrs, connection):
        if name == 'instancesSet':
            self.instances = ResultSet([('item', Instance)])
            return self.instances
        elif name == 'groupSet':
            self.groups = ResultSet([('item', Group)])
            return self.groups
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'reservationId':
            self.id = value
        elif name == 'ownerId':
            self.owner_id = value
        else:
            setattr(self, name, value)

    def stop_all(self):
        for instance in self.instances:
            instance.stop()
            
class Instance(TaggedEC2Object):
    
    def __init__(self, connection=None):
        TaggedEC2Object.__init__(self, connection)
        self.id = None
        self.dns_name = None
        self.public_dns_name = None
        self.private_dns_name = None
        self.state = None
        self.state_code = None
        self.key_name = None
        self.shutdown_state = None
        self.previous_state = None
        self.instance_type = None
        self.instance_class = None
        self.launch_time = None
        self.image_id = None
        self.placement = None
        self.kernel = None
        self.ramdisk = None
        self.product_codes = ProductCodes()
        self.ami_launch_index = None
        self.monitored = False
        self.instance_class = None
        self.spot_instance_request_id = None
        self.subnet_id = None
        self.vpc_id = None
        self.private_ip_address = None
        self.ip_address = None
        self.requester_id = None
        self._in_monitoring_element = False
        self.persistent = False
        self.root_device_name = None
        self.root_device_type = None
        self.block_device_mapping = None
        self.state_reason = None
        self.group_name = None
        self.client_token = None
        self.groups = []

    def __repr__(self):
        return 'Instance:%s' % self.id

    def startElement(self, name, attrs, connection):
        retval = TaggedEC2Object.startElement(self, name, attrs, connection)
        if retval is not None:
            return retval
        if name == 'monitoring':
            self._in_monitoring_element = True
        elif name == 'blockDeviceMapping':
            self.block_device_mapping = BlockDeviceMapping()
            return self.block_device_mapping
        elif name == 'productCodes':
            return self.product_codes
        elif name == 'stateReason':
            self.state_reason = StateReason()
            return self.state_reason
        elif name == 'groupSet':
            self.groups = ResultSet([('item', Group)])
            return self.groups
        return None

    def endElement(self, name, value, connection):
        if name == 'instanceId':
            self.id = value
        elif name == 'imageId':
            self.image_id = value
        elif name == 'dnsName' or name == 'publicDnsName':
            self.dns_name = value           # backwards compatibility
            self.public_dns_name = value
        elif name == 'privateDnsName':
            self.private_dns_name = value
        elif name == 'keyName':
            self.key_name = value
        elif name == 'amiLaunchIndex':
            self.ami_launch_index = value
        elif name == 'shutdownState':
            self.shutdown_state = value
        elif name == 'previousState':
            self.previous_state = value
        elif name == 'name':
            self.state = value
        elif name == 'code':
            try:
                self.state_code = int(value)
            except ValueError:
                boto.log.warning('Error converting code (%s) to int' % value)
                self.state_code = value
        elif name == 'instanceType':
            self.instance_type = value
        elif name == 'instanceClass':
            self.instance_class = value
        elif name == 'rootDeviceName':
            self.root_device_name = value
        elif name == 'rootDeviceType':
            self.root_device_type = value
        elif name == 'launchTime':
            self.launch_time = value
        elif name == 'availabilityZone':
            self.placement = value
        elif name == 'placement':
            pass
        elif name == 'kernelId':
            self.kernel = value
        elif name == 'ramdiskId':
            self.ramdisk = value
        elif name == 'state':
            if self._in_monitoring_element:
                if value == 'enabled':
                    self.monitored = True
                self._in_monitoring_element = False
        elif name == 'instanceClass':
            self.instance_class = value
        elif name == 'spotInstanceRequestId':
            self.spot_instance_request_id = value
        elif name == 'subnetId':
            self.subnet_id = value
        elif name == 'vpcId':
            self.vpc_id = value
        elif name == 'privateIpAddress':
            self.private_ip_address = value
        elif name == 'ipAddress':
            self.ip_address = value
        elif name == 'requesterId':
            self.requester_id = value
        elif name == 'persistent':
            if value == 'true':
                self.persistent = True
            else:
                self.persistent = False
        elif name == 'groupName':
            if self._in_monitoring_element:
                self.group_name = value
        elif name == 'clientToken':
            self.client_token = value
        else:
            setattr(self, name, value)

    def _update(self, updated):
        self.__dict__.update(updated.__dict__)

    def update(self, validate=False):
        """
        Update the instance's state information by making a call to fetch
        the current instance attributes from the service.

        :type validate: bool
        :param validate: By default, if EC2 returns no data about the
                         instance the update method returns quietly.  If
                         the validate param is True, however, it will
                         raise a ValueError exception if no data is
                         returned from EC2.
        """
        rs = self.connection.get_all_instances([self.id])
        if len(rs) > 0:
            r = rs[0]
            for i in r.instances:
                if i.id == self.id:
                    self._update(i)
        elif validate:
            raise ValueError('%s is not a valid Instance ID' % self.id)
        return self.state

    def terminate(self):
        """
        Terminate the instance
        """
        rs = self.connection.terminate_instances([self.id])
        if len(rs) > 0:
            self._update(rs[0])

    def stop(self, force=False):
        """
        Stop the instance

        :type force: bool
        :param force: Forces the instance to stop
        
        :rtype: list
        :return: A list of the instances stopped
        """
        rs = self.connection.stop_instances([self.id])
        if len(rs) > 0:
            self._update(rs[0])

    def start(self):
        """
        Start the instance.
        """
        rs = self.connection.start_instances([self.id])
        if len(rs) > 0:
            self._update(rs[0])

    def reboot(self):
        return self.connection.reboot_instances([self.id])

    def get_console_output(self):
        """
        Retrieves the console output for the instance.

        :rtype: :class:`boto.ec2.instance.ConsoleOutput`
        :return: The console output as a ConsoleOutput object
        """
        return self.connection.get_console_output(self.id)

    def confirm_product(self, product_code):
        return self.connection.confirm_product_instance(self.id, product_code)

    def use_ip(self, ip_address):
        if isinstance(ip_address, Address):
            ip_address = ip_address.public_ip
        return self.connection.associate_address(self.id, ip_address)

    def monitor(self):
        return self.connection.monitor_instance(self.id)

    def unmonitor(self):
        return self.connection.unmonitor_instance(self.id)

    def get_attribute(self, attribute):
        """
        Gets an attribute from this instance.

        :type attribute: string
        :param attribute: The attribute you need information about
                          Valid choices are:
                          instanceType|kernel|ramdisk|userData|
                          disableApiTermination|
                          instanceInitiatedShutdownBehavior|
                          rootDeviceName|blockDeviceMapping

        :rtype: :class:`boto.ec2.image.InstanceAttribute`
        :return: An InstanceAttribute object representing the value of the
                 attribute requested
        """
        return self.connection.get_instance_attribute(self.id, attribute)

    def modify_attribute(self, attribute, value):
        """
        Changes an attribute of this instance

        :type attribute: string
        :param attribute: The attribute you wish to change.
                          AttributeName - Expected value (default)
                          instanceType - A valid instance type (m1.small)
                          kernel - Kernel ID (None)
                          ramdisk - Ramdisk ID (None)
                          userData - Base64 encoded String (None)
                          disableApiTermination - Boolean (true)
                          instanceInitiatedShutdownBehavior - stop|terminate
                          rootDeviceName - device name (None)

        :type value: string
        :param value: The new value for the attribute

        :rtype: bool
        :return: Whether the operation succeeded or not
        """
        return self.connection.modify_instance_attribute(self.id, attribute,
                                                         value)

    def reset_attribute(self, attribute):
        """
        Resets an attribute of this instance to its default value.

        :type attribute: string
        :param attribute: The attribute to reset. Valid values are:
                          kernel|ramdisk

        :rtype: bool
        :return: Whether the operation succeeded or not
        """
        return self.connection.reset_instance_attribute(self.id, attribute)

class Group:

    def __init__(self, parent=None):
        self.id = None
        self.name = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'groupId':
            self.id = value
        elif name == 'groupName':
            self.name = value
        else:
            setattr(self, name, value)
    
class ConsoleOutput:

    def __init__(self, parent=None):
        self.parent = parent
        self.instance_id = None
        self.timestamp = None
        self.output = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'instanceId':
            self.instance_id = value
        elif name == 'timestamp':
            self.timestamp = value
        elif name == 'output':
            self.output = base64.b64decode(value)
        else:
            setattr(self, name, value)

class InstanceAttribute(dict):

    ValidValues = ['instanceType', 'kernel', 'ramdisk', 'userData',
                   'disableApiTermination', 'instanceInitiatedShutdownBehavior',
                   'rootDeviceName', 'blockDeviceMapping', 'sourceDestCheck',
                   'groupSet']

    def __init__(self, parent=None):
        dict.__init__(self)
        self.instance_id = None
        self.request_id = None
        self._current_value = None

    def startElement(self, name, attrs, connection):
        if name == 'blockDeviceMapping':
            self[name] = BlockDeviceMapping()
            return self[name]
        elif name == 'groupSet':
            self[name] = ResultSet([('item', Group)])
            return self[name]
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'instanceId':
            self.instance_id = value
        elif name == 'requestId':
            self.request_id = value
        elif name == 'value':
            self._current_value = value
        elif name in self.ValidValues:
            self[name] = self._current_value

class StateReason(dict):

    def __init__(self, parent=None):
        dict.__init__(self)

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name != 'stateReason':
            self[name] = value
            
