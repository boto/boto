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

"""
Represents a connection to the EC2 service.
"""

import urllib
import base64
import boto
from boto.connection import AWSQueryConnection
from boto.resultset import ResultSet
from boto.ec2.image import Image, ImageAttribute
from boto.ec2.instance import Reservation, Instance, ConsoleOutput, InstanceAttribute
from boto.ec2.keypair import KeyPair
from boto.ec2.address import Address
from boto.ec2.volume import Volume
from boto.ec2.snapshot import Snapshot
from boto.ec2.snapshot import SnapshotAttribute
from boto.ec2.zone import Zone
from boto.ec2.securitygroup import SecurityGroup
from boto.ec2.regioninfo import RegionInfo
from boto.ec2.instanceinfo import InstanceInfo
from boto.ec2.reservedinstance import ReservedInstancesOffering, ReservedInstance
from boto.ec2.spotinstancerequest import SpotInstanceRequest
from boto.ec2.spotpricehistory import SpotPriceHistory
from boto.ec2.spotdatafeedsubscription import SpotDatafeedSubscription
from boto.exception import EC2ResponseError

#boto.set_stream_logger('ec2')

class EC2Connection(AWSQueryConnection):

    APIVersion = boto.config.get('Boto', 'ec2_version', '2009-11-30')
    DefaultRegionName = boto.config.get('Boto', 'ec2_region_name', 'us-east-1')
    DefaultRegionEndpoint = boto.config.get('Boto', 'ec2_region_endpoint',
                                            'ec2.amazonaws.com')
    SignatureVersion = '2'
    ResponseError = EC2ResponseError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, host=None, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None, path='/'):
        """
        Init method to create a new connection to EC2.

        B{Note:} The host argument is overridden by the host specified in the boto configuration file.
        """
        if not region:
            region = RegionInfo(self, self.DefaultRegionName, self.DefaultRegionEndpoint)
        self.region = region
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
                                    proxy_user, proxy_pass,
                                    self.region.endpoint, debug,
                                    https_connection_factory, path)

    def get_params(self):
        """
        Returns a dictionary containing the value of of all of the keyword
        arguments passed when constructing this connection.
        """
        param_names = ['aws_access_key_id', 'aws_secret_access_key', 'is_secure',
                       'port', 'proxy', 'proxy_port', 'proxy_user', 'proxy_pass',
                       'debug', 'https_connection_factory']
        params = {}
        for name in param_names:
            params[name] = getattr(self, name)
        return params

    # Image methods

    def get_all_images(self, image_ids=None, owners=None, executable_by=None):
        """
        Retrieve all the EC2 images available on your account.

        :type image_ids: list
        :param image_ids: A list of strings with the image IDs wanted

        :type owners: list
        :param owners: A list of owner IDs

        :type executable_by:
        :param executable_by:

        :rtype: list
        :return: A list of :class:`boto.ec2.image.Image`
        """
        params = {}
        if image_ids:
            self.build_list_params(params, image_ids, 'ImageId')
        if owners:
            self.build_list_params(params, owners, 'Owner')
        if executable_by:
            self.build_list_params(params, executable_by, 'ExecutableBy')
        return self.get_list('DescribeImages', params, [('item', Image)])

    def get_all_kernels(self, kernel_ids=None, owners=None):
        """
        Retrieve all the EC2 kernels available on your account.  Simply filters the list returned
        by get_all_images because EC2 does not provide a way to filter server-side.

        :type kernel_ids: list
        :param kernel_ids: A list of strings with the image IDs wanted

        :type owners: list
        :param owners: A list of owner IDs

        :rtype: list
        :return: A list of :class:`boto.ec2.image.Image`
        """
        rs = self.get_all_images(kernel_ids, owners)
        kernels = []
        for image in rs:
            if image.type == 'kernel':
                kernels.append(image)
        return kernels

    def get_all_ramdisks(self, ramdisk_ids=None, owners=None):
        """
        Retrieve all the EC2 ramdisks available on your account.
        Simply filters the list returned by get_all_images because
        EC2 does not provide a way to filter server-side.

        :type ramdisk_ids: list
        :param ramdisk_ids: A list of strings with the image IDs wanted

        :type owners: list
        :param owners: A list of owner IDs

        :rtype: list
        :return: A list of :class:`boto.ec2.image.Image`
        """
        rs = self.get_all_images(ramdisk_ids, owners)
        ramdisks = []
        for image in rs:
            if image.type == 'ramdisk':
                ramdisks.append(image)
        return ramdisks

    def get_image(self, image_id):
        """
        Shortcut method to retrieve a specific image (AMI).

        :type image_id: string
        :param image_id: the ID of the Image to retrieve

        :rtype: :class:`boto.ec2.image.Image`
        :return: The EC2 Image specified or None if the image is not found
        """
        try:
            return self.get_all_images(image_ids=[image_id])[0]
        except IndexError: # None of those images available
            return None

    def register_image(self, name=None, description=None, image_location=None,
                       architecture=None, kernel_id=None, ramdisk_id=None,
                       root_device_name=None, block_device_map=None):
        """
        Register an image.

        :type name: string
        :param name: The name of the AMI.  Valid only for EBS-based images.

        :type description: string
        :param description: The description of the AMI.

        :type image_location: string
        :param image_location: Full path to your AMI manifest in Amazon S3 storage.
                               Only used for S3-based AMI's.

        :type architecture: string
        :param architecture: The architecture of the AMI.  Valid choices are:
                             i386 | x86_64

        :type kernel_id: string
        :param kernel_id: The ID of the kernel with which to launch the instances

        :type root_device_name: string
        :param root_device_name: The root device name (e.g. /dev/sdh)

        :type block_device_map: :class:`boto.ec2.blockdevicemapping.BlockDeviceMapping`
        :param block_device_map: A BlockDeviceMapping data structure
                                 describing the EBS volumes associated
                                 with the Image.

        :rtype: string
        :return: The new image id
        """
        params = {}
        if name:
            params['Name'] = name
        if description:
            params['Description'] = description
        if architecture:
            params['Architecture'] = architecture
        if kernel_id:
            params['KernelId'] = kernel_id
        if ramdisk_id:
            params['RamdiskId'] = ramdisk_id
        if image_location:
            params['ImageLocation'] = image_location
        if root_device_name:
            params['RootDeviceName'] = root_device_name
        if block_device_map:
            block_device_map.build_list_params(params)
        rs = self.get_object('RegisterImage', params, ResultSet)
        image_id = getattr(rs, 'imageId', None)
        return image_id

    def deregister_image(self, image_id):
        """
        Unregister an AMI.

        :type image_id: string
        :param image_id: the ID of the Image to unregister

        :rtype: bool
        :return: True if successful
        """
        return self.get_status('DeregisterImage', {'ImageId':image_id})

    def create_image(self, instance_id, name, description=None, no_reboot=False):
        """
        Will create an AMI from the instance in the running or stopped
        state.
        
        :type instance_id: string
        :param instance_id: the ID of the instance to image.

        :type name: string
        :param name: The name of the new image

        :type description: string
        :param description: An optional human-readable string describing
                            the contents and purpose of the AMI.

        :type no_reboot: bool
        :param no_reboot: An optional flag indicating that the bundling process
                          should not attempt to shutdown the instance before
                          bundling.  If this flag is True, the responsibility
                          of maintaining file system integrity is left to the
                          owner of the instance.
        
        :rtype: string
        :return: The new image id
        """
        params = {'InstanceId' : instance_id,
                  'Name' : name}
        if description:
            params['Description'] = description
        if no_reboot:
            params['NoReboot'] = 'true'
        rs = self.get_object('CreateImage', params, Image)
        image_id = getattr(rs, 'imageId', None)
        if not image_id:
            image_id = getattr(rs, 'ImageId', None)
        return image_id
        
    # ImageAttribute methods

    def get_image_attribute(self, image_id, attribute='launchPermission'):
        """
        Gets an attribute from an image.
        See http://docs.amazonwebservices.com/AWSEC2/2008-02-01/DeveloperGuide/ApiReference-Query-DescribeImageAttribute.html

        :type image_id: string
        :param image_id: The Amazon image id for which you want info about

        :type attribute: string
        :param attribute: The attribute you need information about.
                          Valid choices are:
                          * launchPermission
                          * productCodes
                          * blockDeviceMapping

        :rtype: :class:`boto.ec2.image.ImageAttribute`
        :return: An ImageAttribute object representing the value of the attribute requested
        """
        params = {'ImageId' : image_id,
                  'Attribute' : attribute}
        return self.get_object('DescribeImageAttribute', params, ImageAttribute)

    def modify_image_attribute(self, image_id, attribute='launchPermission',
                               operation='add', user_ids=None, groups=None,
                               product_codes=None):
        """
        Changes an attribute of an image.
        See http://docs.amazonwebservices.com/AWSEC2/latest/APIReference/ApiReference-query-ModifyImageAttribute.html

        :type image_id: string
        :param image_id: The image id you wish to change

        :type attribute: string
        :param attribute: The attribute you wish to change

        :type operation: string
        :param operation: Either add or remove (this is required for changing launchPermissions)

        :type user_ids: list
        :param user_ids: The Amazon IDs of users to add/remove attributes

        :type groups: list
        :param groups: The groups to add/remove attributes

        :type product_codes: list
        :param product_codes: Amazon DevPay product code. Currently only one
                              product code can be associated with an AMI. Once
                              set, the product code cannot be changed or reset.
        """
        params = {'ImageId' : image_id,
                  'Attribute' : attribute,
                  'OperationType' : operation}
        if user_ids:
            self.build_list_params(params, user_ids, 'UserId')
        if groups:
            self.build_list_params(params, groups, 'UserGroup')
        if product_codes:
            self.build_list_params(params, product_codes, 'ProductCode')
        return self.get_status('ModifyImageAttribute', params)

    def reset_image_attribute(self, image_id, attribute='launchPermission'):
        """
        Resets an attribute of an AMI to its default value.
        See http://docs.amazonwebservices.com/AWSEC2/2008-02-01/DeveloperGuide/ApiReference-Query-ResetImageAttribute.html

        :type image_id: string
        :param image_id: ID of the AMI for which an attribute will be described

        :type attribute: string
        :param attribute: The attribute to reset

        :rtype: bool
        :return: Whether the operation succeeded or not
        """
        params = {'ImageId' : image_id,
                  'Attribute' : attribute}
        return self.get_status('ResetImageAttribute', params)

    # Instance methods

    def get_all_instances(self, instance_ids=None):
        """
        Retrieve all the instances associated with your account.

        :type instance_ids: list
        :param instance_ids: A list of strings of instance IDs

        :rtype: list
        :return: A list of  :class:`boto.ec2.instance.Reservation`
        """
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_list('DescribeInstances', params, [('item', Reservation)])

    def run_instances(self, image_id, min_count=1, max_count=1,
                      key_name=None, security_groups=None,
                      user_data=None, addressing_type=None,
                      instance_type='m1.small', placement=None,
                      kernel_id=None, ramdisk_id=None,
                      monitoring_enabled=False, subnet_id=None,
                      block_device_map=None):
        """
        Runs an image on EC2.

        :type image_id: string
        :param image_id: The ID of the image to run

        :type min_count: int
        :param min_count: The minimum number of instances to launch

        :type max_count: int
        :param max_count: The maximum number of instances to launch

        :type key_name: string
        :param key_name: The name of the key pair with which to launch instances

        :type security_groups: list of strings
        :param security_groups: The names of the security groups with which to associate instances

        :type user_data: string
        :param user_data: The user data passed to the launched instances

        :type instance_type: string
        :param instance_type: The type of instance to run (m1.small, m1.large, m1.xlarge)

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

        :type block_device_map: :class:`boto.ec2.blockdevicemapping.BlockDeviceMapping`
        :param block_device_map: A BlockDeviceMapping data structure
                                 describing the EBS volumes associated
                                 with the Image.

        :rtype: Reservation
        :return: The :class:`boto.ec2.instance.Reservation` associated with the request for machines
        """
        params = {'ImageId':image_id,
                  'MinCount':min_count,
                  'MaxCount': max_count}
        if key_name:
            params['KeyName'] = key_name
        if security_groups:
            l = []
            for group in security_groups:
                if isinstance(group, SecurityGroup):
                    l.append(group.name)
                else:
                    l.append(group)
            self.build_list_params(params, l, 'SecurityGroup')
        if user_data:
            params['UserData'] = base64.b64encode(user_data)
        if addressing_type:
            params['AddressingType'] = addressing_type
        if instance_type:
            params['InstanceType'] = instance_type
        if placement:
            params['Placement.AvailabilityZone'] = placement
        if kernel_id:
            params['KernelId'] = kernel_id
        if ramdisk_id:
            params['RamdiskId'] = ramdisk_id
        if monitoring_enabled:
            params['Monitoring.Enabled'] = 'true'
        if subnet_id:
            params['SubnetId'] = subnet_id
        if block_device_map:
            block_device_map.build_list_params(params)
        return self.get_object('RunInstances', params, Reservation, verb='POST')

    def terminate_instances(self, instance_ids=None):
        """
        Terminate the instances specified

        :type instance_ids: list
        :param instance_ids: A list of strings of the Instance IDs to terminate

        :rtype: list
        :return: A list of the instances terminated
        """
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_list('TerminateInstances', params, [('item', Instance)])

    def stop_instances(self, instance_ids=None, force=False):
        """
        Stop the instances specified
        
        :type instance_ids: list
        :param instance_ids: A list of strings of the Instance IDs to stop

        :type force: bool
        :param force: Forces the instance to stop
        
        :rtype: list
        :return: A list of the instances stopped
        """
        params = {}
        if force:
            params['Force'] = 'true'
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_list('StopInstances', params, [('item', Instance)])

    def start_instances(self, instance_ids=None):
        """
        Start the instances specified
        
        :type instance_ids: list
        :param instance_ids: A list of strings of the Instance IDs to start
        
        :rtype: list
        :return: A list of the instances started
        """
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_list('StartInstances', params, [('item', Instance)])

    def get_console_output(self, instance_id):
        """
        Retrieves the console output for the specified instance.
        See http://docs.amazonwebservices.com/AWSEC2/2008-02-01/DeveloperGuide/ApiReference-Query-GetConsoleOutput.html

        :type instance_id: string
        :param instance_id: The instance ID of a running instance on the cloud.

        :rtype: :class:`boto.ec2.instance.ConsoleOutput`
        :return: The console output as a ConsoleOutput object
        """
        params = {}
        self.build_list_params(params, [instance_id], 'InstanceId')
        return self.get_object('GetConsoleOutput', params, ConsoleOutput)

    def reboot_instances(self, instance_ids=None):
        """
        Reboot the specified instances.

        :type instance_ids: list
        :param instance_ids: The instances to terminate and reboot
        """
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_status('RebootInstances', params)

    def confirm_product_instance(self, product_code, instance_id):
        params = {'ProductCode' : product_code,
                  'InstanceId' : instance_id}
        rs = self.get_object('ConfirmProductInstance', params, ResultSet)
        return (rs.status, rs.ownerId)

    # InstanceAttribute methods

    def get_instance_attribute(self, instance_id, attribute):
        """
        Gets an attribute from an instance.

        :type instance_id: string
        :param instance_id: The Amazon id of the instance

        :type attribute: string
        :param attribute: The attribute you need information about
                          Valid choices are:
                          instanceType|kernel|ramdisk|userData|
                          disableApiTermination|
                          instanceInitiatedShutdownBehavior|
                          rootDeviceName|blockDeviceMapping

        :rtype: :class:`boto.ec2.image.ImageAttribute`
        :return: An ImageAttribute object representing the value of the attribute requested
        """
        params = {'InstanceId' : instance_id}
        if attribute:
            params['Attribute'] = attribute
        return self.get_object('DescribeInstanceAttribute', params, InstanceAttribute)

    def modify_instance_attribute(self, instance_id, attribute, value):
        """
        Changes an attribute of an instance

        :type instance_id: string
        :param instance_id: The instance id you wish to change

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
        params = {'InstanceId' : instance_id,
                  'Attribute' : attribute,
                  'Value' : value}
        return self.get_status('ModifyInstanceAttribute', params)

    def reset_instance_attribute(self, instance_id, attribute):
        """
        Resets an attribute of an instance to its default value.

        :type instance_id: string
        :param instance_id: ID of the instance

        :type attribute: string
        :param attribute: The attribute to reset. Valid values are:
                          kernel|ramdisk

        :rtype: bool
        :return: Whether the operation succeeded or not
        """
        params = {'InstanceId' : instance_id,
                  'Attribute' : attribute}
        return self.get_status('ResetInstanceAttribute', params)

    # Spot Instances

    def get_all_spot_instance_requests(self, request_ids=None):
        """
        Retrieve all the spot instances requests associated with your account.
        
        @type request_ids: list
        @param request_ids: A list of strings of spot instance request IDs
        
        @rtype: list
        @return: A list of
                 :class:`boto.ec2.spotinstancerequest.SpotInstanceRequest`
        """
        params = {}
        if request_ids:
            self.build_list_params(params, request_ids, 'SpotInstanceRequestId')
        return self.get_list('DescribeSpotInstanceRequests', params,
                             [('item', SpotInstanceRequest)])

    def get_spot_price_history(self, start_time=None, end_time=None,
                               instance_type=None, product_description=None):
        """
        Retrieve the recent history of spot instances pricing.
        
        @type start_time: str
        @param start_time: An indication of how far back to provide price
                           changes for. An ISO8601 DateTime string.
        
        @type end_time: str
        @param end_time: An indication of how far forward to provide price
                         changes for.  An ISO8601 DateTime string.
        
        @type instance_type: str
        @param instance_type: Filter responses to a particular instance type.
        
        @type product_description: str
        @param product_descripton: Filter responses to a particular platform.
                                   Valid values are currently: Linux
        
        @rtype: list
        @return: A list tuples containing price and timestamp.
        """
        params = {}
        if start_time:
            params['StartTime'] = start_time
        if end_time:
            params['EndTime'] = end_time
        if instance_type:
            params['InstanceType'] = instance_type
        if product_description:
            params['ProductDescription'] = product_description
        return self.get_list('DescribeSpotPriceHistory', params, [('item', SpotPriceHistory)])

    def request_spot_instances(self, price, image_id, count=1, type=None,
                               valid_from=None, valid_until=None,
                               launch_group=None, availability_zone_group=None,
                               key_name=None, security_groups=None,
                               user_data=None, addressing_type=None,
                               instance_type='m1.small', placement=None,
                               kernel_id=None, ramdisk_id=None,
                               monitoring_enabled=False, subnet_id=None,
                               block_device_map=None):
        """
        Request instances on the spot market at a particular price.

        :type price: str
        :param price: The maximum price of your bid
        
        :type image_id: string
        :param image_id: The ID of the image to run

        :type count: int
        :param count: The of instances to requested
        
        :type type: str
        :param type: Type of request. Can be 'one-time' or 'persistent'.
                     Default is one-time.

        :type valid_from: str
        :param valid_from: Start date of the request. An ISO8601 time string.

        :type valid_until: str
        :param valid_until: End date of the request.  An ISO8601 time string.

        :type launch_group: str
        :param launch_group: If supplied, all requests will be fulfilled
                             as a group.
                             
        :type availability_zone_group: str
        :param availability_zone_group: If supplied, all requests will be fulfilled
                                        within a single availability zone.
                             
        :type key_name: string
        :param key_name: The name of the key pair with which to launch instances

        :type security_groups: list of strings
        :param security_groups: The names of the security groups with which to associate instances

        :type user_data: string
        :param user_data: The user data passed to the launched instances

        :type instance_type: string
        :param instance_type: The type of instance to run (m1.small, m1.large, m1.xlarge)

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

        :type block_device_map: :class:`boto.ec2.blockdevicemapping.BlockDeviceMapping`
        :param block_device_map: A BlockDeviceMapping data structure
                                 describing the EBS volumes associated
                                 with the Image.

        :rtype: Reservation
        :return: The :class:`boto.ec2.instance.Reservation` associated with the request for machines
        """
        params = {'LaunchSpecification.ImageId':image_id,
                  'SpotPrice' : price}
        if count:
            params['InstanceCount'] = count
        if valid_from:
            params['ValidFrom'] = valid_from
        if valid_until:
            params['ValidUntil'] = valid_until
        if launch_group:
            params['LaunchGroup'] = launch_group
        if availability_zone_group:
            params['AvailabilityZoneGroup'] = availability_zone_group
        if key_name:
            params['LaunchSpecification.KeyName'] = key_name
        if security_groups:
            l = []
            for group in security_groups:
                if isinstance(group, SecurityGroup):
                    l.append(group.name)
                else:
                    l.append(group)
            self.build_list_params(params, l,
                                   'LaunchSpecification.SecurityGroup')
        if user_data:
            params['LaunchSpecification.UserData'] = base64.b64encode(user_data)
        if addressing_type:
            params['LaunchSpecification.AddressingType'] = addressing_type
        if instance_type:
            params['LaunchSpecification.InstanceType'] = instance_type
        if placement:
            params['LaunchSpecification.Placement.AvailabilityZone'] = placement
        if kernel_id:
            params['LaunchSpecification.KernelId'] = kernel_id
        if ramdisk_id:
            params['LaunchSpecification.RamdiskId'] = ramdisk_id
        if monitoring_enabled:
            params['LaunchSpecification.Monitoring.Enabled'] = 'true'
        if subnet_id:
            params['LaunchSpecification.SubnetId'] = subnet_id
        if block_device_map:
            block_device_map.build_list_params(params, 'LaunchSpecification.')
        return self.get_list('RequestSpotInstances', params,
                             [('item', SpotInstanceRequest)],
                             verb='POST')

        
    def cancel_spot_instance_requests(self, request_ids):
        """
        Cancel the specified Spot Instance Requests.
        
        :type request_ids: list
        :param request_ids: A list of strings of the Request IDs to terminate
        
        :rtype: list
        :return: A list of the instances terminated
        """
        params = {}
        if request_ids:
            self.build_list_params(params, request_ids, 'SpotInstanceRequestId')
        return self.get_list('CancelSpotInstanceRequests', params, [('item', Instance)])

    def get_spot_datafeed_subscription(self):
        """
        Return the current spot instance data feed subscription
        associated with this account, if any.
        
        :rtype: :class:`boto.ec2.spotdatafeedsubscription.SpotDatafeedSubscription`
        :return: The datafeed subscription object or None
        """
        return self.get_object('DescribeSpotDatafeedSubscription',
                               None, SpotDatafeedSubscription)

    def create_spot_datafeed_subscription(self, bucket, prefix):
        """
        Create a spot instance datafeed subscription for this account.

        :type bucket: str or unicode
        :param bucket: The name of the bucket where spot instance data
                       will be written.  The account issuing this request
                       must have FULL_CONTROL access to the bucket
                       specified in the request.

        :type prefix: str or unicode
        :param prefix: An optional prefix that will be pre-pended to all
                       data files written to the bucket.
                       
        :rtype: :class:`boto.ec2.spotdatafeedsubscription.SpotDatafeedSubscription`
        :return: The datafeed subscription object or None
        """
        params = {'Bucket' : bucket}
        if prefix:
            params['Prefix'] = prefix
        return self.get_object('CreateSpotDatafeedSubscription',
                               params, SpotDatafeedSubscription)

    def delete_spot_datafeed_subscription(self):
        """
        Delete the current spot instance data feed subscription
        associated with this account
        
        :rtype: bool
        :return: True if successful
        """
        return self.get_status('DeleteSpotDatafeedSubscription', None)

    # Zone methods

    def get_all_zones(self, zones=None):
        """
        Get all Availability Zones associated with the current region.

        :type zones: list
        :param zones: Optional list of zones.  If this list is present,
                      only the Zones associated with these zone names
                      will be returned.

        :rtype: list of L{boto.ec2.zone.Zone}
        :return: The requested Zone objects
        """
        params = {}
        if zones:
            self.build_list_params(params, zones, 'ZoneName')
        return self.get_list('DescribeAvailabilityZones', params, [('item', Zone)])

    # Address methods

    def get_all_addresses(self, addresses=None):
        """
        Get all EIP's associated with the current credentials.

        :type addresses: list
        :param addresses: Optional list of addresses.  If this list is present,
                           only the Addresses associated with these addresses
                           will be returned.

        :rtype: list of L{boto.ec2.address.Address}
        :return: The requested Address objects
        """
        params = {}
        if addresses:
            self.build_list_params(params, addresses, 'PublicIp')
        return self.get_list('DescribeAddresses', params, [('item', Address)])

    def allocate_address(self):
        """
        Allocate a new Elastic IP address and associate it with your account.

        :rtype: L{boto.ec2.address.Address}
        :return: The newly allocated Address
        """
        return self.get_object('AllocateAddress', None, Address)

    def associate_address(self, instance_id, public_ip):
        """
        Associate an Elastic IP address with a currently running instance.

        :type instance_id: string
        :param instance_id: The ID of the instance

        :type public_ip: string
        :param public_ip: The public IP address

        :rtype: bool
        :return: True if successful
        """
        params = {'InstanceId' : instance_id, 'PublicIp' : public_ip}
        return self.get_status('AssociateAddress', params)

    def disassociate_address(self, public_ip):
        """
        Disassociate an Elastic IP address from a currently running instance.

        :type public_ip: string
        :param public_ip: The public IP address

        :rtype: bool
        :return: True if successful
        """
        params = {'PublicIp' : public_ip}
        return self.get_status('DisassociateAddress', params)

    def release_address(self, public_ip):
        """
        Free up an Elastic IP address

        :type public_ip: string
        :param public_ip: The public IP address

        :rtype: bool
        :return: True if successful
        """
        params = {'PublicIp' : public_ip}
        return self.get_status('ReleaseAddress', params)

    # Volume methods

    def get_all_volumes(self, volume_ids=None):
        """
        Get all Volumes associated with the current credentials.

        :type volume_ids: list
        :param volume_ids: Optional list of volume ids.  If this list is present,
                           only the volumes associated with these volume ids
                           will be returned.

        :rtype: list of L{boto.ec2.volume.Volume}
        :return: The requested Volume objects
        """
        params = {}
        if volume_ids:
            self.build_list_params(params, volume_ids, 'VolumeId')
        return self.get_list('DescribeVolumes', params, [('item', Volume)])

    def create_volume(self, size, zone, snapshot=None):
        """
        Create a new EBS Volume.

        :type size: int
        :param size: The size of the new volume, in GiB

        :type zone: string or L{boto.ec2.zone.Zone}
        :param zone: The availability zone in which the Volume will be created.

        :type snapshot: string or L{boto.ec2.snapshot.Snapshot}
        :param snapshot: The snapshot from which the new Volume will be created.
        """
        if isinstance(zone, Zone):
            zone = zone.name
        params = {'AvailabilityZone' : zone}
        if size:
            params['Size'] = size
        if snapshot:
            if isinstance(snapshot, Snapshot):
                snapshot = snapshot.id
            params['SnapshotId'] = snapshot
        return self.get_object('CreateVolume', params, Volume)

    def delete_volume(self, volume_id):
        """
        Delete an EBS volume.

        :type volume_id: str
        :param volume_id: The ID of the volume to be delete.

        :rtype: bool
        :return: True if successful
        """
        params = {'VolumeId': volume_id}
        return self.get_status('DeleteVolume', params)

    def attach_volume(self, volume_id, instance_id, device):
        """
        Attach an EBS volume to an EC2 instance.

        :type volume_id: str
        :param volume_id: The ID of the EBS volume to be attached.

        :type instance_id: str
        :param instance_id: The ID of the EC2 instance to which it will
                            be attached.

        :type device: str
        :param device: The device on the instance through which the
                       volume will be exposted (e.g. /dev/sdh)

        :rtype: bool
        :return: True if successful
        """
        params = {'InstanceId' : instance_id,
                  'VolumeId' : volume_id,
                  'Device' : device}
        return self.get_status('AttachVolume', params)

    def detach_volume(self, volume_id, instance_id=None, device=None, force=False):
        """
        Detach an EBS volume from an EC2 instance.

        :type volume_id: str
        :param volume_id: The ID of the EBS volume to be attached.

        :type instance_id: str
        :param instance_id: The ID of the EC2 instance from which it will
                            be detached.

        :type device: str
        :param device: The device on the instance through which the
                       volume is exposted (e.g. /dev/sdh)

        :type force: bool
        :param force: Forces detachment if the previous detachment attempt did
                      not occur cleanly.  This option can lead to data loss or
                      a corrupted file system. Use this option only as a last
                      resort to detach a volume from a failed instance. The
                      instance will not have an opportunity to flush file system
                      caches nor file system meta data. If you use this option,
                      you must perform file system check and repair procedures.

        :rtype: bool
        :return: True if successful
        """
        params = {'VolumeId' : volume_id}
        if instance_id:
            params['InstanceId'] = instance_id
        if device:
            params['Device'] = device
        if force:
            params['Force'] = 'true'
        return self.get_status('DetachVolume', params)

    # Snapshot methods

    def get_all_snapshots(self, snapshot_ids=None, owner=None, restorable_by=None):
        """
        Get all EBS Snapshots associated with the current credentials.

        :type snapshot_ids: list
        :param snapshot_ids: Optional list of snapshot ids.  If this list is present,
                           only the Snapshots associated with these snapshot ids
                           will be returned.

        :type owner: str
        :param owner: If present, only the snapshots owned by the specified user
                      will be returned.  Valid values are:
                      self | amazon | AWS Account ID

        :type restorable_by: str
        :param restorable_by: If present, only the snapshots that are restorable
                              by the specified account id will be returned.

        :rtype: list of L{boto.ec2.snapshot.Snapshot}
        :return: The requested Snapshot objects
        """
        params = {}
        if snapshot_ids:
            self.build_list_params(params, snapshot_ids, 'SnapshotId')
        if owner:
            params['Owner'] = owner
        if restorable_by:
            params['RestorableBy'] = restorable_by
        return self.get_list('DescribeSnapshots', params, [('item', Snapshot)])

    def create_snapshot(self, volume_id, description=None):
        """
        Create a snapshot of an existing EBS Volume.

        :type volume_id: str
        :param volume_id: The ID of the volume to be snapshot'ed

        :type description: str
        :param description: A description of the snapshot.  Limited to 255 characters.

        :rtype: bool
        :return: True if successful
        """
        params = {'VolumeId' : volume_id}
        if description:
            params['Description'] = description[0:255]
        return self.get_object('CreateSnapshot', params, Snapshot)

    def delete_snapshot(self, snapshot_id):
        params = {'SnapshotId': snapshot_id}
        return self.get_status('DeleteSnapshot', params)

    def get_snapshot_attribute(self, snapshot_id, attribute='createVolumePermission'):
        """
        Get information about an attribute of a snapshot.  Only one attribute can be
        specified per call.

        :type snapshot_id: str
        :param snapshot_id: The ID of the snapshot.

        :type attribute: str
        :param attribute: The requested attribute.  Valid values are:
                          createVolumePermission

        :rtype: list of L{boto.ec2.snapshotattribute.SnapshotAttribute}
        :return: The requested Snapshot attribute
        """
        params = {'Attribute' : attribute}
        if snapshot_id:
            params['SnapshotId'] = snapshot_id
        return self.get_object('DescribeSnapshotAttribute', params, SnapshotAttribute)

    def modify_snapshot_attribute(self, snapshot_id, attribute='createVolumePermission',
                                  operation='add', user_ids=None, groups=None):
        """
        Changes an attribute of an image.

        :type snapshot_id: string
        :param snapshot_id: The snapshot id you wish to change

        :type attribute: string
        :param attribute: The attribute you wish to change.  Valid values are:
                          createVolumePermission

        :type operation: string
        :param operation: Either add or remove (this is required for changing
                          snapshot ermissions)

        :type user_ids: list
        :param user_ids: The Amazon IDs of users to add/remove attributes

        :type groups: list
        :param groups: The groups to add/remove attributes.  The only valid
                       value at this time is 'all'.

        """
        params = {'SnapshotId' : snapshot_id,
                  'Attribute' : attribute,
                  'OperationType' : operation}
        if user_ids:
            self.build_list_params(params, user_ids, 'UserId')
        if groups:
            self.build_list_params(params, groups, 'UserGroup')
        return self.get_status('ModifySnapshotAttribute', params)

    def reset_snapshot_attribute(self, snapshot_id, attribute='createVolumePermission'):
        """
        Resets an attribute of a snapshot to its default value.

        :type snapshot_id: string
        :param snapshot_id: ID of the snapshot

        :type attribute: string
        :param attribute: The attribute to reset

        :rtype: bool
        :return: Whether the operation succeeded or not
        """
        params = {'SnapshotId' : snapshot_id,
                  'Attribute' : attribute}
        return self.get_status('ResetSnapshotAttribute', params)

    # Keypair methods

    def get_all_key_pairs(self, keynames=None):
        """
        Get all key pairs associated with your account.

        :type keynames: list
        :param keynames: A list of the names of keypairs to retrieve.
                         If not provided, all key pairs will be returned.

        :rtype: list
        :return: A list of :class:`boto.ec2.keypair.KeyPair`
        """
        params = {}
        if keynames:
            self.build_list_params(params, keynames, 'KeyName')
        return self.get_list('DescribeKeyPairs', params, [('item', KeyPair)])

    def get_key_pair(self, keyname):
        """
        Convenience method to retrieve a specific keypair (KeyPair).

        :type image_id: string
        :param image_id: the ID of the Image to retrieve

        :rtype: :class:`boto.ec2.keypair.KeyPair`
        :return: The KeyPair specified or None if it is not found
        """
        try:
            return self.get_all_key_pairs(keynames=[keyname])[0]
        except IndexError: # None of those key pairs available
            return None

    def create_key_pair(self, key_name):
        """
        Create a new key pair for your account.
        This will create the key pair within the region you
        are currently connected to.

        :type key_name: string
        :param key_name: The name of the new keypair

        :rtype: :class:`boto.ec2.keypair.KeyPair`
        :return: The newly created :class:`boto.ec2.keypair.KeyPair`.
                 The material attribute of the new KeyPair object
                 will contain the the unencrypted PEM encoded RSA private key.
        """
        params = {'KeyName':key_name}
        return self.get_object('CreateKeyPair', params, KeyPair)

    def delete_key_pair(self, key_name):
        """
        Delete a key pair from your account.

        :type key_name: string
        :param key_name: The name of the keypair to delete
        """
        params = {'KeyName':key_name}
        return self.get_status('DeleteKeyPair', params)

    # SecurityGroup methods

    def get_all_security_groups(self, groupnames=None):
        """
        Get all security groups associated with your account in a region.

        :type groupnames: list
        :param groupnames: A list of the names of security groups to retrieve.
                           If not provided, all security groups will be returned.

        :rtype: list
        :return: A list of :class:`boto.ec2.securitygroup.SecurityGroup`
        """
        params = {}
        if groupnames:
            self.build_list_params(params, groupnames, 'GroupName')
        return self.get_list('DescribeSecurityGroups', params, [('item', SecurityGroup)])

    def create_security_group(self, name, description):
        """
        Create a new security group for your account.
        This will create the security group within the region you
        are currently connected to.

        :type name: string
        :param name: The name of the new security group

        :type description: string
        :param description: The description of the new security group

        :rtype: :class:`boto.ec2.securitygroup.SecurityGroup`
        :return: The newly created :class:`boto.ec2.keypair.KeyPair`.
        """
        params = {'GroupName':name, 'GroupDescription':description}
        group = self.get_object('CreateSecurityGroup', params, SecurityGroup)
        group.name = name
        group.description = description
        return group

    def delete_security_group(self, name):
        """
        Delete a security group from your account.

        :type key_name: string
        :param key_name: The name of the keypair to delete
        """
        params = {'GroupName':name}
        return self.get_status('DeleteSecurityGroup', params)

    def authorize_security_group(self, group_name, src_security_group_name=None,
                                 src_security_group_owner_id=None,
                                 ip_protocol=None, from_port=None, to_port=None,
                                 cidr_ip=None):
        """
        Add a new rule to an existing security group.
        You need to pass in either src_security_group_name and
        src_security_group_owner_id OR ip_protocol, from_port, to_port,
        and cidr_ip.  In other words, either you are authorizing another
        group or you are authorizing some ip-based rule.

        :type group_name: string
        :param group_name: The name of the security group you are adding
                           the rule to.

        :type src_security_group_name: string
        :param src_security_group_name: The name of the security group you are
                                        granting access to.

        :type src_security_group_owner_id: string
        :param src_security_group_owner_id: The ID of the owner of the security group you are
                                            granting access to.

        :type ip_protocol: string
        :param ip_protocol: Either tcp | udp | icmp

        :type from_port: int
        :param from_port: The beginning port number you are enabling

        :type to_port: int
        :param to_port: The ending port number you are enabling

        :type to_port: string
        :param to_port: The CIDR block you are providing access to.
                        See http://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing

        :rtype: bool
        :return: True if successful.
        """
        params = {'GroupName':group_name}
        if src_security_group_name:
            params['SourceSecurityGroupName'] = src_security_group_name
        if src_security_group_owner_id:
            params['SourceSecurityGroupOwnerId'] = src_security_group_owner_id
        if ip_protocol:
            params['IpProtocol'] = ip_protocol
        if from_port:
            params['FromPort'] = from_port
        if to_port:
            params['ToPort'] = to_port
        if cidr_ip:
            params['CidrIp'] = urllib.quote(cidr_ip)
        return self.get_status('AuthorizeSecurityGroupIngress', params)

    def revoke_security_group(self, group_name, src_security_group_name=None,
                              src_security_group_owner_id=None,
                              ip_protocol=None, from_port=None, to_port=None,
                              cidr_ip=None):
        """
        Remove an existing rule from an existing security group.
        You need to pass in either src_security_group_name and
        src_security_group_owner_id OR ip_protocol, from_port, to_port,
        and cidr_ip.  In other words, either you are revoking another
        group or you are revoking some ip-based rule.

        :type group_name: string
        :param group_name: The name of the security group you are removing
                           the rule from.

        :type src_security_group_name: string
        :param src_security_group_name: The name of the security group you are
                                        revoking access to.

        :type src_security_group_owner_id: string
        :param src_security_group_owner_id: The ID of the owner of the security group you are
                                            revoking access to.

        :type ip_protocol: string
        :param ip_protocol: Either tcp | udp | icmp

        :type from_port: int
        :param from_port: The beginning port number you are disabling

        :type to_port: int
        :param to_port: The ending port number you are disabling

        :type to_port: string
        :param to_port: The CIDR block you are revoking access to.
                        See http://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing

        :rtype: bool
        :return: True if successful.
        """
        params = {'GroupName':group_name}
        if src_security_group_name:
            params['SourceSecurityGroupName'] = src_security_group_name
        if src_security_group_owner_id:
            params['SourceSecurityGroupOwnerId'] = src_security_group_owner_id
        if ip_protocol:
            params['IpProtocol'] = ip_protocol
        if from_port:
            params['FromPort'] = from_port
        if to_port:
            params['ToPort'] = to_port
        if cidr_ip:
            params['CidrIp'] = cidr_ip
        return self.get_status('RevokeSecurityGroupIngress', params)

    #
    # Regions
    #

    def get_all_regions(self):
        """
        Get all available regions for the EC2 service.

        :rtype: list
        :return: A list of :class:`boto.ec2.regioninfo.RegionInfo`
        """
        return self.get_list('DescribeRegions', None, [('item', RegionInfo)])

    #
    # Reservation methods
    #

    def get_all_reserved_instances_offerings(self, reserved_instances_id=None,
                                             instance_type=None,
                                             availability_zone=None,
                                             product_description=None):
        """
        Describes Reserved Instance offerings that are available for purchase.

        :type reserved_instances_id: str
        :param reserved_instances_id: Displays Reserved Instances with the specified offering IDs.

        :type instance_type: str
        :param instance_type: Displays Reserved Instances of the specified instance type.

        :type availability_zone: str
        :param availability_zone: Displays Reserved Instances within the specified Availability Zone.

        :type product_description: str
        :param product_description: Displays Reserved Instances with the specified product description.

        :rtype: list
        :return: A list of :class:`boto.ec2.reservedinstance.ReservedInstancesOffering`
        """
        params = {}
        if reserved_instances_id:
            params['ReservedInstancesId'] = reserved_instances_id
        if instance_type:
            params['InstanceType'] = instance_type
        if availability_zone:
            params['AvailabilityZone'] = availability_zone
        if product_description:
            params['ProductDescription'] = product_description

        return self.get_list('DescribeReservedInstancesOfferings',
                             params, [('item', ReservedInstancesOffering)])

    def get_all_reserved_instances(self, reserved_instances_id=None):
        """
        Describes Reserved Instance offerings that are available for purchase.

        :type reserved_instance_ids: list
        :param reserved_instance_ids: A list of the reserved instance ids that will be returned.
                                      If not provided, all reserved instances will be returned.

        :rtype: list
        :return: A list of :class:`boto.ec2.reservedinstance.ReservedInstance`
        """
        params = {}
        if reserved_instances_id:
            self.build_list_params(params, reserved_instances_id, 'ReservedInstancesId')
        return self.get_list('DescribeReservedInstances',
                             params, [('item', ReservedInstance)])

    def purchase_reserved_instance_offering(self, reserved_instances_offering_id,
                                            instance_count=1):
        """
        Purchase a Reserved Instance for use with your account.
        ** CAUTION **
        This request can result in large amounts of money being charged to your
        AWS account.  Use with caution!

        :type reserved_instances_offering_id: string
        :param reserved_instances_offering_id: The offering ID of the Reserved
                                               Instance to purchase

        :type instance_count: int
        :param instance_count: The number of Reserved Instances to purchase.
                               Default value is 1.

        :rtype: :class:`boto.ec2.reservedinstance.ReservedInstance`
        :return: The newly created Reserved Instance
        """
        params = {'ReservedInstancesOfferingId' : reserved_instances_offering_id,
                  'InstanceCount' : instance_count}
        return self.get_object('PurchaseReservedInstancesOffering', params, ReservedInstance)

    #
    # Monitoring
    #

    def monitor_instance(self, instance_id):
        """
        Enable CloudWatch monitoring for the supplied instance.

        :type instance_id: string
        :param instance_id: The instance id

        :rtype: list
        :return: A list of :class:`boto.ec2.instanceinfo.InstanceInfo`
        """
        params = {'InstanceId' : instance_id}
        return self.get_list('MonitorInstances', params, [('item', InstanceInfo)])

    def unmonitor_instance(self, instance_id):
        """
        Disable CloudWatch monitoring for the supplied instance.

        :type instance_id: string
        :param instance_id: The instance id

        :rtype: list
        :return: A list of :class:`boto.ec2.instanceinfo.InstanceInfo`
        """
        params = {'InstanceId' : instance_id}
        return self.get_list('UnmonitorInstances', params, [('item', InstanceInfo)])

