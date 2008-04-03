# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
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
from boto.ec2.zone import Zone
from boto.ec2.securitygroup import SecurityGroup
from boto.exception import EC2ResponseError

class EC2Connection(AWSQueryConnection):

    APIVersion = boto.config.get('Boto', 'ec2_version', '2008-02-01')
    SignatureVersion = '1'
    ResponseError = EC2ResponseError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, host='ec2.amazonaws.com', debug=0,
                 https_connection_factory=None):
        if config.has_option('Boto', 'ec2_host'):
            host = config.get('Boto', 'ec2_host')
        AWSQueryConnection.__init__(self, aws_access_key_id, aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                                    host, debug, https_connection_factory)

    # Image methods
        
    def get_all_images(self, image_ids=None, owners=None, executable_by=None):
        params = {}
        if image_ids:
            self.build_list_params(params, image_ids, 'ImageId')
        if owners:
            self.build_list_params(params, owners, 'Owner')
        if executable_by:
            self.build_list_params(params, executable_by, 'ExecutableBy')
        return self.get_list('DescribeImages', params, [('item', Image)])

    def register_image(self, image_location):
        params = {'ImageLocation':image_location}
        rs = self.get_object('RegisterImage', params, ResultSet)
        return rs.imageId
        
    def deregister_image(self, image_id):
        return self.get_status('DeregisterImage', {'ImageId':image_id})
        
    # ImageAttribute methods
        
    def get_image_attribute(self, image_id, attribute='launchPermission'):
        params = {'ImageId' : image_id,
                  'Attribute' : attribute}
        return self.get_object('DescribeImageAttribute', params, ImageAttribute)
        
    def modify_image_attribute(self, image_id, attribute='launchPermission',
                               operation='add', user_ids=None, groups=None):
        params = {'ImageId' : image_id,
                  'Attribute' : attribute,
                  'OperationType' : operation}
        if user_ids:
            self.build_list_params(params, user_ids, 'UserId')
        if groups:
            self.build_list_params(params, groups, 'UserGroup')
        return self.get_status('ModifyImageAttribute', params)

    def reset_image_attribute(self, image_id, attribute='launchPermission'):
        params = {'ImageId' : image_id,
                  'Attribute' : attribute}
        return self.get_status('ResetImageAttribute', params)
        
    # Instance methods
        
    def get_all_instances(self, instance_ids=None):
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_list('DescribeInstances', params, [('item', Reservation)])

    def run_instances(self, image_id, min_count=1, max_count=1,
                      key_name=None, security_groups=None,
                      user_data=None, addressing_type=None,
                      instance_type='m1.small', placement=None):
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
        return self.get_object('RunInstances', params, Reservation)
        
    def terminate_instances(self, instance_ids=None):
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_list('TerminateInstances', params, [('item', Instance)])

    def get_console_output(self, instance_id):
        params = {}
        self.build_list_params(params, [instance_id], 'InstanceId')
        return self.get_object('GetConsoleOutput', params, ConsoleOutput)

    def reboot_instances(self, instance_ids=None):
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
        params = {}
        if zones:
            self.build_list_params(params, zones, 'ZoneName')
        return self.get_list('DescribeAvailabilityZones', params, [('item', Zone)])

    # Address methods

    def get_all_addresses(self, addresses=None):
        params = {}
        if addresses:
            self.build_list_params(params, addresses, 'PublicIp')
        return self.get_list('DescribeAddresses', params, [('item', Address)])

    def allocate_address(self):
        return self.get_object('AllocateAddress', None, Address)

    def release_address(self, public_ip):
        params = {'PublicIp' : public_ip}
        return self.get_status('ReleaseAddress', params)

    def associate_address(self, instance_id, public_ip):
        params = {'InstanceId' : instance_id, 'PublicIp' : public_ip}
        return self.get_status('AssociateAddress', params)

    def disassociate_address(self, public_ip):
        params = {'PublicIp' : public_ip}
        return self.get_status('DisassociateAddress', params)

    # Keypair methods
        
    def get_all_key_pairs(self, keynames=None):
        params = {}
        if keynames:
            self.build_list_params(params, keynames, 'KeyName')
        return self.get_list('DescribeKeyPairs', params, [('item', KeyPair)])
        
    def create_key_pair(self, key_name):
        params = {'KeyName':key_name}
        return self.get_object('CreateKeyPair', params, KeyPair)
        
    def delete_key_pair(self, key_name):
        params = {'KeyName':key_name}
        return self.get_status('DeleteKeyPair', params)

    # SecurityGroup methods
        
    def get_all_security_groups(self, groupnames=None):
        params = {}
        if groupnames:
            self.build_list_params(params, groupnames, 'GroupName')
        return self.get_list('DescribeSecurityGroups', params, [('item', SecurityGroup)])

    def create_security_group(self, name, description):
        params = {'GroupName':name, 'GroupDescription':description}
        group = self.get_object('CreateSecurityGroup', params, SecurityGroup)
        group.name = name
        group.description = description
        return group

    def delete_security_group(self, name):
        params = {'GroupName':name}
        return self.get_status('DeleteSecurityGroup', params)

    def authorize_security_group(self, group_name, src_security_group_name=None,
                                 src_security_group_owner_id=None,
                                 ip_protocol=None, from_port=None, to_port=None,
                                 cidr_ip=None):
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

