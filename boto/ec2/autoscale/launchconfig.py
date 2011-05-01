# Copyright (c) 2009 Reza Lotun http://reza.lotun.name/
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


from datetime import datetime
import base64
from boto.resultset import ResultSet
from boto.ec2.elb.listelement import ListElement

# this should use the corresponding object from boto.ec2
class Ebs(object):
    def __init__(self, connection=None, snapshot_id=None, volume_size=None):
        self.connection = connection
        self.snapshot_id = snapshot_id
        self.volume_size = volume_size

    def __repr__(self):
        return 'Ebs(%s, %s)' % (self.snapshot_id, self.volume_size)

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'SnapshotId':
            self.snapshot_id = value
        elif name == 'VolumeSize':
            self.volume_size = value


class InstanceMonitoring(object):
    def __init__(self, connection=None, enabled='false'):
        self.connection = connection
        self.enabled = enabled

    def __repr__(self):
        return 'InstanceMonitoring(%s)' % self.enabled

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'Enabled':
            self.enabled = value


# this should use the BlockDeviceMapping from boto.ec2.blockdevicemapping
class BlockDeviceMapping(object):
    def __init__(self, connection=None, device_name=None, virtual_name=None):
        self.connection = connection
        self.device_name = None
        self.virtual_name = None
        self.ebs = None

    def __repr__(self):
        return 'BlockDeviceMapping(%s, %s)' % (self.device_name, self.virtual_name)

    def startElement(self, name, attrs, connection):
        if name == 'Ebs':
            self.ebs = Ebs(self)
            return self.ebs

    def endElement(self, name, value, connection):
        if name == 'DeviceName':
            self.device_name = value
        elif name == 'VirtualName':
            self.virtual_name = value


class LaunchConfiguration(object):
    def __init__(self, connection=None, name=None, image_id=None,
                 key_name=None, security_groups=None, user_data=None,
                 instance_type='m1.small', kernel_id=None,
                 ramdisk_id=None, block_device_mappings=None,
                 instance_monitoring=False):
        """
        A launch configuration.

        :type name: str
        :param name: Name of the launch configuration to create.

        :type image_id: str
        :param image_id: Unique ID of the Amazon Machine Image (AMI) which was
                         assigned during registration.

        :type key_name: str
        :param key_name: The name of the EC2 key pair.

        :type security_groups: list
        :param security_groups: Names of the security groups with which to
                                associate the EC2 instances.

        :type user_data: str
        :param user_data: The user data available to launched EC2 instances.

        :type instance_type: str
        :param instance_type: The instance type

        :type kern_id: str
        :param kern_id: Kernel id for instance

        :type ramdisk_id: str
        :param ramdisk_id: RAM disk id for instance

        :type block_device_mappings: list
        :param block_device_mappings: Specifies how block devices are exposed for instances

        :type instance_monitoring: bool
        :param instance_monitoring: Whether instances in group are launched with detailed monitoring.
        """
        self.connection = connection
        self.name = name
        self.instance_type = instance_type
        self.block_device_mappings = block_device_mappings
        self.key_name = key_name
        sec_groups = security_groups or []
        self.security_groups = ListElement(sec_groups)
        self.image_id = image_id
        self.ramdisk_id = ramdisk_id
        self.created_time = None
        self.kernel_id = kernel_id
        self.user_data = user_data
        self.created_time = None
        self.instance_monitoring = instance_monitoring
        self.launch_configuration_arn = None

    def __repr__(self):
        return 'LaunchConfiguration:%s' % self.name

    def startElement(self, name, attrs, connection):
        if name == 'SecurityGroups':
            return self.security_groups
        elif name == 'BlockDeviceMappings':
            self.block_device_mappings = ResultSet([('member', BlockDeviceMapping)])
            return self.block_device_mappings
        elif name == 'InstanceMonitoring':
            self.instance_monitoring = InstanceMonitoring(self)
            return self.instance_monitoring

    def endElement(self, name, value, connection):
        if name == 'InstanceType':
            self.instance_type = value
        elif name == 'LaunchConfigurationName':
            self.name = value
        elif name == 'KeyName':
            self.key_name = value
        elif name == 'ImageId':
            self.image_id = value
        elif name == 'CreatedTime':
            self.created_time = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
        elif name == 'KernelId':
            self.kernel_id = value
        elif name == 'RamdiskId':
            self.ramdisk_id = value
        elif name == 'UserData':
            self.user_data = base64.b64decode(value)
        elif name == 'LaunchConfigurationARN':
            self.launch_configuration_arn = value
        elif name == 'InstanceMonitoring':
            self.instance_monitoring = value
        else:
            setattr(self, name, value)

    def delete(self):
        """ Delete this launch configuration. """
        return self.connection.delete_launch_configuration(self.name)

