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


from boto.ec2.autoscale.request import Request
from boto.ec2.elb.listelement import ListElement


class LaunchConfiguration(object):
    def __init__(self, connection=None, name=None, image_id=None,
                 key_name=None, security_groups=None, user_data=None,
                 instance_type='m1.small', kernel_id=None,
                 ramdisk_id=None, block_device_mappings=None):
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

    def __repr__(self):
        return 'LaunchConfiguration:%s' % self.name

    def startElement(self, name, attrs, connection):
        if name == 'SecurityGroups':
            return self.security_groups
        else:
            return

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
            self.created_time = value
        elif name == 'KernelId':
            self.kernel_id = value
        elif name == 'RamdiskId':
            self.ramdisk_id = value
        elif name == 'UserData':
            self.user_data = value
        else:
            setattr(self, name, value)

    def delete(self):
        """ Delete this launch configuration. """
        params = {'LaunchConfigurationName' : self.name}
        return self.connection.get_object('DeleteLaunchConfiguration', params,
                                          Request)

