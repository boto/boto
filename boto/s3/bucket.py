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

from boto import handler
from boto.resultset import ResultSet
from boto.s3.acl import Policy, CannedACLStrings, ACL, Grant
from boto.s3.user import User
from boto.s3.key import Key
from boto.exception import S3ResponseError
import boto.utils
import xml.sax
import urllib

class Bucket:

    BucketLoggingBody = """<?xml version="1.0" encoding="UTF-8"?>
       <BucketLoggingStatus xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
         <LoggingEnabled>
           <TargetBucket>%s</TargetBucket>
           <TargetPrefix>%s</TargetPrefix>
         </LoggingEnabled>
       </BucketLoggingStatus>"""
    
    EmptyBucketLoggingBody = """<?xml version="1.0" encoding="UTF-8"?>
       <BucketLoggingStatus xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
       </BucketLoggingStatus>"""

    LoggingGroup = 'http://acs.amazonaws.com/groups/s3/LogDelivery'

    def __init__(self, connection=None, name=None, debug=None):
        self.name = name
        self.connection = connection
        self.debug = debug

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'Name':
            self.name = value
        elif name == 'CreationDate':
            self.creation_date = value
        else:
            setattr(self, name, value)

    def lookup(self, key):
        path = '/%s/%s' % (self.name, key)
        response = self.connection.make_request('HEAD', urllib.quote(path))
        if response.status == 200:
            body = response.read()
            k = Key()
            k.bucket = self
            k.metadata = boto.utils.get_aws_metadata(response.msg)
            k.etag = response.getheader('etag')
            k.content_type = response.getheader('content-type')
            k.last_modified = response.getheader('last-modified')
            k.key = key
            return k
        else:
            # -- gross hack --
            # httplib gets confused with chunked responses to HEAD requests
            # so I have to fake it out
            response.chunked = 0
            body = response.read()
            return None

    # params can be one of: prefix, marker, max-keys, delimiter
    # as defined in S3 Developer's Guide, however since max-keys is not
    # a legal variable in Python you have to pass maxkeys and this
    # method will munge it (Ugh!)
    def get_all_keys(self, headers=None, **params):
        path = '/%s' % urllib.quote(self.name)
        l = []
        for k,v in params.items():
            if  k == 'maxkeys':
                k = 'max-keys'
            l.append('%s=%s' % (urllib.quote(k), urllib.quote(str(v))))
        s = '&'.join(l)
        if s:
            path = path + '?%s' % s
        response = self.connection.make_request('GET', path, headers)
        body = response.read()
        if response.status == 200:
            rs = ResultSet('Contents', Key)
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise S3ResponseError(response.status, response.reason)

    def delete_key(self, key_name):
        # for backward compatibility, previous version expected a Key object
        if isinstance(key_name, Key):
            key_name = key_name.key
        path = '/%s/%s' % (self.name, key_name)
        response = self.connection.make_request('DELETE',
                                                urllib.quote(path))
        body = response.read()
        if response.status != 204:
            raise S3ResponseError(response.status, response.reason)

    def set_canned_acl(self, acl_str, key_name=None):
        assert acl_str in CannedACLStrings
        if key_name:
            path = '/%s/%s' % (self.name, key_name)
        else:
            path = '/%s' % self.name
        path = urllib.quote(path) + '?acl'
        headers = {'x-amz-acl': acl_str}
        response = self.connection.make_request('PUT', path, headers)
        body = response.read()
        if response.status != 200:
            raise S3ResponseError(response.status, response.reason)

    def set_xml_acl(self, acl_str, key_name=None):
        if key_name:
            path = '/%s/%s' % (self.name, key_name)
        else:
            path = '/%s' % self.name
        path = urllib.quote(path) + '?acl'
        response = self.connection.make_request('PUT', path, data=acl_str)
        body = response.read()
        if response.status != 200:
            raise S3ResponseError(response.status, response.reason)

    def set_acl(self, acl_or_str, key_name=None):
        # just in case user passes a Key object rather than key name
        if isinstance(key_name, Key):
            key_name = key_name.key
        if isinstance(acl_or_str, Policy):
            self.set_xml_acl(acl_or_str.to_xml(), key_name)
        else:
            self.set_canned_acl(acl_or_str, key_name)
            
    def get_acl(self, key_name=None):
        # just in case user passes a Key object rather than key name
        if isinstance(key_name, Key):
            key_name = key_name.key
        if key_name:
            path = '/%s/%s' % (self.name, key_name)
        else:
            path = '/%s' % self.name
        path = urllib.quote(path) + '?acl'
        response = self.connection.make_request('GET', path)
        body = response.read()
        if response.status == 200:
            policy = Policy(self)
            h = handler.XmlHandler(policy, self)
            xml.sax.parseString(body, h)
            return policy
        else:
            raise S3ResponseError(response.status, response.reason)

    def enable_logging(self, target_bucket, target_prefix=''):
        if isinstance(target_bucket, Bucket):
            target_bucket_name = target_bucket.name
        else:
            target_bucket_name = target_bucket
        path = '/%s' % self.name
        path = urllib.quote(path) + '?logging'
        body = self.BucketLoggingBody % (target_bucket_name, target_prefix)
        response = self.connection.make_request('PUT', path, data=body)
        body = response.read()
        if response.status == 200:
            return body
        else:
            raise S3ResponseError(response.status, response.reason)
        
    def disable_logging(self):
        path = '/%s' % self.name
        path = urllib.quote(path) + '?logging'
        body = self.EmptyBucketLoggingBody
        response = self.connection.make_request('PUT', path, data=body)
        body = response.read()
        if response.status == 200:
            return body
        else:
            raise S3ResponseError(response.status, response.reason)
        
    def get_logging_status(self):
        path = '/%s' % self.name
        path = urllib.quote(path) + '?logging'
        response = self.connection.make_request('GET', path)
        body = response.read()
        if response.status == 200:
            return body
        else:
            raise S3ResponseError(response.status, response.reason)

    def set_as_logging_target(self):
        policy = self.get_acl()
        g1 = Grant(permission='WRITE', type='Group', uri=self.LoggingGroup)
        g2 = Grant(permission='READ_ACP', type='Group', uri=self.LoggingGroup)
        policy.acl.add_grant(g1)
        policy.acl.add_grant(g2)
        self.set_acl(policy)
