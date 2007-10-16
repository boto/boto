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
from boto import handler
from boto.connection import AWSQueryConnection
from boto.resultset import ResultSet
from boto.ec2.image import Image, ImageAttribute
from boto.ec2.instance import Reservation, Instance, ConsoleOutput
from boto.ec2.keypair import KeyPair
from boto.ec2.securitygroup import SecurityGroup
from boto.exception import EC2ResponseError

class EC2Connection(AWSQueryConnection):

    APIVersion = '2007-08-29'
    SignatureVersion = '1'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 host='ec2-pinotage.amazonaws.com', debug=0,
                 https_connection_factory=None):
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
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
        response = self.make_request('DescribeImages', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet([('item', Image)])
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    def register_image(self, image_location):
        params = {'ImageLocation':image_location}
        response = self.make_request('RegisterImage', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs.imageId
        else:
            raise EC2ResponseError(response.status, response.reason, body)
        
    def deregister_image(self, image_id):
        params = {'ImageId':image_id}
        response = self.make_request('DeregisterImage', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs.status
        else:
            raise EC2ResponseError(response.status, response.reason, body)
        
    # ImageAttribute methods
        
    def get_image_attribute(self, image_id, attribute='launchPermission'):
        params = {'ImageId' : image_id,
                  'Attribute' : attribute}
        response = self.make_request('DescribeImageAttribute', params)
        body = response.read()
        if response.status == 200:
            image_attr = ImageAttribute()
            h = handler.XmlHandler(image_attr, self)
            xml.sax.parseString(body, h)
            return image_attr
        else:
            raise EC2ResponseError(response.status, response.reason, body)
        
    def modify_image_attribute(self, image_id, attribute='launchPermission',
                               operation='add', user_ids=None, groups=None):
        params = {'ImageId' : image_id,
                  'Attribute' : attribute,
                  'OperationType' : operation}
        if user_ids:
            self.build_list_params(params, user_ids, 'UserId')
        if groups:
            self.build_list_params(params, groups, 'UserGroup')
        response = self.make_request('ModifyImageAttribute', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs.status
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    def reset_image_attribute(self, image_id, attribute='launchPermission'):
        params = {'ImageId' : image_id,
                  'Attribute' : attribute}
        response = self.make_request('ResetImageAttribute', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs.status
        else:
            raise EC2ResponseError(response.status, response.reason, body)
        
    # Instance methods
        
    def get_all_instances(self, instance_ids=None):
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        response = self.make_request('DescribeInstances', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet([('item', Reservation)])
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    def run_instances(self, image_id, min_count=1, max_count=1,
                      key_name=None, security_groups=None,
                      user_data=None, addressing_type=None,
                      instance_type='m1.small'):
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
        response = self.make_request('RunInstances', params)
        body = response.read()
        if response.status == 200:
            res = Reservation(self.connection)
            h = handler.XmlHandler(res, self)
            xml.sax.parseString(body, h)
            return res
        else:
            raise EC2ResponseError(response.status, response.reason, body)
        
    def terminate_instances(self, instance_ids=None):
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        response = self.make_request('TerminateInstances', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet([('item', Instance)])
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    def get_console_output(self, instance_id):
        params = {}
        self.build_list_params(params, [instance_id], 'InstanceId')
        response = self.make_request('GetConsoleOutput', params)
        body = response.read()
        if response.status == 200:
            co = ConsoleOutput()
            h = handler.XmlHandler(co, self)
            xml.sax.parseString(body, h)
            return co
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    def reboot_instances(self, instance_ids=None):
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        response = self.make_request('RebootInstances', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs.status
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    def confirm_product_instance(self, product_code, instance_id):
        params = {'ProductCode' : product_code,
                  'InstanceId' : instance_id}
        response = self.make_request('ConfirmProductInstance', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return (rs.status, rs.ownerId)
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    # Keypair methods
        
    def get_all_key_pairs(self, keynames=None):
        params = {}
        if keynames:
            self.build_list_params(params, keynames, 'KeyName')
        response = self.make_request('DescribeKeyPairs', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet([('item', KeyPair)])
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise EC2ResponseError(response.status, response.reason, body)
        
    def create_key_pair(self, key_name):
        params = {'KeyName':key_name}
        response = self.make_request('CreateKeyPair', params)
        body = response.read()
        if response.status == 200:
            key = KeyPair(self)
            h = handler.XmlHandler(key, self)
            xml.sax.parseString(body, h)
            return key
        else:
            raise EC2ResponseError(response.status, response.reason, body)
        
    def delete_key_pair(self, key_name):
        params = {'KeyName':key_name}
        response = self.make_request('DeleteKeyPair', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs.status
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    # SecurityGroup methods
        
    def get_all_security_groups(self, groupnames=None):
        params = {}
        if groupnames:
            self.build_list_params(params, groupnames, 'GroupName')
        response = self.make_request('DescribeSecurityGroups', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet([('item', SecurityGroup)])
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    def create_security_group(self, name, description):
        params = {'GroupName':name, 'GroupDescription':description}
        response = self.make_request('CreateSecurityGroup', params)
        body = response.read()
        if response.status == 200:
            sg = SecurityGroup(self, name=name, description=description)
            h = handler.XmlHandler(sg, self)
            xml.sax.parseString(body, h)
            if sg.status:
                return sg
            else:
                return None
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    def delete_security_group(self, name):
        params = {'GroupName':name}
        response = self.make_request('DeleteSecurityGroup', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs.status
        else:
            raise EC2ResponseError(response.status, response.reason, body)

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
        response = self.make_request('AuthorizeSecurityGroupIngress', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs.status
        else:
            raise EC2ResponseError(response.status, response.reason, body)

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
        response = self.make_request('RevokeSecurityGroupIngress', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs.status
        else:
            raise EC2ResponseError(response.status, response.reason, body)

