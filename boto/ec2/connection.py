# Copyright (c) 2006-2008 Mitch Garnaat http://garnaat.org/
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
import xml.sax
import base64
import boto
from boto import config
from boto.connection import AWSQueryConnection
from boto.resultset import ResultSet
from boto.ec2.image import Image, ImageAttribute
from boto.ec2.instance import Reservation, Instance, ConsoleOutput
from boto.ec2.keypair import KeyPair
from boto.ec2.address import Address
from boto.ec2.volume import Volume
from boto.ec2.snapshot import Snapshot
from boto.ec2.zone import Zone
from boto.ec2.securitygroup import SecurityGroup
from boto.ec2.regioninfo import RegionInfo
from boto.exception import EC2ResponseError

class EC2Connection(AWSQueryConnection):

    APIVersion = boto.config.get('Boto', 'ec2_version', '2008-12-01')
    DefaultRegionName = boto.config.get('Boto', 'ec2_region_name', 'us-east-1')
    DefaultRegionEndpoint = boto.config.get('Boto', 'ec2_region_endpoint',
                                            'us-east-1.ec2.amazonaws.com')
    SignatureVersion = '2'
    ResponseError = EC2ResponseError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None):
        """
        Init method to create a new connection to EC2.
        
        B{Note:} The host argument is overridden by the host specified in the boto configuration file.        
        """
        if not region:
            region = RegionInfo(self, self.DefaultRegionName, self.DefaultRegionEndpoint)
        self.region = region
        AWSQueryConnection.__init__(self, aws_access_key_id, aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                                    self.region.endpoint, debug, https_connection_factory)

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
        
        @type image_ids: list
        @param image_ids: A list of strings with the image IDs wanted
        
        @type owners: list
        @param owners: A list of owner IDs
        
        @type executable_by: 
        @param executable_by: 
        
        @rtype: list
        @return: A list of L{Images<boto.ec2.image.Image>}
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
        
        @type kernel_ids: list
        @param kernel_ids: A list of strings with the image IDs wanted
        
        @type owners: list
        @param owners: A list of owner IDs
        
        @rtype: list
        @return: A list of L{Images<boto.ec2.image.Image>}
        """
        rs = self.get_all_images(kernel_ids, owners)
        kernels = []
        for image in rs:
            if image.type == 'kernel':
                kernels.append(image)
        return kernels

    def get_all_ramdisks(self, ramdisk_ids=None, owners=None):
        """
        Retrieve all the EC2 ramdisks available on your account.  Simply filters the list returned
        by get_all_images because EC2 does not provide a way to filter server-side.
        
        @type ramdisk_ids: list
        @param ramdisk_ids: A list of strings with the image IDs wanted
        
        @type owners: list
        @param owners: A list of owner IDs
        
        @rtype: list
        @return: A list of L{Images<boto.ec2.image.Image>}
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
        
        @type image_id: string
        @param image_id: the ID of the Image to retrieve
        
        @rtype: L{Image<boto.ec2.image.Image>}
        @return: The EC2 Image specified or None if the image is not found
        """
        try:
            return self.get_all_images(image_ids=[image_id])[0]
        except IndexError: # None of those images available
            return None

    def register_image(self, image_location):
        """
        Register an image.

        @type image_location: string
        @param image_location: Full path to your AMI manifest in Amazon S3 storage.

        @rtype: string
        @return: The new image id
        """
        params = {'ImageLocation':image_location}
        rs = self.get_object('RegisterImage', params, ResultSet)
        return rs.imageId
        
    def deregister_image(self, image_id):
        """
        Unregister an AMI.
        
        @type image_id: string
        @param image_id: the ID of the Image to unregister
        
        @rtype: bool
        @return: True if successful
        """
        return self.get_status('DeregisterImage', {'ImageId':image_id})
        
    # ImageAttribute methods
        
    def get_image_attribute(self, image_id, attribute='launchPermission'):
        """
        Gets an attribute from an image.
        See http://docs.amazonwebservices.com/AWSEC2/2008-02-01/DeveloperGuide/ApiReference-Query-DescribeImageAttribute.html
        
        @type image_id: string
        @param image_id: The Amazon image id for which you want info about
        
        @type attribute: string
        @param attribute: The attribute you need information about
        
        @rtype: L{ImageAttribute<boto.ec2.image.ImageAttribute>}
        @return: An ImageAttribute object representing the value of the attribute requested
        """
        params = {'ImageId' : image_id,
                  'Attribute' : attribute}
        return self.get_object('DescribeImageAttribute', params, ImageAttribute)
        
    def modify_image_attribute(self, image_id, attribute='launchPermission',
                               operation='add', user_ids=None, groups=None):
        """
        Changes an attribute of an image.
        See http://docs.amazonwebservices.com/AWSEC2/2008-02-01/DeveloperGuide/ApiReference-Query-ModifyImageAttribute.html
        
        @type image_id: string
        @param image_id: The image id you wish to change
        
        @type attribute: string
        @param attribute: The attribute you wish to change
        
        @type operation: string
        @param operation: Either add or remove (this is required for changing launchPermissions
        
        @type user_ids: list
        @param user_ids: The Amazon IDs of users to add/remove attributes
        
        @type groups: list
        @param groups: The groups to add/remove attributes
        """
        params = {'ImageId' : image_id,
                  'Attribute' : attribute,
                  'OperationType' : operation}
        if user_ids:
            self.build_list_params(params, user_ids, 'UserId')
        if groups:
            self.build_list_params(params, groups, 'UserGroup')
        return self.get_status('ModifyImageAttribute', params)

    def reset_image_attribute(self, image_id, attribute='launchPermission'):
        """
        Resets an attribute of an AMI to its default value.
        See http://docs.amazonwebservices.com/AWSEC2/2008-02-01/DeveloperGuide/ApiReference-Query-ResetImageAttribute.html
        
        @type image_id: string
        @param image_id: ID of the AMI for which an attribute will be described
        
        @type attribute: string
        @param attribute: The attribute to reset
        
        @rtype: bool
        @return: Whether the operation succeeded or not
        """
        params = {'ImageId' : image_id,
                  'Attribute' : attribute}
        return self.get_status('ResetImageAttribute', params)
        
    # Instance methods
        
    def get_all_instances(self, instance_ids=None):
        """
        Retrieve all the instances associated with your account.
        
        @type instance_ids: list
        @param instance_ids: A list of strings of instance IDs
        
        @rtype: list
        @return: A list of L{Instances<boto.ec2.instance.Instance>}
        """
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_list('DescribeInstances', params, [('item', Reservation)])

    def run_instances(self, image_id, min_count=1, max_count=1,
                      key_name=None, security_groups=None,
                      user_data=None, addressing_type=None,
                      instance_type='m1.small', placement=None,
                      kernel_id=None, ramdisk_id=None):
        """
        Runs an image on EC2.
        
        @type image_id: string
        @param image_id: The ID of the image to run
        
        @type min_count: int
        @param min_count: The minimum number of instances to launch
        
        @type max_count: int
        @param max_count: The maximum number of instances to launch
        
        @type key_name: string
        @param key_name: The name of the key pair with which to launch instances
        
        @type security_groups: list of strings
        @param security_groups: The names of the security groups with which to associate instances
        
        @type user_data: string
        @param user_data: The user data passed to the launched instances
        
        @type instance_type: string
        @param instance_type: The type of instance to run (m1.small, m1.large, m1.xlarge)
        
        @type placement: string
        @param placement: The availability zone in which to launch the instances
        
        @type kernel_id: string
        @param kernel_id: The ID of the kernel with which to launch the instances
        
        @type ramdisk_id: string
        @param ramdisk_id: The ID of the RAM disk with which to launch the instances
        
        @rtype: Reservation
        @return: The L{Reservation<boto.ec2.instance.Reservation>} associated with the request for machines
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
        return self.get_object('RunInstances', params, Reservation)
        
    def terminate_instances(self, instance_ids=None):
        """
        Terminate the instances specified
        
        @type instance_ids: list
        @param instance_ids: A list of strings of the Instance IDs to terminate
        
        @rtype: list
        @return: A list of the instances terminated
        """
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_list('TerminateInstances', params, [('item', Instance)])

    def get_console_output(self, instance_id):
        """
        Retrieves the console output for the specified instance.
        See http://docs.amazonwebservices.com/AWSEC2/2008-02-01/DeveloperGuide/ApiReference-Query-GetConsoleOutput.html
        
        @type instance_id: string
        @param instance_id: The instance ID of a running instance on the cloud.
        
        @rtype: L{boto.ec2.instance.ConsoleOutput}
        @return: The console output as a ConsoleOutput object
        """
        params = {}
        self.build_list_params(params, [instance_id], 'InstanceId')
        return self.get_object('GetConsoleOutput', params, ConsoleOutput)

    def reboot_instances(self, instance_ids=None):
        """
        Reboot the specified instances.
        
        @type instance_ids: list
        @param instance_ids: The instances to terminate and reboot
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

    # Zone methods

    def get_all_zones(self, zones=None):
        """
        Get all Availability Zones associated with the current region.

        @type zones: list
        @param zones: Optional list of zones.  If this list is present,
                      only the Zones associated with these zone names
                      will be returned.

        @rtype: list of L{boto.ec2.zone.Zone}
        @return: The requested Zone objects
        """
        params = {}
        if zones:
            self.build_list_params(params, zones, 'ZoneName')
        return self.get_list('DescribeAvailabilityZones', params, [('item', Zone)])

    # Address methods

    def get_all_addresses(self, addresses=None):
        """
        Get all EIP's associated with the current credentials.

        @type addresses: list
        @param addresses: Optional list of addresses.  If this list is present,
                           only the Addresses associated with these addresses
                           will be returned.

        @rtype: list of L{boto.ec2.address.Address}
        @return: The requested Address objects
        """
        params = {}
        if addresses:
            self.build_list_params(params, addresses, 'PublicIp')
        return self.get_list('DescribeAddresses', params, [('item', Address)])

    def allocate_address(self):
        """
        Allocate a new Elastic IP address and associate it with your account.

        @rtype: L{boto.ec2.address.Address}
        @return: The newly allocated Address
        """
        return self.get_object('AllocateAddress', None, Address)

    def associate_address(self, instance_id, public_ip):
        """
        Associate an Elastic IP address with a currently running instance.

        @type instance_id: string
        @param instance_id: The ID of the instance

        @type public_ip: string
        @param public_ip: The public IP address

        @rtype: bool
        @return: True if successful
        """
        params = {'InstanceId' : instance_id, 'PublicIp' : public_ip}
        return self.get_status('AssociateAddress', params)

    def disassociate_address(self, public_ip):
        """
        Disassociate an Elastic IP address from a currently running instance.

        @type public_ip: string
        @param public_ip: The public IP address

        @rtype: bool
        @return: True if successful
        """
        params = {'PublicIp' : public_ip}
        return self.get_status('DisassociateAddress', params)

    def release_address(self, public_ip):
        """
        Free up an Elastic IP address

        @type public_ip: string
        @param public_ip: The public IP address

        @rtype: bool
        @return: True if successful
        """
        params = {'PublicIp' : public_ip}
        return self.get_status('ReleaseAddress', params)

    # Volume methods

    def get_all_volumes(self, volume_ids=None):
        """
        Get all Volumes associated with the current credentials.

        @type volume_ids: list
        @param volume_ids: Optional list of volume ids.  If this list is present,
                           only the volumes associated with these volume ids
                           will be returned.

        @rtype: list of L{boto.ec2.volume.Volume}
        @return: The requested Volume objects
        """
        params = {}
        if volume_ids:
            self.build_list_params(params, volume_ids, 'VolumeId')
        return self.get_list('DescribeVolumes', params, [('item', Volume)])
        
    def create_volume(self, size, zone, snapshot=None):
        """
        Create a new EBS Volume.

        @type size: int
        @param size: The size of the new volume, in GiB

        @type zone: string or L{boto.ec2.zone.Zone}
        @param zone: The availability zone in which the Volume will be created.

        @type snapshot: string or L{boto.ec2.snapshot.Snapshot}
        @param snapshot: The snapshot from which the new Volume will be created.
        """
        if isinstance(zone, Zone):
            zone = zone.name
        params = {'Size': size, 'AvailabilityZone' : zone}
        if snapshot:
            if isinstance(snapshot, Snapshot):
                snapshot = snapshot.id
            params['SnapshotId'] = snapshot
        return self.get_object('CreateVolume', params, Volume)
        
    def delete_volume(self, volume_id):
        params = {'VolumeId': volume_id}
        return self.get_status('DeleteVolume', params)

    def attach_volume(self, volume_id, instance_id, device):
        params = {'InstanceId' : instance_id,
                  'VolumeId' : volume_id,
                  'Device' : device}
        return self.get_status('AttachVolume', params)

    def detach_volume(self, volume_id, instance_id, device='', force=False):
        params = {'InstanceId' : instance_id,
                  'VolumeId' : volume_id,
                  'Device' : device}
        if force:
            params['Force'] = 'true'
        return self.get_status('DetachVolume', params)

    # Snapshot methods

    def get_all_snapshots(self, snapshot_ids=None):
        """
        Get all EBS Snapshots associated with the current credentials.

        @type snapshot_ids: list
        @param snapshot_ids: Optional list of snapshot ids.  If this list is present,
                           only the Snapshots associated with these snapshot ids
                           will be returned.

        @rtype: list of L{boto.ec2.snapshot.Snapshot}
        @return: The requested Snapshot objects
        """
        params = {}
        if snapshot_ids:
            self.build_list_params(params, snapshot_ids, 'SnapshotId')
        return self.get_list('DescribeSnapshots', params, [('item', Snapshot)])
        
    def create_snapshot(self, volume_id):
        params = {'VolumeId' : volume_id}
        return self.get_object('CreateSnapshot', params, Snapshot)
        
    def delete_snapshot(self, snapshot_id):
        params = {'SnapshotId': snapshot_id}
        return self.get_status('DeleteSnapshot', params)

    # Keypair methods
        
    def get_all_key_pairs(self, keynames=None):
        """
        Get all key pairs associated with your account.
        
        @type keynames: list
        @param keynames: A list of the names of keypairs to retrieve.
                         If not provided, all key pairs will be returned.
        
        @rtype: list
        @return: A list of L{KeyPairs<boto.ec2.keypair.KeyPair>}
        """
        params = {}
        if keynames:
            self.build_list_params(params, keynames, 'KeyName')
        return self.get_list('DescribeKeyPairs', params, [('item', KeyPair)])
    
    def get_key_pair(self, keyname):
        """
        Convenience method to retrieve a specific keypair (KeyPair).
        
        @type image_id: string
        @param image_id: the ID of the Image to retrieve
        
        @rtype: L{KeyPair<boto.ec2.keypair.KeyPair>}
        @return: The KeyPair specified or None if it is not found
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
        
        @type key_name: string
        @param key_name: The name of the new keypair
        
        @rtype: L{KeyPair<boto.ec2.keypair.KeyPair>}
        @return: The newly created L{KeyPair<boto.ec2.keypair.KeyPair>}.
                 The material attribute of the new KeyPair object
                 will contain the the unencrypted PEM encoded RSA private key.
        """
        params = {'KeyName':key_name}
        return self.get_object('CreateKeyPair', params, KeyPair)
        
    def delete_key_pair(self, key_name):
        """
        Delete a key pair from your account.
        
        @type key_name: string
        @param key_name: The name of the keypair to delete
        """
        params = {'KeyName':key_name}
        return self.get_status('DeleteKeyPair', params)

    # SecurityGroup methods
        
    def get_all_security_groups(self, groupnames=None):
        """
        Get all security groups associated with your account in a region.
        
        @type groupnames: list
        @param groupnames: A list of the names of security groups to retrieve.
                           If not provided, all security groups will be returned.
        
        @rtype: list
        @return: A list of L{SecurityGroups<boto.ec2.securitygroup.SecurityGroup>}
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
        
        @type name: string
        @param name: The name of the new security group
        
        @type description: string
        @param description: The description of the new security group
        
        @rtype: L{SecurityGroup<boto.ec2.securitygroup.SecurityGroup>}
        @return: The newly created L{KeyPair<boto.ec2.keypair.KeyPair>}.
        """
        params = {'GroupName':name, 'GroupDescription':description}
        group = self.get_object('CreateSecurityGroup', params, SecurityGroup)
        group.name = name
        group.description = description
        return group

    def delete_security_group(self, name):
        """
        Delete a security group from your account.
        
        @type key_name: string
        @param key_name: The name of the keypair to delete
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
        
        @type group_name: string
        @param group_name: The name of the security group you are adding
                           the rule to.
                           
        @type src_security_group_name: string
        @param src_security_group_name: The name of the security group you are 
                                        granting access to.
                                        
        @type src_security_group_owner_id: string
        @param src_security_group_owner_id: The ID of the owner of the security group you are 
                                            granting access to.
                                            
        @type ip_protocol: string
        @param ip_protocol: Either tcp | udp | icmp

        @type from_port: int
        @param from_port: The beginning port number you are enabling

        @type to_port: int
        @param to_port: The ending port number you are enabling

        @type to_port: string
        @param to_port: The CIDR block you are providing access to.
                        See http://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing

        @rtype: bool
        @return: True if successful.
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
        
        @type group_name: string
        @param group_name: The name of the security group you are removing
                           the rule from.
                           
        @type src_security_group_name: string
        @param src_security_group_name: The name of the security group you are 
                                        revoking access to.
                                        
        @type src_security_group_owner_id: string
        @param src_security_group_owner_id: The ID of the owner of the security group you are 
                                            revoking access to.
                                            
        @type ip_protocol: string
        @param ip_protocol: Either tcp | udp | icmp

        @type from_port: int
        @param from_port: The beginning port number you are disabling

        @type to_port: int
        @param to_port: The ending port number you are disabling

        @type to_port: string
        @param to_port: The CIDR block you are revoking access to.
                        See http://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing
                        
        @rtype: bool
        @return: True if successful.
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
        
        @rtype: list
        @return: A list of L{RegionInfo<boto.ec2.regioninfo.RegionInfo>}
        """
        return self.get_list('DescribeRegions', None, [('item', RegionInfo)])


