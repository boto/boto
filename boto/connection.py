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

#
# Parts of this code were copied or derived from sample code supplied by AWS.
# The following notice applies to that code.
#
#  This software code is made available "AS IS" without warranties of any
#  kind.  You may copy, display, modify and redistribute the software
#  code either by itself or as incorporated into your code; provided that
#  you do not remove any proprietary notices.  Your use of this software
#  code is at your own risk and you waive any claim against Amazon
#  Digital Services, Inc. or its affiliates with respect to your use of
#  this software code. (c) 2006 Amazon Digital Services, Inc. or its
#  affiliates.

"""
Handles basic connections to AWS
"""

import base64
import hmac
import httplib
import re
import sha
import sys
import time
import urllib
import os
import xml.sax
from boto.exception import SQSError, S3ResponseError
from boto.exception import S3CreateError, EC2ResponseError
from boto.exception import AWSAuthConnectionError
from boto import handler
from boto.sqs.queue import Queue
from boto.s3.bucket import Bucket
from boto.resultset import ResultSet
from boto.ec2.image import Image, ImageAttribute
from boto.ec2.instance import Reservation, Instance, ConsoleOutput
from boto.ec2.keypair import KeyPair
from boto.ec2.securitygroup import SecurityGroup
import boto.utils

PORTS_BY_SECURITY = { True: 443, False: 80 }

class AWSAuthConnection:
    def __init__(self, server, aws_access_key_id=None,
                 aws_secret_access_key=None, is_secure=True, port=None,
                 proxy=None, proxy_port=None, debug=False):
        self.is_secure = is_secure
        if (is_secure):
            self.protocol = 'https'
        else:
            self.protocol = 'http'
        self.server = server
        self.debug = debug
        if not port:
            port = PORTS_BY_SECURITY[is_secure]
        self.port = port
        self.server_name = '%s:%d' % (server, port)

        if aws_access_key_id:
            self.aws_access_key_id = aws_access_key_id
        else:
            if os.environ.has_key('AWS_ACCESS_KEY_ID'):
                self.aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']

        if aws_secret_access_key:
            self.aws_secret_access_key = aws_secret_access_key
        else:
            if os.environ.has_key('AWS_SECRET_ACCESS_KEY'):
                self.aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']

        self.proxy = proxy
        #This lowercase environment var is the same as used in urllib
        if os.environ.has_key('http_proxy'): 
            self.proxy = os.environ['http_proxy'].split(':')[0]
	self.use_proxy = (self.proxy != None)

        if (self.use_proxy and self.is_secure):
            raise AWSAuthConnectionError("Unable to provide secure connection through proxy")

        if proxy_port:
            self.proxy_port = proxy_port
        else:
            if os.environ.has_key('http_proxy'):
                self.proxy_port = os.environ['http_proxy'].split(':')[1]

        self.make_http_connection()
        self._last_rs = None

    def make_http_connection(self):
	if (self.use_proxy):
	    cnxn_point = self.proxy
            cnxn_port = int(self.proxy_port)
	else:
	    cnxn_point = self.server
            cnxn_port = self.port
        if self.debug:
            print 'establishing HTTP connection'
        if (self.is_secure):
            self.connection = httplib.HTTPSConnection("%s:%d" % (cnxn_point,
                                                                 cnxn_port))
        else:
            self.connection = httplib.HTTPConnection("%s:%d" % (cnxn_point,
                                                                cnxn_port))
        self.set_debug(self.debug)

    def set_debug(self, debug=0):
        self.debug = debug
        self.connection.set_debuglevel(debug)

    def prefix_proxy_to_path(self, path):
        path = self.protocol + '://' + self.server + path
        return path
        
    def make_request(self, method, path, headers=None, data='', metadata=None):
        if headers == None:
            headers = {}
        if metadata == None:
            metadata = {}
        if not headers.has_key('Content-Length'):
            headers['Content-Length'] = len(data)
        final_headers = boto.utils.merge_meta(headers, metadata);
        # add auth header
        self.add_aws_auth_header(final_headers, method, path)
        if self.use_proxy:
            path = self.prefix_proxy_to_path(path)
        self.connection.request(method, path, data, final_headers)
        try:
            return self.connection.getresponse()
        except httplib.HTTPException, e:
            self.make_http_connection()
            self.connection.request(method, path, data, final_headers)
            return self.connection.getresponse()

    def add_aws_auth_header(self, headers, method, path):
        if not headers.has_key('Date'):
            headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT",
                                            time.gmtime())

        c_string = boto.utils.canonical_string(method, path, headers)
        if self.debug:
            print '\n\n%s\n\n' % c_string
        headers['Authorization'] = \
            "AWS %s:%s" % (self.aws_access_key_id,
                           boto.utils.encode(self.aws_secret_access_key,
                                             c_string))
        
class SQSConnection(AWSAuthConnection):
    
    DefaultHost = 'queue.amazonaws.com'
    DefaultVersion = '2006-04-01'
    DefaultContentType = 'text/plain'
    
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=False, port=None, proxy=None, proxy_port=None,
                 debug=0):
        AWSAuthConnection.__init__(self, self.DefaultHost,
                                   aws_access_key_id, aws_secret_access_key,
                                   is_secure, port, proxy, proxy_port, debug)

    def make_request(self, method, path, headers=None, data=''):
        # add auth header
        if headers == None:
            headers = {}

        if not headers.has_key('AWS-Version'):
            headers['AWS-Version'] = self.DefaultVersion

        if not headers.has_key('Content-Type'):
            headers['Content-Type'] = self.DefaultContentType

        return AWSAuthConnection.make_request(self, method, path,
                                              headers, data)

    def get_all_queues(self, prefix=''):
        if prefix:
            path = '/?QueueNamePrefix=%s' % prefix
        else:
            path = '/'
        response = self.make_request('GET', path)
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        rs = ResultSet('QueueUrl', Queue)
        h = handler.XmlHandler(rs, self)
        xml.sax.parseString(body, h)
        return rs

    def create_queue(self, queue_name, visibility_timeout=None):
        path = '/?QueueName=%s' % queue_name
        if visibility_timeout:
            path = path + '&DefaultVisibilityTimeout=%d' % visibility_timeout
        response = self.make_request('POST', path)
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        q = Queue(self)
        h = handler.XmlHandler(q, self)
        xml.sax.parseString(body, h)
        return q

    def delete_queue(self, queue):
        response = self.make_request('DELETE', queue.id)
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        rs = ResultSet()
        h = handler.XmlHandler(rs, self)
        xml.sax.parseString(body, h)
        return rs

class S3Connection(AWSAuthConnection):

    DefaultHost = 's3.amazonaws.com'
    QueryString = 'Signature=%s&Expires=%d&AWSAccessKeyId=%s'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=False, port=None, proxy=None, proxy_port=None,
                 debug=0):
        AWSAuthConnection.__init__(self, self.DefaultHost,
                                   aws_access_key_id, aws_secret_access_key,
                                   is_secure, port, proxy, proxy_port, debug)
    
    def generate_url(self, expires_in, method, path, headers):
        expires = int(time.time() + expires_in)
        canonical_str = boto.utils.canonical_string(method, path,
                                                    headers, expires)
        encoded_canonical = boto.utils.encode(self.aws_secret_access_key,
                                              canonical_str, True)
        if '?' in path:
            arg_div = '&'
        else:
            arg_div = '?'
        query_part = self.QueryString % (encoded_canonical, expires,
                                         self.aws_access_key_id)
        return self.protocol + '://' + self.server_name + path  + arg_div + query_part
    
    def get_all_buckets(self):
        path = '/'
        response = self.make_request('GET', urllib.quote(path))
        body = response.read()
        if response.status > 300:
            raise S3ResponseError(response.status, response.reason)
        rs = ResultSet('Bucket', Bucket)
        h = handler.XmlHandler(rs, self)
        xml.sax.parseString(body, h)
        return rs

    def get_bucket(self, bucket_name):
        bucket = Bucket(self, bucket_name)
        rs = bucket.get_all_keys(None, maxkeys=0)
        return bucket

    def create_bucket(self, bucket_name, headers={}):
        path = '/%s' % bucket_name
        response = self.make_request('PUT', urllib.quote(path), headers)
        body = response.read()
        if response.status == 409:
             raise S3CreateError(response.status, response.reason)
        if response.status == 200:
            b = Bucket(self, bucket_name, debug=self.debug)
            return b
        else:
            raise S3ResponseError(response.status, response.reason)

    def delete_bucket(self, bucket):
        if isinstance(bucket, Bucket):
            bucket_name = bucket.name
        else:
            bucket_name = bucket
        path = '/%s' % bucket_name
        response = self.make_request('DELETE', urllib.quote(path))
        body = response.read()
        if response.status != 204:
            raise S3ResponseError(response.status, response.reason)

class EC2Connection(AWSAuthConnection):

    DefaultHost = 'ec2.amazonaws.com'
    EC2Version = '2007-01-03'
    SignatureVersion = '1'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 debug=0):
        AWSAuthConnection.__init__(self, self.DefaultHost,
                                   aws_access_key_id, aws_secret_access_key,
                                   is_secure, port, proxy, proxy_port, debug)

    def make_request(self, action, params=None):
        if params == None:
            params = {}
        h = hmac.new(key=self.aws_secret_access_key, digestmod=sha)
        params['Action'] = action
        params['Version'] = self.EC2Version
        params['AWSAccessKeyId'] = self.aws_access_key_id
        params['SignatureVersion'] = self.SignatureVersion
        params['Timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        keys = params.keys()
	keys.sort(cmp = lambda x, y: cmp(x.lower(), y.lower()))
        qs = ''
        for key in keys:
            h.update(key)
            h.update(str(params[key]))
            qs += key + '=' + urllib.quote(str(params[key])) + '&'
        signature = base64.b64encode(h.digest())
        qs = '/?' + qs + 'Signature=' + urllib.quote(signature)

	if self.use_proxy:
            qs = self.prefix_proxy_to_path(qs)

        self.connection.request('GET', qs)
        try:
            return self.connection.getresponse()
        except httplib.HTTPException, e:
            self.make_http_connection()
            self.connection.request('GET', qs)
            return self.connection.getresponse()

    def build_list_params(self, params, items, label):
        for i in range(1, len(items)+1):
            params['%s.%d' % (label, i)] = items[i-1]

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
            rs = ResultSet('item', Image)
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
            rs = ResultSet('item', Reservation)
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    def run_instances(self, image_id, min_count=1, max_count=1, key_name=None,
                      security_groups=None, user_data=None):
        params = {'ImageId':image_id,
                  'MinCount':min_count,
                  'MaxCount': max_count}
        if key_name:
            params['KeyName'] = key_name
        if security_groups:
            self.build_list_params(params, security_groups, 'SecurityGroup')
        if user_data:
            params['UserData'] = user_data
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
            rs = ResultSet('item', Instance)
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

    # Keypair methods
        
    def get_all_key_pairs(self, keynames=None):
        params = {}
        if keynames:
            self.build_list_params(params, keynames, 'KeyName')
        response = self.make_request('DescribeKeyPairs', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet('item', KeyPair)
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
            rs = ResultSet('item', SecurityGroup)
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


        
