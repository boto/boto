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
Represents a connection to the EC2 service.
"""

import base64
import warnings
from datetime import datetime
from datetime import timedelta
import boto
from boto.connection import AWSQueryConnection
from boto.resultset import ResultSet
from boto.ec2.image import Image, ImageAttribute
from boto.ec2.instance import Reservation, Instance
from boto.ec2.instance import ConsoleOutput, InstanceAttribute
from boto.ec2.keypair import KeyPair
from boto.ec2.address import Address
from boto.ec2.volume import Volume
from boto.ec2.snapshot import Snapshot
from boto.ec2.snapshot import SnapshotAttribute
from boto.ec2.zone import Zone
from boto.ec2.securitygroup import SecurityGroup
from boto.ec2.regioninfo import RegionInfo
from boto.ec2.instanceinfo import InstanceInfo
from boto.ec2.reservedinstance import ReservedInstancesOffering
from boto.ec2.reservedinstance import ReservedInstance
from boto.ec2.spotinstancerequest import SpotInstanceRequest
from boto.ec2.spotpricehistory import SpotPriceHistory
from boto.ec2.spotdatafeedsubscription import SpotDatafeedSubscription
from boto.ec2.bundleinstance import BundleInstanceTask
from boto.ec2.placementgroup import PlacementGroup
from boto.ec2.tag import Tag
from boto.ec2.instancestatus import InstanceStatusSet
from boto.ec2.networkinterface import NetworkInterface
from boto.exception import EC2ResponseError

#boto.set_stream_logger('ec2')

class EC2Connection(AWSQueryConnection):

    APIVersion = boto.config.get('Boto', 'ec2_version', '2011-12-15')
    DefaultRegionName = boto.config.get('Boto', 'ec2_region_name', 'us-east-1')
    DefaultRegionEndpoint = boto.config.get('Boto', 'ec2_region_endpoint',
                                            'ec2.us-east-1.amazonaws.com')
    ResponseError = EC2ResponseError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, host=None, port=None,
                 proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None, path='/',
                 api_version=None, security_token=None):
        """
        Init method to create a new connection to EC2.
        """
        if not region:
            region = RegionInfo(self, self.DefaultRegionName,
                                self.DefaultRegionEndpoint)
        self.region = region
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
                                    proxy_user, proxy_pass,
                                    self.region.endpoint, debug,
                                    https_connection_factory, path,
                                    security_token)
        if api_version:
            self.APIVersion = api_version

    def _required_auth_capability(self):
        return ['ec2']

    def get_params(self):
        """
        Returns a dictionary containing the value of of all of the keyword
        arguments passed when constructing this connection.
        """
        param_names = ['aws_access_key_id', 'aws_secret_access_key',
                       'is_secure', 'port', 'proxy', 'proxy_port',
                       'proxy_user', 'proxy_pass',
                       'debug', 'https_connection_factory']
        params = {}
        for name in param_names:
            params[name] = getattr(self, name)
        return params

    def build_filter_params(self, params, filters):
        i = 1
        for name in filters:
            aws_name = name
            if not aws_name.startswith('tag:'):
                aws_name = name.replace('_', '-')
            params['Filter.%d.Name' % i] = aws_name
            value = filters[name]
            if not isinstance(value, list):
                value = [value]
            j = 1
            for v in value:
                params['Filter.%d.Value.%d' % (i,j)] = v
                j += 1
            i += 1

    # Image methods

    def get_all_images(self, image_ids=None, owners=None,
                       executable_by=None, filters=None):
        """
        Retrieve all the EC2 images available on your account.

        :type image_ids: list
        :param image_ids: A list of strings with the image IDs wanted

        :type owners: list
        :param owners: A list of owner IDs

        :type executable_by: list
        :param executable_by: Returns AMIs for which the specified
                              user ID has explicit launch permissions

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

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
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeImages', params,
                             [('item', Image)], verb='POST')

    def get_all_kernels(self, kernel_ids=None, owners=None):
        """
        Retrieve all the EC2 kernels available on your account.
        Constructs a filter to allow the processing to happen server side.

        :type kernel_ids: list
        :param kernel_ids: A list of strings with the image IDs wanted

        :type owners: list
        :param owners: A list of owner IDs

        :rtype: list
        :return: A list of :class:`boto.ec2.image.Image`
        """
        params = {}
        if kernel_ids:
            self.build_list_params(params, kernel_ids, 'ImageId')
        if owners:
            self.build_list_params(params, owners, 'Owner')
        filter = {'image-type' : 'kernel'}
        self.build_filter_params(params, filter)
        return self.get_list('DescribeImages', params,
                             [('item', Image)], verb='POST')

    def get_all_ramdisks(self, ramdisk_ids=None, owners=None):
        """
        Retrieve all the EC2 ramdisks available on your account.
        Constructs a filter to allow the processing to happen server side.

        :type ramdisk_ids: list
        :param ramdisk_ids: A list of strings with the image IDs wanted

        :type owners: list
        :param owners: A list of owner IDs

        :rtype: list
        :return: A list of :class:`boto.ec2.image.Image`
        """
        params = {}
        if ramdisk_ids:
            self.build_list_params(params, ramdisk_ids, 'ImageId')
        if owners:
            self.build_list_params(params, owners, 'Owner')
        filter = {'image-type' : 'ramdisk'}
        self.build_filter_params(params, filter)
        return self.get_list('DescribeImages', params,
                             [('item', Image)], verb='POST')

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
        :param image_location: Full path to your AMI manifest in
                               Amazon S3 storage.
                               Only used for S3-based AMI's.

        :type architecture: string
        :param architecture: The architecture of the AMI.  Valid choices are:
                             i386 | x86_64

        :type kernel_id: string
        :param kernel_id: The ID of the kernel with which to launch
                          the instances

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
        rs = self.get_object('RegisterImage', params, ResultSet, verb='POST')
        image_id = getattr(rs, 'imageId', None)
        return image_id

    def deregister_image(self, image_id, delete_snapshot=False):
        """
        Unregister an AMI.

        :type image_id: string
        :param image_id: the ID of the Image to unregister

        :type delete_snapshot: bool
        :param delete_snapshot: Set to True if we should delete the
                                snapshot associated with an EBS volume
                                mounted at /dev/sda1

        :rtype: bool
        :return: True if successful
        """
        snapshot_id = None
        if delete_snapshot:
            image = self.get_image(image_id)
            for key in image.block_device_mapping:
                if key == "/dev/sda1":
                    snapshot_id = image.block_device_mapping[key].snapshot_id
                    break

        result = self.get_status('DeregisterImage',
                                 {'ImageId':image_id}, verb='POST')
        if result and snapshot_id:
            return result and self.delete_snapshot(snapshot_id)
        return result

    def create_image(self, instance_id, name,
                     description=None, no_reboot=False):
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
        img = self.get_object('CreateImage', params, Image, verb='POST')
        return img.id

    # ImageAttribute methods

    def get_image_attribute(self, image_id, attribute='launchPermission'):
        """
        Gets an attribute from an image.

        :type image_id: string
        :param image_id: The Amazon image id for which you want info about

        :type attribute: string
        :param attribute: The attribute you need information about.
                          Valid choices are:
                          * launchPermission
                          * productCodes
                          * blockDeviceMapping

        :rtype: :class:`boto.ec2.image.ImageAttribute`
        :return: An ImageAttribute object representing the value of the
                 attribute requested
        """
        params = {'ImageId' : image_id,
                  'Attribute' : attribute}
        return self.get_object('DescribeImageAttribute', params,
                               ImageAttribute, verb='POST')

    def modify_image_attribute(self, image_id, attribute='launchPermission',
                               operation='add', user_ids=None, groups=None,
                               product_codes=None):
        """
        Changes an attribute of an image.

        :type image_id: string
        :param image_id: The image id you wish to change

        :type attribute: string
        :param attribute: The attribute you wish to change

        :type operation: string
        :param operation: Either add or remove (this is required for changing
                          launchPermissions)

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
        return self.get_status('ModifyImageAttribute', params, verb='POST')

    def reset_image_attribute(self, image_id, attribute='launchPermission'):
        """
        Resets an attribute of an AMI to its default value.

        :type image_id: string
        :param image_id: ID of the AMI for which an attribute will be described

        :type attribute: string
        :param attribute: The attribute to reset

        :rtype: bool
        :return: Whether the operation succeeded or not
        """
        params = {'ImageId' : image_id,
                  'Attribute' : attribute}
        return self.get_status('ResetImageAttribute', params, verb='POST')

    # Instance methods

    def get_all_instances(self, instance_ids=None, filters=None):
        """
        Retrieve all the instances associated with your account.

        :type instance_ids: list
        :param instance_ids: A list of strings of instance IDs

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list
        :return: A list of  :class:`boto.ec2.instance.Reservation`
        """
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        if filters:
            if 'group-id' in filters:
                gid = filters.get('group-id')
                if not gid.startswith('sg-') or len(gid) != 11:
                    warnings.warn(
                        "The group-id filter now requires a security group "
                        "identifier (sg-*) instead of a group name. To filter "
                        "by group name use the 'group-name' filter instead.",
                        UserWarning)
            self.build_filter_params(params, filters)
        return self.get_list('DescribeInstances', params,
                             [('item', Reservation)], verb='POST')
    
    def get_all_instance_status(self, instance_ids=None,
                                max_results=None, next_token=None,
                                filters=None):
        """
        Retrieve all the instances in your account scheduled for maintenance.

        :type instance_ids: list
        :param instance_ids: A list of strings of instance IDs

        :type max_results: int
        :param max_results: The maximum number of paginated instance
            items per response.

        :type next_token: str
        :param next_token: A string specifying the next paginated set
            of results to return.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
            the results returned.  Filters are provided
            in the form of a dictionary consisting of
            filter names as the key and filter values
            as the value.  The set of allowable filter
            names/values is dependent on the request
            being performed.  Check the EC2 API guide
            for details.

        :rtype: list
        :return: A list of instances that have maintenance scheduled.
        """
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        if max_results:
            params['MaxResults'] = max_results
        if next_token:
            params['NextToken'] = next_token
        if filters:
            self.build_filter_params(params, filters)
        return self.get_object('DescribeInstanceStatus', params,
                               InstanceStatusSet, verb='POST')

    def run_instances(self, image_id, min_count=1, max_count=1,
                      key_name=None, security_groups=None,
                      user_data=None, addressing_type=None,
                      instance_type='m1.small', placement=None,
                      kernel_id=None, ramdisk_id=None,
                      monitoring_enabled=False, subnet_id=None,
                      block_device_map=None,
                      disable_api_termination=False,
                      instance_initiated_shutdown_behavior=None,
                      private_ip_address=None,
                      placement_group=None, client_token=None,
                      security_group_ids=None):
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
        :param security_groups: The names of the security groups with which to
                                associate instances

        :type user_data: string
        :param user_data: The user data passed to the launched instances

        :type instance_type: string
        :param instance_type: The type of instance to run:

                              * m1.small
                              * m1.large
                              * m1.xlarge
                              * c1.medium
                              * c1.xlarge
                              * m2.xlarge
                              * m2.2xlarge
                              * m2.4xlarge
                              * cc1.4xlarge
                              * t1.micro

        :type placement: string
        :param placement: The availability zone in which to launch the instances

        :type kernel_id: string
        :param kernel_id: The ID of the kernel with which to launch the
                          instances

        :type ramdisk_id: string
        :param ramdisk_id: The ID of the RAM disk with which to launch the
                           instances

        :type monitoring_enabled: bool
        :param monitoring_enabled: Enable CloudWatch monitoring on the instance.

        :type subnet_id: string
        :param subnet_id: The subnet ID within which to launch the instances
                          for VPC.

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
        :param instance_initiated_shutdown_behavior: Specifies whether the
                                                     instance stops or
                                                     terminates on
                                                     instance-initiated
                                                     shutdown.
                                                     Valid values are:

                                                     * stop
                                                     * terminate

        :type placement_group: string
        :param placement_group: If specified, this is the name of the placement
                                group in which the instance(s) will be launched.

        :type client_token: string
        :param client_token: Unique, case-sensitive identifier you provide
                             to ensure idempotency of the request.
                             Maximum 64 ASCII characters

        :rtype: Reservation
        :return: The :class:`boto.ec2.instance.Reservation` associated with
                 the request for machines

        :type security_group_ids: list of strings
        :param security_group_ids: The ID of the VPC security groups with
                                   which to associate instances
        """
        params = {'ImageId':image_id,
                  'MinCount':min_count,
                  'MaxCount': max_count}
        if key_name:
            params['KeyName'] = key_name
        if security_group_ids:
            l = []
            for group in security_group_ids:
                if isinstance(group, SecurityGroup):
                    l.append(group.id)
                else:
                    l.append(group)
            self.build_list_params(params, l, 'SecurityGroupId')
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
        if placement_group:
            params['Placement.GroupName'] = placement_group
        if kernel_id:
            params['KernelId'] = kernel_id
        if ramdisk_id:
            params['RamdiskId'] = ramdisk_id
        if monitoring_enabled:
            params['Monitoring.Enabled'] = 'true'
        if subnet_id:
            params['SubnetId'] = subnet_id
        if private_ip_address:
            params['PrivateIpAddress'] = private_ip_address
        if block_device_map:
            block_device_map.build_list_params(params)
        if disable_api_termination:
            params['DisableApiTermination'] = 'true'
        if instance_initiated_shutdown_behavior:
            val = instance_initiated_shutdown_behavior
            params['InstanceInitiatedShutdownBehavior'] = val
        if client_token:
            params['ClientToken'] = client_token
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
        return self.get_list('TerminateInstances', params,
                             [('item', Instance)], verb='POST')

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
        return self.get_list('StopInstances', params,
                             [('item', Instance)], verb='POST')

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
        return self.get_list('StartInstances', params,
                             [('item', Instance)], verb='POST')

    def get_console_output(self, instance_id):
        """
        Retrieves the console output for the specified instance.

        :type instance_id: string
        :param instance_id: The instance ID of a running instance on the cloud.

        :rtype: :class:`boto.ec2.instance.ConsoleOutput`
        :return: The console output as a ConsoleOutput object
        """
        params = {}
        self.build_list_params(params, [instance_id], 'InstanceId')
        return self.get_object('GetConsoleOutput', params,
                               ConsoleOutput, verb='POST')

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
        rs = self.get_object('ConfirmProductInstance', params,
                             ResultSet, verb='POST')
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

                          * instanceType|kernel|ramdisk|userData|
                          * disableApiTermination|
                          * instanceInitiatedShutdownBehavior|
                          * rootDeviceName|blockDeviceMapping

        :rtype: :class:`boto.ec2.image.InstanceAttribute`
        :return: An InstanceAttribute object representing the value of the
                 attribute requested
        """
        params = {'InstanceId' : instance_id}
        if attribute:
            params['Attribute'] = attribute
        return self.get_object('DescribeInstanceAttribute', params,
                               InstanceAttribute, verb='POST')

    def modify_instance_attribute(self, instance_id, attribute, value):
        """
        Changes an attribute of an instance

        :type instance_id: string
        :param instance_id: The instance id you wish to change

        :type attribute: string
        :param attribute: The attribute you wish to change.

                          * AttributeName - Expected value (default)
                          * instanceType - A valid instance type (m1.small)
                          * kernel - Kernel ID (None)
                          * ramdisk - Ramdisk ID (None)
                          * userData - Base64 encoded String (None)
                          * disableApiTermination - Boolean (true)
                          * instanceInitiatedShutdownBehavior - stop|terminate
                          * rootDeviceName - device name (None)

        :type value: string
        :param value: The new value for the attribute

        :rtype: bool
        :return: Whether the operation succeeded or not
        """
        # Allow a bool to be passed in for value of disableApiTermination
        if attribute == 'disableApiTermination':
            if isinstance(value, bool):
                if value:
                    value = 'true'
                else:
                    value = 'false'
        params = {'InstanceId' : instance_id,
                  'Attribute' : attribute,
                  'Value' : value}
        return self.get_status('ModifyInstanceAttribute', params, verb='POST')

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
        return self.get_status('ResetInstanceAttribute', params, verb='POST')

    # Spot Instances

    def get_all_spot_instance_requests(self, request_ids=None,
                                       filters=None):
        """
        Retrieve all the spot instances requests associated with your account.

        :type request_ids: list
        :param request_ids: A list of strings of spot instance request IDs

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list
        :return: A list of
                 :class:`boto.ec2.spotinstancerequest.SpotInstanceRequest`
        """
        params = {}
        if request_ids:
            self.build_list_params(params, request_ids, 'SpotInstanceRequestId')
        if filters:
            if 'launch.group-id' in filters:
                lgid = filters.get('launch.group-id')
                if not lgid.startswith('sg-') or len(lgid) != 11:
                    warnings.warn(
                        "The 'launch.group-id' filter now requires a security "
                        "group id (sg-*) and no longer supports filtering by "
                        "group name. Please update your filters accordingly.",
                        UserWarning)
            self.build_filter_params(params, filters)
        return self.get_list('DescribeSpotInstanceRequests', params,
                             [('item', SpotInstanceRequest)], verb='POST')

    def get_spot_price_history(self, start_time=None, end_time=None,
                               instance_type=None, product_description=None,
                               availability_zone=None):
        """
        Retrieve the recent history of spot instances pricing.

        :type start_time: str
        :param start_time: An indication of how far back to provide price
                           changes for. An ISO8601 DateTime string.

        :type end_time: str
        :param end_time: An indication of how far forward to provide price
                         changes for.  An ISO8601 DateTime string.

        :type instance_type: str
        :param instance_type: Filter responses to a particular instance type.

        :type product_description: str
        :param product_description: Filter responses to a particular platform.
                                    Valid values are currently: "Linux/UNIX",
                                    "SUSE Linux", and "Windows"

        :type availability_zone: str
        :param availability_zone: The availability zone for which prices
                                  should be returned

        :rtype: list
        :return: A list tuples containing price and timestamp.
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
        if availability_zone:
            params['AvailabilityZone'] = availability_zone
        return self.get_list('DescribeSpotPriceHistory', params,
                             [('item', SpotPriceHistory)], verb='POST')

    def request_spot_instances(self, price, image_id, count=1, type='one-time',
                               valid_from=None, valid_until=None,
                               launch_group=None, availability_zone_group=None,
                               key_name=None, security_groups=None,
                               user_data=None, addressing_type=None,
                               instance_type='m1.small', placement=None,
                               kernel_id=None, ramdisk_id=None,
                               monitoring_enabled=False, subnet_id=None,
                               placement_group=None,
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
        :param availability_zone_group: If supplied, all requests will be
                                        fulfilled within a single
                                        availability zone.

        :type key_name: string
        :param key_name: The name of the key pair with which to launch instances

        :type security_groups: list of strings
        :param security_groups: The names of the security groups with which to
                                associate instances

        :type user_data: string
        :param user_data: The user data passed to the launched instances

        :type instance_type: string
        :param instance_type: The type of instance to run:

                              * m1.small
                              * m1.large
                              * m1.xlarge
                              * c1.medium
                              * c1.xlarge
                              * m2.xlarge
                              * m2.2xlarge
                              * m2.4xlarge
                              * cc1.4xlarge
                              * t1.micro

        :type placement: string
        :param placement: The availability zone in which to launch the instances

        :type kernel_id: string
        :param kernel_id: The ID of the kernel with which to launch the
                          instances

        :type ramdisk_id: string
        :param ramdisk_id: The ID of the RAM disk with which to launch the
                           instances

        :type monitoring_enabled: bool
        :param monitoring_enabled: Enable CloudWatch monitoring on the instance.

        :type subnet_id: string
        :param subnet_id: The subnet ID within which to launch the instances
                          for VPC.
        
        :type placement_group: string
        :param placement_group: If specified, this is the name of the placement
                                group in which the instance(s) will be launched.

        :type block_device_map: :class:`boto.ec2.blockdevicemapping.BlockDeviceMapping`
        :param block_device_map: A BlockDeviceMapping data structure
                                 describing the EBS volumes associated
                                 with the Image.

        :rtype: Reservation
        :return: The :class:`boto.ec2.spotinstancerequest.SpotInstanceRequest`
                 associated with the request for machines
        """
        params = {'LaunchSpecification.ImageId':image_id,
                  'Type' : type,
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
        if placement_group:
            params['LaunchSpecification.Placement.GroupName'] = placement_group
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
        return self.get_list('CancelSpotInstanceRequests', params,
                             [('item', Instance)], verb='POST')

    def get_spot_datafeed_subscription(self):
        """
        Return the current spot instance data feed subscription
        associated with this account, if any.

        :rtype: :class:`boto.ec2.spotdatafeedsubscription.SpotDatafeedSubscription`
        :return: The datafeed subscription object or None
        """
        return self.get_object('DescribeSpotDatafeedSubscription',
                               None, SpotDatafeedSubscription, verb='POST')

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
                               params, SpotDatafeedSubscription, verb='POST')

    def delete_spot_datafeed_subscription(self):
        """
        Delete the current spot instance data feed subscription
        associated with this account

        :rtype: bool
        :return: True if successful
        """
        return self.get_status('DeleteSpotDatafeedSubscription',
                               None, verb='POST')

    # Zone methods

    def get_all_zones(self, zones=None, filters=None):
        """
        Get all Availability Zones associated with the current region.

        :type zones: list
        :param zones: Optional list of zones.  If this list is present,
                      only the Zones associated with these zone names
                      will be returned.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list of :class:`boto.ec2.zone.Zone`
        :return: The requested Zone objects
        """
        params = {}
        if zones:
            self.build_list_params(params, zones, 'ZoneName')
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeAvailabilityZones', params,
                             [('item', Zone)], verb='POST')

    # Address methods

    def get_all_addresses(self, addresses=None, filters=None, allocation_ids=None):
        """
        Get all EIP's associated with the current credentials.

        :type addresses: list
        :param addresses: Optional list of addresses.  If this list is present,
                           only the Addresses associated with these addresses
                           will be returned.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :type allocation_ids: list
        :param allocation_ids: Optional list of allocation IDs.  If this list is
                           present, only the Addresses associated with the given
                           allocation IDs will be returned.

        :rtype: list of :class:`boto.ec2.address.Address`
        :return: The requested Address objects
        """
        params = {}
        if addresses:
            self.build_list_params(params, addresses, 'PublicIp')
        if allocation_ids:
            self.build_list_params(params, allocation_ids, 'AllocationId')
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeAddresses', params, [('item', Address)], verb='POST')

    def allocate_address(self, domain=None):
        """
        Allocate a new Elastic IP address and associate it with your account.

        :rtype: :class:`boto.ec2.address.Address`
        :return: The newly allocated Address
        """
        params = {}

        if domain is not None:
            params['Domain'] = domain

        return self.get_object('AllocateAddress', params, Address, verb='POST')

    def associate_address(self, instance_id, public_ip=None, allocation_id=None):
        """
        Associate an Elastic IP address with a currently running instance.
        This requires one of ``public_ip`` or ``allocation_id`` depending
        on if you're associating a VPC address or a plain EC2 address.

        :type instance_id: string
        :param instance_id: The ID of the instance

        :type public_ip: string
        :param public_ip: The public IP address for EC2 based allocations.

        :type allocation_id: string
        :param allocation_id: The allocation ID for a VPC-based elastic IP.

        :rtype: bool
        :return: True if successful
        """
        params = { 'InstanceId' : instance_id }

        if public_ip is not None:
            params['PublicIp'] = public_ip
        elif allocation_id is not None:
            params['AllocationId'] = allocation_id

        return self.get_status('AssociateAddress', params, verb='POST')

    def disassociate_address(self, public_ip=None, association_id=None):
        """
        Disassociate an Elastic IP address from a currently running instance.

        :type public_ip: string
        :param public_ip: The public IP address for EC2 elastic IPs.

        :type association_id: string
        :param association_id: The association ID for a VPC based elastic ip.

        :rtype: bool
        :return: True if successful
        """
        params = {}

        if public_ip is not None:
            params['PublicIp'] = public_ip
        elif association_id is not None:
            params['AssociationId'] = association_id

        return self.get_status('DisassociateAddress', params, verb='POST')

    def release_address(self, public_ip=None, allocation_id=None):
        """
        Free up an Elastic IP address.

        :type public_ip: string
        :param public_ip: The public IP address for EC2 elastic IPs.

        :type allocation_id: string
        :param allocation_id: The ID for VPC elastic IPs.

        :rtype: bool
        :return: True if successful
        """
        params = {}

        if public_ip is not None:
            params['PublicIp'] = public_ip
        elif allocation_id is not None:
            params['AllocationId'] = allocation_id

        return self.get_status('ReleaseAddress', params, verb='POST')

    # Volume methods

    def get_all_volumes(self, volume_ids=None, filters=None):
        """
        Get all Volumes associated with the current credentials.

        :type volume_ids: list
        :param volume_ids: Optional list of volume ids.  If this list
                           is present, only the volumes associated with
                           these volume ids will be returned.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list of :class:`boto.ec2.volume.Volume`
        :return: The requested Volume objects
        """
        params = {}
        if volume_ids:
            self.build_list_params(params, volume_ids, 'VolumeId')
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeVolumes', params,
                             [('item', Volume)], verb='POST')

    def create_volume(self, size, zone, snapshot=None):
        """
        Create a new EBS Volume.

        :type size: int
        :param size: The size of the new volume, in GiB

        :type zone: string or :class:`boto.ec2.zone.Zone`
        :param zone: The availability zone in which the Volume will be created.

        :type snapshot: string or :class:`boto.ec2.snapshot.Snapshot`
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
        return self.get_object('CreateVolume', params, Volume, verb='POST')

    def delete_volume(self, volume_id):
        """
        Delete an EBS volume.

        :type volume_id: str
        :param volume_id: The ID of the volume to be delete.

        :rtype: bool
        :return: True if successful
        """
        params = {'VolumeId': volume_id}
        return self.get_status('DeleteVolume', params, verb='POST')

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
        return self.get_status('AttachVolume', params, verb='POST')

    def detach_volume(self, volume_id, instance_id=None,
                      device=None, force=False):
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
        return self.get_status('DetachVolume', params, verb='POST')

    # Snapshot methods

    def get_all_snapshots(self, snapshot_ids=None,
                          owner=None, restorable_by=None,
                          filters=None):
        """
        Get all EBS Snapshots associated with the current credentials.

        :type snapshot_ids: list
        :param snapshot_ids: Optional list of snapshot ids.  If this list is
                             present, only the Snapshots associated with
                             these snapshot ids will be returned.

        :type owner: str
        :param owner: If present, only the snapshots owned by the specified user
                      will be returned.  Valid values are:

                      * self
                      * amazon
                      * AWS Account ID

        :type restorable_by: str
        :param restorable_by: If present, only the snapshots that are restorable
                              by the specified account id will be returned.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list of :class:`boto.ec2.snapshot.Snapshot`
        :return: The requested Snapshot objects
        """
        params = {}
        if snapshot_ids:
            self.build_list_params(params, snapshot_ids, 'SnapshotId')
        if owner:
            params['Owner'] = owner
        if restorable_by:
            params['RestorableBy'] = restorable_by
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeSnapshots', params,
                             [('item', Snapshot)], verb='POST')

    def create_snapshot(self, volume_id, description=None):
        """
        Create a snapshot of an existing EBS Volume.

        :type volume_id: str
        :param volume_id: The ID of the volume to be snapshot'ed

        :type description: str
        :param description: A description of the snapshot.
                            Limited to 255 characters.

        :rtype: bool
        :return: True if successful
        """
        params = {'VolumeId' : volume_id}
        if description:
            params['Description'] = description[0:255]
        snapshot = self.get_object('CreateSnapshot', params,
                                   Snapshot, verb='POST')
        volume = self.get_all_volumes([volume_id])[0]
        volume_name = volume.tags.get('Name')
        if volume_name:
            snapshot.add_tag('Name', volume_name)
        return snapshot

    def delete_snapshot(self, snapshot_id):
        params = {'SnapshotId': snapshot_id}
        return self.get_status('DeleteSnapshot', params, verb='POST')

    def trim_snapshots(self, hourly_backups = 8, daily_backups = 7,
                       weekly_backups = 4):
        """
        Trim excess snapshots, based on when they were taken. More current
        snapshots are retained, with the number retained decreasing as you
        move back in time.

        If ebs volumes have a 'Name' tag with a value, their snapshots
        will be assigned the same tag when they are created. The values
        of the 'Name' tags for snapshots are used by this function to
        group snapshots taken from the same volume (or from a series
        of like-named volumes over time) for trimming.

        For every group of like-named snapshots, this function retains
        the newest and oldest snapshots, as well as, by default,  the
        first snapshots taken in each of the last eight hours, the first
        snapshots taken in each of the last seven days, the first snapshots
        taken in the last 4 weeks (counting Midnight Sunday morning as
        the start of the week), and the first snapshot from the first
        Sunday of each month forever.

        :type hourly_backups: int
        :param hourly_backups: How many recent hourly backups should be saved.

        :type daily_backups: int
        :param daily_backups: How many recent daily backups should be saved.

        :type weekly_backups: int
        :param weekly_backups: How many recent weekly backups should be saved.
        """

        # This function first builds up an ordered list of target times
        # that snapshots should be saved for (last 8 hours, last 7 days, etc.).
        # Then a map of snapshots is constructed, with the keys being
        # the snapshot / volume names and the values being arrays of
        # chronologically sorted snapshots.
        # Finally, for each array in the map, we go through the snapshot
        # array and the target time array in an interleaved fashion,
        # deleting snapshots whose start_times don't immediately follow a
        # target time (we delete a snapshot if there's another snapshot
        # that was made closer to the preceding target time).

        now = datetime.utcnow()
        last_hour = datetime(now.year, now.month, now.day, now.hour)
        last_midnight = datetime(now.year, now.month, now.day)
        last_sunday = datetime(now.year, now.month, now.day) - timedelta(days = (now.weekday() + 1) % 7)
        start_of_month = datetime(now.year, now.month, 1)

        target_backup_times = []

        # there are no snapshots older than 1/1/2007
        oldest_snapshot_date = datetime(2007, 1, 1)

        for hour in range(0, hourly_backups):
            target_backup_times.append(last_hour - timedelta(hours = hour))

        for day in range(0, daily_backups):
            target_backup_times.append(last_midnight - timedelta(days = day))

        for week in range(0, weekly_backups):
            target_backup_times.append(last_sunday - timedelta(weeks = week))

        one_day = timedelta(days = 1)
        while start_of_month > oldest_snapshot_date:
            # append the start of the month to the list of
            # snapshot dates to save:
            target_backup_times.append(start_of_month)
            # there's no timedelta setting for one month, so instead:
            # decrement the day by one, so we go to the final day of
            # the previous month...
            start_of_month -= one_day
            # ... and then go to the first day of that previous month:
            start_of_month = datetime(start_of_month.year,
                                      start_of_month.month, 1)

        temp = []

        for t in target_backup_times:
            if temp.__contains__(t) == False:
                temp.append(t)

        target_backup_times = temp
        # make the oldeest dates first, and make sure the month start
        # and last four week's start are in the proper order
        target_backup_times.sort()

        # get all the snapshots, sort them by date and time, and
        # organize them into one array for each volume:
        all_snapshots = self.get_all_snapshots(owner = 'self')
        all_snapshots.sort(cmp = lambda x, y: cmp(x.start_time, y.start_time))
        snaps_for_each_volume = {}
        for snap in all_snapshots:
            # the snapshot name and the volume name are the same.
            # The snapshot name is set from the volume
            # name at the time the snapshot is taken
            volume_name = snap.tags.get('Name')
            if volume_name:
                # only examine snapshots that have a volume name
                snaps_for_volume = snaps_for_each_volume.get(volume_name)
                if not snaps_for_volume:
                    snaps_for_volume = []
                    snaps_for_each_volume[volume_name] = snaps_for_volume
                snaps_for_volume.append(snap)

        # Do a running comparison of snapshot dates to desired time
        #periods, keeping the oldest snapshot in each
        # time period and deleting the rest:
        for volume_name in snaps_for_each_volume:
            snaps = snaps_for_each_volume[volume_name]
            snaps = snaps[:-1] # never delete the newest snapshot
            time_period_number = 0
            snap_found_for_this_time_period = False
            for snap in snaps:
                check_this_snap = True
                while check_this_snap and time_period_number < target_backup_times.__len__():
                    snap_date = datetime.strptime(snap.start_time,
                                                  '%Y-%m-%dT%H:%M:%S.000Z')
                    if snap_date < target_backup_times[time_period_number]:
                        # the snap date is before the cutoff date.
                        # Figure out if it's the first snap in this
                        # date range and act accordingly (since both
                        #date the date ranges and the snapshots
                        # are sorted chronologically, we know this
                        #snapshot isn't in an earlier date range):
                        if snap_found_for_this_time_period == True:
                            if not snap.tags.get('preserve_snapshot'):
                                # as long as the snapshot wasn't marked
                                # with the 'preserve_snapshot' tag, delete it:
                                try:
                                    self.delete_snapshot(snap.id)
                                    boto.log.info('Trimmed snapshot %s (%s)' % (snap.tags['Name'], snap.start_time))
                                except EC2ResponseError:
                                    boto.log.error('Attempt to trim snapshot %s (%s) failed. Possible result of a race condition with trimming on another server?' % (snap.tags['Name'], snap.start_time))
                            # go on and look at the next snapshot,
                            #leaving the time period alone
                        else:
                            # this was the first snapshot found for this
                            #time period. Leave it alone and look at the
                            # next snapshot:
                            snap_found_for_this_time_period = True
                        check_this_snap = False
                    else:
                        # the snap is after the cutoff date. Check it
                        # against the next cutoff date
                        time_period_number += 1
                        snap_found_for_this_time_period = False


    def get_snapshot_attribute(self, snapshot_id,
                               attribute='createVolumePermission'):
        """
        Get information about an attribute of a snapshot.  Only one attribute
        can be specified per call.

        :type snapshot_id: str
        :param snapshot_id: The ID of the snapshot.

        :type attribute: str
        :param attribute: The requested attribute.  Valid values are:

                          * createVolumePermission

        :rtype: list of :class:`boto.ec2.snapshotattribute.SnapshotAttribute`
        :return: The requested Snapshot attribute
        """
        params = {'Attribute' : attribute}
        if snapshot_id:
            params['SnapshotId'] = snapshot_id
        return self.get_object('DescribeSnapshotAttribute', params,
                               SnapshotAttribute, verb='POST')

    def modify_snapshot_attribute(self, snapshot_id,
                                  attribute='createVolumePermission',
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
        return self.get_status('ModifySnapshotAttribute', params, verb='POST')

    def reset_snapshot_attribute(self, snapshot_id,
                                 attribute='createVolumePermission'):
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
        return self.get_status('ResetSnapshotAttribute', params, verb='POST')

    # Keypair methods

    def get_all_key_pairs(self, keynames=None, filters=None):
        """
        Get all key pairs associated with your account.

        :type keynames: list
        :param keynames: A list of the names of keypairs to retrieve.
                         If not provided, all key pairs will be returned.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list
        :return: A list of :class:`boto.ec2.keypair.KeyPair`
        """
        params = {}
        if keynames:
            self.build_list_params(params, keynames, 'KeyName')
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeKeyPairs', params,
                             [('item', KeyPair)], verb='POST')

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
        except self.ResponseError, e:
            if e.code == 'InvalidKeyPair.NotFound':
                return None
            else:
                raise

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
        return self.get_object('CreateKeyPair', params, KeyPair, verb='POST')

    def delete_key_pair(self, key_name):
        """
        Delete a key pair from your account.

        :type key_name: string
        :param key_name: The name of the keypair to delete
        """
        params = {'KeyName':key_name}
        return self.get_status('DeleteKeyPair', params, verb='POST')

    def import_key_pair(self, key_name, public_key_material):
        """
        mports the public key from an RSA key pair that you created
        with a third-party tool.

        Supported formats:

        * OpenSSH public key format (e.g., the format
          in ~/.ssh/authorized_keys)

        * Base64 encoded DER format

        * SSH public key file format as specified in RFC4716

        DSA keys are not supported. Make sure your key generator is
        set up to create RSA keys.

        Supported lengths: 1024, 2048, and 4096.

        :type key_name: string
        :param key_name: The name of the new keypair

        :type public_key_material: string
        :param public_key_material: The public key. You must base64 encode
                                    the public key material before sending
                                    it to AWS.

        :rtype: :class:`boto.ec2.keypair.KeyPair`
        :return: The newly created :class:`boto.ec2.keypair.KeyPair`.
                 The material attribute of the new KeyPair object
                 will contain the the unencrypted PEM encoded RSA private key.
        """
        public_key_material = base64.b64encode(public_key_material)
        params = {'KeyName' : key_name,
                  'PublicKeyMaterial' : public_key_material}
        return self.get_object('ImportKeyPair', params, KeyPair, verb='POST')

    # SecurityGroup methods

    def get_all_security_groups(self, groupnames=None, group_ids=None,
                                filters=None):
        """
        Get all security groups associated with your account in a region.

        :type groupnames: list
        :param groupnames: A list of the names of security groups to retrieve.
                           If not provided, all security groups will be
                           returned.

        :type group_ids: list
        :param group_ids: A list of IDs of security groups to retrieve for
                          security groups within a VPC.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list
        :return: A list of :class:`boto.ec2.securitygroup.SecurityGroup`
        """
        params = {}
        if groupnames is not None:
            self.build_list_params(params, groupnames, 'GroupName')
        if group_ids is not None:
            self.build_list_params(params, group_ids, 'GroupId')
        if filters is not None:
            self.build_filter_params(params, filters)

        return self.get_list('DescribeSecurityGroups', params,
                             [('item', SecurityGroup)], verb='POST')

    def create_security_group(self, name, description, vpc_id=None):
        """
        Create a new security group for your account.
        This will create the security group within the region you
        are currently connected to.

        :type name: string
        :param name: The name of the new security group

        :type description: string
        :param description: The description of the new security group

        :type vpc_id: string
        :param vpc_id: The ID of the VPC to create the security group in,
                       if any.

        :rtype: :class:`boto.ec2.securitygroup.SecurityGroup`
        :return: The newly created :class:`boto.ec2.keypair.KeyPair`.
        """
        params = {
            'GroupName': name,
            'GroupDescription': description
        }

        if vpc_id is not None:
            params['VpcId'] = vpc_id

        group = self.get_object('CreateSecurityGroup', params,
                                SecurityGroup, verb='POST')
        group.name = name
        group.description = description
        return group

    def delete_security_group(self, name=None, group_id=None):
        """
        Delete a security group from your account.

        :type name: string
        :param name: The name of the security group to delete.

        :type group_id: string
        :param group_id: The ID of the security group to delete within
          a VPC.

        :rtype: bool
        :return: True if successful.
        """
        params = {}

        if name is not None:
            params['GroupName'] = name
        elif group_id is not None:
            params['GroupId'] = group_id

        return self.get_status('DeleteSecurityGroup', params, verb='POST')

    def authorize_security_group_deprecated(self, group_name,
                                            src_security_group_name=None,
                                            src_security_group_owner_id=None,
                                            ip_protocol=None,
                                            from_port=None, to_port=None,
                                            cidr_ip=None):
        """
        NOTE: This method uses the old-style request parameters
              that did not allow a port to be specified when
              authorizing a group.

        :type group_name: string
        :param group_name: The name of the security group you are adding
                           the rule to.

        :type src_security_group_name: string
        :param src_security_group_name: The name of the security group you are
                                        granting access to.

        :type src_security_group_owner_id: string
        :param src_security_group_owner_id: The ID of the owner of the security
                                            group you are granting access to.

        :type ip_protocol: string
        :param ip_protocol: Either tcp | udp | icmp

        :type from_port: int
        :param from_port: The beginning port number you are enabling

        :type to_port: int
        :param to_port: The ending port number you are enabling

        :type to_port: string
        :param to_port: The CIDR block you are providing access to.
                        See http://goo.gl/Yj5QC

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
        return self.get_status('AuthorizeSecurityGroupIngress', params)

    def authorize_security_group(self, group_name=None,
                                 src_security_group_name=None,
                                 src_security_group_owner_id=None,
                                 ip_protocol=None, from_port=None, to_port=None,
                                 cidr_ip=None, group_id=None,
                                 src_security_group_group_id=None):
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
        :param src_security_group_owner_id: The ID of the owner of the security
                                            group you are granting access to.

        :type ip_protocol: string
        :param ip_protocol: Either tcp | udp | icmp

        :type from_port: int
        :param from_port: The beginning port number you are enabling

        :type to_port: int
        :param to_port: The ending port number you are enabling

        :type cidr_ip: string
        :param cidr_ip: The CIDR block you are providing access to.
                        See http://goo.gl/Yj5QC

        :type group_id: string
        :param group_id: ID of the EC2 or VPC security group to modify.
                         This is required for VPC security groups and
                         can be used instead of group_name for EC2
                         security groups.

        :type group_id: string
        :param group_id: ID of the EC2 or VPC source security group.
                         This is required for VPC security groups and
                         can be used instead of group_name for EC2
                         security groups.

        :rtype: bool
        :return: True if successful.
        """
        if src_security_group_name:
            if from_port is None and to_port is None and ip_protocol is None:
                return self.authorize_security_group_deprecated(
                    group_name, src_security_group_name,
                    src_security_group_owner_id)

        params = {}

        if group_name:
            params['GroupName'] = group_name
        if group_id:
            params['GroupId'] = group_id
        if src_security_group_name:
            param_name = 'IpPermissions.1.Groups.1.GroupName'
            params[param_name] = src_security_group_name
        if src_security_group_owner_id:
            param_name = 'IpPermissions.1.Groups.1.UserId'
            params[param_name] = src_security_group_owner_id
        if src_security_group_group_id:
            param_name = 'IpPermissions.1.Groups.1.GroupId'
            params[param_name] = src_security_group_group_id
        if ip_protocol:
            params['IpPermissions.1.IpProtocol'] = ip_protocol
        if from_port is not None:
            params['IpPermissions.1.FromPort'] = from_port
        if to_port is not None:
            params['IpPermissions.1.ToPort'] = to_port
        if cidr_ip:
            params['IpPermissions.1.IpRanges.1.CidrIp'] = cidr_ip

        return self.get_status('AuthorizeSecurityGroupIngress',
                               params, verb='POST')

    def authorize_security_group_egress(self,
                                        group_id,
                                        ip_protocol,
                                        from_port=None,
                                        to_port=None,
                                        src_group_id=None,
                                        cidr_ip=None):
        """
        The action adds one or more egress rules to a VPC security
        group. Specifically, this action permits instances in a
        security group to send traffic to one or more destination
        CIDR IP address ranges, or to one or more destination
        security groups in the same VPC.
        """
        params = {
            'GroupId': group_id,
            'IpPermissions.1.IpProtocol': ip_protocol
        }

        if from_port is not None:
            params['IpPermissions.1.FromPort'] = from_port
        if to_port is not None:
            params['IpPermissions.1.ToPort'] = to_port
        if src_group_id is not None:
            params['IpPermissions.1.Groups.1.GroupId'] = src_group_id
        if cidr_ip is not None:
            params['IpPermissions.1.IpRanges.1.CidrIp'] = cidr_ip

        return self.get_status('AuthorizeSecurityGroupEgress',
                               params, verb='POST')

    def revoke_security_group_deprecated(self, group_name,
                                         src_security_group_name=None,
                                         src_security_group_owner_id=None,
                                         ip_protocol=None,
                                         from_port=None, to_port=None,
                                         cidr_ip=None):
        """
        NOTE: This method uses the old-style request parameters
              that did not allow a port to be specified when
              authorizing a group.

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
        :param src_security_group_owner_id: The ID of the owner of the security
                                            group you are revoking access to.

        :type ip_protocol: string
        :param ip_protocol: Either tcp | udp | icmp

        :type from_port: int
        :param from_port: The beginning port number you are disabling

        :type to_port: int
        :param to_port: The ending port number you are disabling

        :type to_port: string
        :param to_port: The CIDR block you are revoking access to.
                        http://goo.gl/Yj5QC

        :type group_id: string
        :param group_id: ID of the EC2 or VPC security group to modify.
                         This is required for VPC security groups and
                         can be used instead of group_name for EC2
                         security groups.

        :type group_id: string
        :param group_id: ID of the EC2 or VPC source security group.
                         This is required for VPC security groups and
                         can be used instead of group_name for EC2
                         security groups.

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

    def revoke_security_group(self, group_name=None, src_security_group_name=None,
                              src_security_group_owner_id=None,
                              ip_protocol=None, from_port=None, to_port=None,
                              cidr_ip=None, group_id=None,
                              src_security_group_group_id=None):
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
        :param src_security_group_owner_id: The ID of the owner of the security
                                            group you are revoking access to.

        :type ip_protocol: string
        :param ip_protocol: Either tcp | udp | icmp

        :type from_port: int
        :param from_port: The beginning port number you are disabling

        :type to_port: int
        :param to_port: The ending port number you are disabling

        :type cidr_ip: string
        :param cidr_ip: The CIDR block you are revoking access to.
                        See http://goo.gl/Yj5QC

        :rtype: bool
        :return: True if successful.
        """
        if src_security_group_name:
            if from_port is None and to_port is None and ip_protocol is None:
                return self.revoke_security_group_deprecated(
                    group_name, src_security_group_name,
                    src_security_group_owner_id)
        params = {}
        if group_name is not None:
            params['GroupName'] = group_name
        if group_id is not None:
            params['GroupId'] = group_id
        if src_security_group_name:
            param_name = 'IpPermissions.1.Groups.1.GroupName'
            params[param_name] = src_security_group_name
        if src_security_group_group_id:
            param_name = 'IpPermissions.1.Groups.1.GroupId'
            params[param_name] = src_security_group_group_id
        if src_security_group_owner_id:
            param_name = 'IpPermissions.1.Groups.1.UserId'
            params[param_name] = src_security_group_owner_id
        if ip_protocol:
            params['IpPermissions.1.IpProtocol'] = ip_protocol
        if from_port is not None:
            params['IpPermissions.1.FromPort'] = from_port
        if to_port is not None:
            params['IpPermissions.1.ToPort'] = to_port
        if cidr_ip:
            params['IpPermissions.1.IpRanges.1.CidrIp'] = cidr_ip
        return self.get_status('RevokeSecurityGroupIngress',
                               params, verb='POST')

    def revoke_security_group_egress(self,
                                     group_id,
                                     ip_protocol,
                                     from_port=None,
                                     to_port=None,
                                     src_group_id=None,
                                     cidr_ip=None):
        """
        Remove an existing egress rule from an existing VPC security group.
        You need to pass in an ip_protocol, from_port and to_port range only
        if the protocol you are using is port-based. You also need to pass in either
        a src_group_id or cidr_ip. 

        :type group_name: string
        :param group_id:  The name of the security group you are removing
                           the rule from.

        :type ip_protocol: string
        :param ip_protocol: Either tcp | udp | icmp | -1

        :type from_port: int
        :param from_port: The beginning port number you are disabling

        :type to_port: int
        :param to_port: The ending port number you are disabling

        :type src_group_id: src_group_id
        :param src_group_id: The source security group you are revoking access to.

        :type cidr_ip: string
        :param cidr_ip: The CIDR block you are revoking access to.
                        See http://goo.gl/Yj5QC

        :rtype: bool
        :return: True if successful.
        """
       
        params = {}
        if group_id:
            params['GroupId'] = group_id
        if ip_protocol:
            params['IpPermissions.1.IpProtocol'] = ip_protocol
        if from_port is not None:
            params['IpPermissions.1.FromPort'] = from_port
        if to_port is not None:
            params['IpPermissions.1.ToPort'] = to_port
        if src_group_id is not None:
            params['IpPermissions.1.Groups.1.GroupId'] = src_group_id
        if cidr_ip:
            params['IpPermissions.1.IpRanges.1.CidrIp'] = cidr_ip
        return self.get_status('RevokeSecurityGroupEgress',
                               params, verb='POST')

    #
    # Regions
    #

    def get_all_regions(self, region_names=None, filters=None):
        """
        Get all available regions for the EC2 service.

        :type region_names: list of str
        :param region_names: Names of regions to limit output

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list
        :return: A list of :class:`boto.ec2.regioninfo.RegionInfo`
        """
        params = {}
        if region_names:
            self.build_list_params(params, region_names, 'RegionName')
        if filters:
            self.build_filter_params(params, filters)
        regions =  self.get_list('DescribeRegions', params,
                                 [('item', RegionInfo)], verb='POST')
        for region in regions:
            region.connection_cls = EC2Connection
        return regions

    #
    # Reservation methods
    #

    def get_all_reserved_instances_offerings(self, reserved_instances_id=None,
                                             instance_type=None,
                                             availability_zone=None,
                                             product_description=None,
                                             filters=None):
        """
        Describes Reserved Instance offerings that are available for purchase.

        :type reserved_instances_id: str
        :param reserved_instances_id: Displays Reserved Instances with the
                                      specified offering IDs.

        :type instance_type: str
        :param instance_type: Displays Reserved Instances of the specified
                              instance type.

        :type availability_zone: str
        :param availability_zone: Displays Reserved Instances within the
                                  specified Availability Zone.

        :type product_description: str
        :param product_description: Displays Reserved Instances with the
                                    specified product description.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

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
        if filters:
            self.build_filter_params(params, filters)

        return self.get_list('DescribeReservedInstancesOfferings',
                             params, [('item', ReservedInstancesOffering)],
                             verb='POST')

    def get_all_reserved_instances(self, reserved_instances_id=None,
                                   filters=None):
        """
        Describes Reserved Instance offerings that are available for purchase.

        :type reserved_instance_ids: list
        :param reserved_instance_ids: A list of the reserved instance ids that
                                      will be returned. If not provided, all
                                      reserved instances will be returned.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list
        :return: A list of :class:`boto.ec2.reservedinstance.ReservedInstance`
        """
        params = {}
        if reserved_instances_id:
            self.build_list_params(params, reserved_instances_id,
                                   'ReservedInstancesId')
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeReservedInstances',
                             params, [('item', ReservedInstance)], verb='POST')

    def purchase_reserved_instance_offering(self,
                                            reserved_instances_offering_id,
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
        params = {
            'ReservedInstancesOfferingId' : reserved_instances_offering_id,
            'InstanceCount' : instance_count}
        return self.get_object('PurchaseReservedInstancesOffering', params,
                               ReservedInstance, verb='POST')

    #
    # Monitoring
    #

    def monitor_instances(self, instance_ids):
        """
        Enable CloudWatch monitoring for the supplied instances.

        :type instance_id: list of strings
        :param instance_id: The instance ids

        :rtype: list
        :return: A list of :class:`boto.ec2.instanceinfo.InstanceInfo`
        """
        params = {}
        self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_list('MonitorInstances', params,
                             [('item', InstanceInfo)], verb='POST')

    def monitor_instance(self, instance_id):
        """
        Deprecated Version, maintained for backward compatibility.
        Enable CloudWatch monitoring for the supplied instance.

        :type instance_id: string
        :param instance_id: The instance id

        :rtype: list
        :return: A list of :class:`boto.ec2.instanceinfo.InstanceInfo`
        """
        return self.monitor_instances([instance_id])

    def unmonitor_instances(self, instance_ids):
        """
        Disable CloudWatch monitoring for the supplied instance.

        :type instance_id: list of string
        :param instance_id: The instance id

        :rtype: list
        :return: A list of :class:`boto.ec2.instanceinfo.InstanceInfo`
        """
        params = {}
        self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_list('UnmonitorInstances', params,
                             [('item', InstanceInfo)], verb='POST')

    def unmonitor_instance(self, instance_id):
        """
        Deprecated Version, maintained for backward compatibility.
        Disable CloudWatch monitoring for the supplied instance.

        :type instance_id: string
        :param instance_id: The instance id

        :rtype: list
        :return: A list of :class:`boto.ec2.instanceinfo.InstanceInfo`
        """
        return self.unmonitor_instances([instance_id])

    #
    # Bundle Windows Instances
    #

    def bundle_instance(self, instance_id,
                        s3_bucket,
                        s3_prefix,
                        s3_upload_policy):
        """
        Bundle Windows instance.

        :type instance_id: string
        :param instance_id: The instance id

        :type s3_bucket: string
        :param s3_bucket: The bucket in which the AMI should be stored.

        :type s3_prefix: string
        :param s3_prefix: The beginning of the file name for the AMI.

        :type s3_upload_policy: string
        :param s3_upload_policy: Base64 encoded policy that specifies condition
                                 and permissions for Amazon EC2 to upload the
                                 user's image into Amazon S3.
        """

        params = {'InstanceId' : instance_id,
                  'Storage.S3.Bucket' : s3_bucket,
                  'Storage.S3.Prefix' : s3_prefix,
                  'Storage.S3.UploadPolicy' : s3_upload_policy}
        s3auth = boto.auth.get_auth_handler(None, boto.config,
                                            self.provider, ['s3'])
        params['Storage.S3.AWSAccessKeyId'] = self.aws_access_key_id
        signature = s3auth.sign_string(s3_upload_policy)
        params['Storage.S3.UploadPolicySignature'] = signature
        return self.get_object('BundleInstance', params,
                               BundleInstanceTask, verb='POST')

    def get_all_bundle_tasks(self, bundle_ids=None, filters=None):
        """
        Retrieve current bundling tasks. If no bundle id is specified, all
        tasks are retrieved.

        :type bundle_ids: list
        :param bundle_ids: A list of strings containing identifiers for
                           previously created bundling tasks.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        """

        params = {}
        if bundle_ids:
            self.build_list_params(params, bundle_ids, 'BundleId')
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeBundleTasks', params,
                             [('item', BundleInstanceTask)], verb='POST')

    def cancel_bundle_task(self, bundle_id):
        """
        Cancel a previously submitted bundle task

        :type bundle_id: string
        :param bundle_id: The identifier of the bundle task to cancel.
        """

        params = {'BundleId' : bundle_id}
        return self.get_object('CancelBundleTask', params,
                               BundleInstanceTask, verb='POST')

    def get_password_data(self, instance_id):
        """
        Get encrypted administrator password for a Windows instance.

        :type instance_id: string
        :param instance_id: The identifier of the instance to retrieve the
                            password for.
        """

        params = {'InstanceId' : instance_id}
        rs = self.get_object('GetPasswordData', params, ResultSet, verb='POST')
        return rs.passwordData

    #
    # Cluster Placement Groups
    #

    def get_all_placement_groups(self, groupnames=None, filters=None):
        """
        Get all placement groups associated with your account in a region.

        :type groupnames: list
        :param groupnames: A list of the names of placement groups to retrieve.
                           If not provided, all placement groups will be
                           returned.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list
        :return: A list of :class:`boto.ec2.placementgroup.PlacementGroup`
        """
        params = {}
        if groupnames:
            self.build_list_params(params, groupnames, 'GroupName')
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribePlacementGroups', params,
                             [('item', PlacementGroup)], verb='POST')

    def create_placement_group(self, name, strategy='cluster'):
        """
        Create a new placement group for your account.
        This will create the placement group within the region you
        are currently connected to.

        :type name: string
        :param name: The name of the new placement group

        :type strategy: string
        :param strategy: The placement strategy of the new placement group.
                         Currently, the only acceptable value is "cluster".

        :rtype: bool
        :return: True if successful
        """
        params = {'GroupName':name, 'Strategy':strategy}
        group = self.get_status('CreatePlacementGroup', params, verb='POST')
        return group

    def delete_placement_group(self, name):
        """
        Delete a placement group from your account.

        :type key_name: string
        :param key_name: The name of the keypair to delete
        """
        params = {'GroupName':name}
        return self.get_status('DeletePlacementGroup', params, verb='POST')

    # Tag methods

    def build_tag_param_list(self, params, tags):
        keys = tags.keys()
        keys.sort()
        i = 1
        for key in keys:
            value = tags[key]
            params['Tag.%d.Key'%i] = key
            if value is not None:
                params['Tag.%d.Value'%i] = value
            i += 1

    def get_all_tags(self, filters=None):
        """
        Retrieve all the metadata tags associated with your account.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: dict
        :return: A dictionary containing metadata tags
        """
        params = {}
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeTags', params,
                             [('item', Tag)], verb='POST')

    def create_tags(self, resource_ids, tags):
        """
        Create new metadata tags for the specified resource ids.

        :type resource_ids: list
        :param resource_ids: List of strings

        :type tags: dict
        :param tags: A dictionary containing the name/value pairs.
                     If you want to create only a tag name, the
                     value for that tag should be the empty string
                     (e.g. '').

        """
        params = {}
        self.build_list_params(params, resource_ids, 'ResourceId')
        self.build_tag_param_list(params, tags)
        return self.get_status('CreateTags', params, verb='POST')

    def delete_tags(self, resource_ids, tags):
        """
        Delete metadata tags for the specified resource ids.

        :type resource_ids: list
        :param resource_ids: List of strings

        :type tags: dict or list
        :param tags: Either a dictionary containing name/value pairs
                     or a list containing just tag names.
                     If you pass in a dictionary, the values must
                     match the actual tag values or the tag will
                     not be deleted.  If you pass in a value of None
                     for the tag value, all tags with that name will
                     be deleted.

        """
        if isinstance(tags, list):
            tags = {}.fromkeys(tags, None)
        params = {}
        self.build_list_params(params, resource_ids, 'ResourceId')
        self.build_tag_param_list(params, tags)
        return self.get_status('DeleteTags', params, verb='POST')

    # Network Interface methods

    def get_all_network_interfaces(self, filters=None):
        """
        Retrieve all of the Elastic Network Interfaces (ENI's)
        associated with your account.

        :type filters: dict
        :param filters: Optional filters that can be used to limit
                        the results returned.  Filters are provided
                        in the form of a dictionary consisting of
                        filter names as the key and filter values
                        as the value.  The set of allowable filter
                        names/values is dependent on the request
                        being performed.  Check the EC2 API guide
                        for details.

        :rtype: list
        :return: A list of :class:`boto.ec2.networkinterface.NetworkInterface`
        """
        params = {}
        if filters:
            self.build_filter_params(params, filters)
        return self.get_list('DescribeNetworkInterfaces', params,
                             [('item', NetworkInterface)], verb='POST')

    def create_network_interface(self, subnet_id, private_ip_address=None,
                                 description=None, groups=None):
        """
        Creates a network interface in the specified subnet.

        :type subnet_id: str
        :param subnet_id: The ID of the subnet to associate with the
            network interface.

        :type private_ip_address: str
        :param private_ip_address: The private IP address of the
            network interface.  If not supplied, one will be chosen
            for you.

        :type description: str
        :param description: The description of the network interface.

        :type groups: list
        :param groups: Lists the groups for use by the network interface.
            This can be either a list of group ID's or a list of
            :class:`boto.ec2.securitygroup.SecurityGroup` objects.

        :rtype: :class:`boto.ec2.networkinterface.NetworkInterface`
        :return: The newly created network interface.
        """
        params = {'SubnetId' : subnet_id}
        if private_ip_address:
            params['PrivateIpAddress'] = private_ip_address
        if description:
            params['Description'] = description
        if groups:
            ids = []
            for group in groups:
                if isinstance(group, SecurityGroup):
                    ids.append(group.id)
                else:
                    ids.append(group)
            self.build_list_params(params, ids, 'SecurityGroupId')
        return self.get_object('CreateNetworkInterface', params,
                               NetworkInterface, verb='POST')

    def attach_network_interface(self, network_interface_id,
                                 instance_id, device_index):
        """
        Attaches a network interface to an instance.

        :type network_interface_id: str
        :param network_interface_id: The ID of the network interface to attach.

        :type instance_id: str
        :param instance_id: The ID of the instance that will be attached
            to the network interface.

        :type device_index: int
        :param device_index: The index of the device for the network
            interface attachment on the instance.
        """
        params = {'NetworkInterfaceId' : network_interface_id,
                  'InstanceId' : instance_id,
                  'Deviceindex' : device_index}
        return self.get_status('AttachNetworkInterface', params, verb='POST')

    def detach_network_interface(self, network_interface_id, force=False):
        """
        Detaches a network interface from an instance.

        :type network_interface_id: str
        :param network_interface_id: The ID of the network interface to detach.

        :type force: bool
        :param force: Set to true to force a detachment.

        """
        params = {'NetworkInterfaceId' : network_interface_id}
        if force:
            params['Force'] = 'true'
        return self.get_status('DetachNetworkInterface', params, verb='POST')

    def delete_network_interface(self, network_interface_id):
        """
        Delete the specified network interface.

        :type network_interface_id: str
        :param network_interface_id: The ID of the network interface to delete.

        """
        params = {'NetworkInterfaceId' : network_interface_id}
        return self.get_status('DeleteNetworkInterface', params, verb='POST')

