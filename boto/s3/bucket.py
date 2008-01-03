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
from boto.s3.prefix import Prefix
from boto.exception import S3ResponseError, S3PermissionsError
from boto.s3.bucketlistresultset import BucketListResultSet
import boto.utils
import xml.sax
import urllib

S3Permissions = ['READ', 'WRITE', 'READ_ACP', 'WRITE_ACP', 'FULL_CONTROL']

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

    def __init__(self, connection=None, name=None, key_class=Key):
        self.name = name
        self.connection = connection
        self.key_class = key_class

    def __iter__(self):
        return iter(BucketListResultSet(self))

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'Name':
            self.name = value
        elif name == 'CreationDate':
            self.creation_date = value
        else:
            setattr(self, name, value)

    def set_key_class(self, key_class):
        """
        Set the Key class associated with this bucket.  By default, this
        would be the boto.s3.key.Key class but if you want to subclass that
        for some reason this allows you to associate your new class with a
        bucket so that when you call bucket.new_key() or when you get a listing
        of keys in the bucket you will get an instances of your key class
        rather than the default.
        """
        self.key_class = key_class

    def lookup(self, key_name):
        """
        Deprecated: Please use get_key method.
        """
        return self.get_key(key_name)
        
    def get_key(self, key_name):
        """
        Check to see if a particular key exists within the bucket.  This
        method uses a HEAD request to check for the existance of the key.
        Returns: An instance of a Key object or None
        """
        path = '/%s/%s' % (self.name, key_name)
        response = self.connection.make_request('HEAD', urllib.quote(path))
        if response.status == 200:
            body = response.read()
            k = self.key_class(self)
            k.metadata = boto.utils.get_aws_metadata(response.msg)
            k.etag = response.getheader('etag')
            k.content_type = response.getheader('content-type')
            k.last_modified = response.getheader('last-modified')
            k.size = response.getheader('content-length')
            k.name = key_name
            return k
        else:
            # -- gross hack --
            # httplib gets confused with chunked responses to HEAD requests
            # so I have to fake it out
            response.chunked = 0
            body = response.read()
            return None

    def list(self, prefix="", delimiter=""):
        """
        List key objects within a bucket.  This returns an instance of an
        BucketListResultSet that automatically handles all of the result
        paging, etc. from S3.  You just need to keep iterating until
        there are no more results.
        Called with no arguments, this will return an iterator object across
        all keys within the bucket.
        The prefix parameter allows you to limit the listing to a particular
        prefix.  For example, if you call the method with prefix='/foo/'
        then the iterator will only cycle through the keys that begin with
        the string '/foo/'.
        The delimiter parameter can be used in conjunction with the prefix
        to allow you to organize and browse your keys hierarchically. See:
        http://docs.amazonwebservices.com/AmazonS3/2006-03-01/
        for more details.
        """
        return BucketListResultSet(self, prefix, delimiter)

    def get_all_keys(self, headers=None, **params):
        """
        Deprecated: This is better handled now by list method.
        
        params can be one of: prefix, marker, max-keys, delimiter
        as defined in S3 Developer's Guide, however since max-keys is not
        a legal variable in Python you have to pass maxkeys and this
        method will munge it (Ugh!)
        """
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
        if self.connection.debug > 1:
            print body
        if response.status == 200:
            rs = ResultSet([('Contents', self.key_class),
                            ('CommonPrefixes', Prefix)])
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def new_key(self, key_name=None):
        return self.key_class(self, key_name)

    def generate_url(self, expires_in, method='GET', headers=None):
        return self.connection.generate_url(expires_in, method,
                                            '/'+self.name, headers)

    def delete_key(self, key_name):
        # for backward compatibility, previous version expected a Key object
        if isinstance(key_name, self.key_class):
            key_name = key_name.name
        path = '/%s/%s' % (self.name, key_name)
        response = self.connection.make_request('DELETE',
                                                urllib.quote(path))
        body = response.read()
        if response.status != 204:
            raise S3ResponseError(response.status, response.reason, body)

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
            raise S3ResponseError(response.status, response.reason, body)

    def set_xml_acl(self, acl_str, key_name=None):
        if key_name:
            path = '/%s/%s' % (self.name, key_name)
        else:
            path = '/%s' % self.name
        path = urllib.quote(path) + '?acl'
        response = self.connection.make_request('PUT', path, data=acl_str)
        body = response.read()
        if response.status != 200:
            raise S3ResponseError(response.status, response.reason, body)

    def set_acl(self, acl_or_str, key_name=None):
        # just in case user passes a Key object rather than key name
        if isinstance(key_name, self.key_class):
            key_name = key_name.name
        if isinstance(acl_or_str, Policy):
            self.set_xml_acl(acl_or_str.to_xml(), key_name)
        else:
            self.set_canned_acl(acl_or_str, key_name)
            
    def get_acl(self, key_name=None):
        # just in case user passes a Key object rather than key name
        if isinstance(key_name, self.key_class):
            key_name = key_name.name
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
            raise S3ResponseError(response.status, response.reason, body)

    def add_email_grant(self, permission, email_address, recursive=False):
        """
        Convenience method that provides a quick way to add an email grant to a bucket.
        This method retrieves the current ACL, creates a new grant based on the parameters
        passed in, adds that grant to the ACL and then PUT's the new ACL back to S3.
        Inputs:
            permission - The permission being granted.  Should be one of:
                         READ|WRITE|READ_ACP|WRITE_ACP|FULL_CONTROL
                         See http://docs.amazonwebservices.com/AmazonS3/2006-03-01/UsingAuthAccess.html
                         for more details on permissions.
            email_address - The email address associated with the AWS account your are granting
                            the permission to.
            recursive - A boolean value to controls whether the command will apply the
                        grant to all keys within the bucket or not.  The default value is False.
                        By passing a True value, the call will iterate through all keys in the
                        bucket and apply the same grant to each key.
                        CAUTION: If you have a lot of keys, this could take a long time!
        Returns:
            Nothing
        """
        if permission not in S3Permissions:
            raise S3PermissionsError('Unknown Permission: %s' % permission)
        policy = self.get_acl()
        policy.acl.add_email_grant(permission, email_address)
        self.set_acl(policy)
        if recursive:
            for key in self:
                key.add_email_grant(permission, email_address)

    def add_user_grant(self, permission, user_id, recursive=False):
        """
        Convenience method that provides a quick way to add a canonical user grant to a bucket.
        This method retrieves the current ACL, creates a new grant based on the parameters
        passed in, adds that grant to the ACL and then PUT's the new ACL back to S3.
        Inputs:
            permission - The permission being granted.  Should be one of:
                         READ|WRITE|READ_ACP|WRITE_ACP|FULL_CONTROL
                         See http://docs.amazonwebservices.com/AmazonS3/2006-03-01/UsingAuthAccess.html
                         for more details on permissions.
            user_id - The canonical user id associated with the AWS account your are granting
                      the permission to.
            recursive - A boolean value to controls whether the command will apply the
                        grant to all keys within the bucket or not.  The default value is False.
                        By passing a True value, the call will iterate through all keys in the
                        bucket and apply the same grant to each key.
                        CAUTION: If you have a lot of keys, this could take a long time!
        Returns:
            Nothing
        """
        if permission not in S3Permissions:
            raise S3PermissionsError('Unknown Permission: %s' % permission)
        policy = self.get_acl()
        policy.acl.add_user_grant(permission, user_id)
        self.set_acl(policy)
        if recursive:
            for key in self:
                key.add_user_grant(permission, user_id)

    def list_grants(self):
        policy = self.get_acl()
        return policy.acl.grants()

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
            raise S3ResponseError(response.status, response.reason, body)
        
    def disable_logging(self):
        path = '/%s' % self.name
        path = urllib.quote(path) + '?logging'
        body = self.EmptyBucketLoggingBody
        response = self.connection.make_request('PUT', path, data=body)
        body = response.read()
        if response.status == 200:
            return body
        else:
            raise S3ResponseError(response.status, response.reason, body)
        
    def get_logging_status(self):
        path = '/%s' % self.name
        path = urllib.quote(path) + '?logging'
        response = self.connection.make_request('GET', path)
        body = response.read()
        if response.status == 200:
            return body
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def set_as_logging_target(self):
        policy = self.get_acl()
        g1 = Grant(permission='WRITE', type='Group', uri=self.LoggingGroup)
        g2 = Grant(permission='READ_ACP', type='Group', uri=self.LoggingGroup)
        policy.acl.add_grant(g1)
        policy.acl.add_grant(g2)
        self.set_acl(policy)
