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

from boto.ec2.ec2object import EC2Object, TaggedEC2Object
from boto.ec2.blockdevicemapping import BlockDeviceMapping

class ProductCodes(list):

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'productCode':
            self.append(value)
    
class Image(TaggedEC2Object):
    """
    Represents an EC2 Image
    """
    
    def __init__(self, connection=None):
        TaggedEC2Object.__init__(self, connection)
        self.id = None
        self.location = None
        self.state = None
        self.ownerId = None  # for backwards compatibility
        self.owner_id = None
        self.owner_alias = None
        self.is_public = False
        self.architecture = None
        self.platform = None
        self.type = None
        self.kernel_id = None
        self.ramdisk_id = None
        self.name = None
        self.description = None
        self.product_codes = ProductCodes()
        self.block_device_mapping = None
        self.root_device_type = None
        self.root_device_name = None
        self.virtualization_type = None
        self.hypervisor = None
        self.instance_lifecycle = None

    def __repr__(self):
        return 'Image:%s' % self.id

    def startElement(self, name, attrs, connection):
        retval = TaggedEC2Object.startElement(self, name, attrs, connection)
        if retval is not None:
            return retval
        if name == 'blockDeviceMapping':
            self.block_device_mapping = BlockDeviceMapping()
            return self.block_device_mapping
        elif name == 'productCodes':
            return self.product_codes
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'imageId':
            self.id = value
        elif name == 'imageLocation':
            self.location = value
        elif name == 'imageState':
            self.state = value
        elif name == 'imageOwnerId':
            self.ownerId = value # for backwards compatibility
            self.owner_id = value
        elif name == 'isPublic':
            if value == 'false':
                self.is_public = False
            elif value == 'true':
                self.is_public = True
            else:
                raise Exception(
                    'Unexpected value of isPublic %s for image %s'%(
                        value, 
                        self.id
                    )
                )
        elif name == 'architecture':
            self.architecture = value
        elif name == 'imageType':
            self.type = value
        elif name == 'kernelId':
            self.kernel_id = value
        elif name == 'ramdiskId':
            self.ramdisk_id = value
        elif name == 'imageOwnerAlias':
            self.owner_alias = value
        elif name == 'platform':
            self.platform = value
        elif name == 'name':
            self.name = value
        elif name == 'description':
            self.description = value
        elif name == 'rootDeviceType':
            self.root_device_type = value
        elif name == 'rootDeviceName':
            self.root_device_name = value
        elif name == 'virtualizationType':
            self.virtualization_type = value
        elif name == 'hypervisor':
            self.hypervisor = value
        elif name == 'instanceLifecycle':
            self.instance_lifecycle = value
        else:
            setattr(self, name, value)

    def _update(self, updated):
        self.__dict__.update(updated.__dict__)

    def update(self, validate=False):
        """
        Update the image's state information by making a call to fetch
        the current image attributes from the service.

        :type validate: bool
        :param validate: By default, if EC2 returns no data about the
                         image the update method returns quietly.  If
                         the validate param is True, however, it will
                         raise a ValueError exception if no data is
                         returned from EC2.
        """
        rs = self.connection.get_all_images([self.id])
        if len(rs) > 0:
            img = rs[0]
            if img.id == self.id:
                self._update(img)
        elif validate:
            raise ValueError('%s is not a valid Image ID' % self.id)
        return self.state

    def run(self, min_count=1, max_count=1, key_name=None,
            security_groups=None, user_data=None,
            addressing_type=None, instance_type='m1.small', placement=None,
            kernel_id=None, ramdisk_id=None,
            monitoring_enabled=False, subnet_id=None,
            block_device_map=None,
            disable_api_termination=False,
            instance_initiated_shutdown_behavior=None,
            private_ip_address=None,
            placement_group=None):
        """
        Runs this instance.
        
        :type min_count: int
        :param min_count: The minimum number of instances to start
        
        :type max_count: int
        :param max_count: The maximum number of instances to start
        
        :type key_name: string
        :param key_name: The name of the keypair to run this instance with.
        
        :type security_groups: 
        :param security_groups:
        
        :type user_data: 
        :param user_data:
        
        :type addressing_type: 
        :param daddressing_type:
        
        :type instance_type: string
        :param instance_type: The type of instance to run.  Current choices are:
                              m1.small | m1.large | m1.xlarge | c1.medium |
                              c1.xlarge | m2.xlarge | m2.2xlarge |
                              m2.4xlarge | cc1.4xlarge
        
        :type placement: string
        :param placement: The availability zone in which to launch the instances

        :type kernel_id: string
        :param kernel_id: The ID of the kernel with which to launch the instances
        
        :type ramdisk_id: string
        :param ramdisk_id: The ID of the RAM disk with which to launch the instances
        
        :type monitoring_enabled: bool
        :param monitoring_enabled: Enable CloudWatch monitoring on the instance.
        
        :type subnet_id: string
        :param subnet_id: The subnet ID within which to launch the instances for VPC.
        
        :type private_ip_address: string
        :param private_ip_address: If you're using VPC, you can optionally use
                                   this parameter to assign the instance a
                                   specific available IP address from the
                                   subnet (e.g., 10.0.0.25).

        :type block_device_map: :class:`boto.ec2.blockdevicemapping.BlockDeviceMapping`
        :param block_device_map: A BlockDeviceMapping data structure
                                 describing the EBS volumes associated
                                 with the Image.

        :type disable_api_termination: bool
        :param disable_api_termination: If True, the instances will be locked
                                        and will not be able to be terminated
                                        via the API.

        :type instance_initiated_shutdown_behavior: string
        :param instance_initiated_shutdown_behavior: Specifies whether the instance's
                                                     EBS volumes are stopped (i.e. detached)
                                                     or terminated (i.e. deleted) when
                                                     the instance is shutdown by the
                                                     owner.  Valid values are:
                                                     stop | terminate

        :type placement_group: string
        :param placement_group: If specified, this is the name of the placement
                                group in which the instance(s) will be launched.

        :rtype: Reservation
        :return: The :class:`boto.ec2.instance.Reservation` associated with the request for machines
        """
        return self.connection.run_instances(self.id, min_count, max_count,
                                             key_name, security_groups,
                                             user_data, addressing_type,
                                             instance_type, placement,
                                             kernel_id, ramdisk_id,
                                             monitoring_enabled, subnet_id,
                                             block_device_map, disable_api_termination,
                                             instance_initiated_shutdown_behavior,
                                             private_ip_address,
                                             placement_group)

    def deregister(self):
        return self.connection.deregister_image(self.id)

    def get_launch_permissions(self):
        img_attrs = self.connection.get_image_attribute(self.id,
                                                        'launchPermission')
        return img_attrs.attrs

    def set_launch_permissions(self, user_ids=None, group_names=None):
        return self.connection.modify_image_attribute(self.id,
                                                      'launchPermission',
                                                      'add',
                                                      user_ids,
                                                      group_names)

    def remove_launch_permissions(self, user_ids=None, group_names=None):
        return self.connection.modify_image_attribute(self.id,
                                                      'launchPermission',
                                                      'remove',
                                                      user_ids,
                                                      group_names)

    def reset_launch_attributes(self):
        return self.connection.reset_image_attribute(self.id,
                                                     'launchPermission')

    def get_kernel(self):
        img_attrs =self.connection.get_image_attribute(self.id, 'kernel')
        return img_attrs.kernel

    def get_ramdisk(self):
        img_attrs = self.connection.get_image_attribute(self.id, 'ramdisk')
        return img_attrs.ramdisk

class ImageAttribute:

    def __init__(self, parent=None):
        self.name = None
        self.kernel = None
        self.ramdisk = None
        self.attrs = {}

    def startElement(self, name, attrs, connection):
        if name == 'blockDeviceMapping':
            self.attrs['block_device_mapping'] = BlockDeviceMapping()
            return self.attrs['block_device_mapping']
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'launchPermission':
            self.name = 'launch_permission'
        elif name == 'group':
            if self.attrs.has_key('groups'):
                self.attrs['groups'].append(value)
            else:
                self.attrs['groups'] = [value]
        elif name == 'userId':
            if self.attrs.has_key('user_ids'):
                self.attrs['user_ids'].append(value)
            else:
                self.attrs['user_ids'] = [value]
        elif name == 'productCode':
            if self.attrs.has_key('product_codes'):
                self.attrs['product_codes'].append(value)
            else:
                self.attrs['product_codes'] = [value]
        elif name == 'imageId':
            self.image_id = value
        elif name == 'kernel':
            self.kernel = value
        elif name == 'ramdisk':
            self.ramdisk = value
        else:
            setattr(self, name, value)
