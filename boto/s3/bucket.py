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

import boto
from boto import handler
from boto.resultset import ResultSet
from boto.s3.acl import Policy, CannedACLStrings, ACL, Grant
from boto.s3.user import User
from boto.s3.key import Key
from boto.s3.prefix import Prefix
from boto.exception import S3ResponseError, S3PermissionsError, S3CopyError
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

    BucketPaymentBody = """<?xml version="1.0" encoding="UTF-8"?>
       <RequestPaymentConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
         <Payer>%s</Payer>
       </RequestPaymentConfiguration>"""

    def __init__(self, connection=None, name=None, key_class=Key):
        self.name = name
        self.connection = connection
        self.key_class = key_class

    def __repr__(self):
        return '<Bucket: %s>' % self.name

    def __iter__(self):
        return iter(BucketListResultSet(self))

    def __contains__(self, key_name):
       return not (self.get_key(key_name) is None)

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
        
        :type key_class: class
        :param key_class: A subclass of Key that can be more specific
        """
        self.key_class = key_class

    def lookup(self, key_name, headers=None):
        """
        Deprecated: Please use get_key method.
        
        :type key_name: string
        :param key_name: The name of the key to retrieve
        
        :rtype: :class:`boto.s3.key.Key`
        :returns: A Key object from this bucket.
        """
        return self.get_key(key_name, headers=headers)
        
    def get_key(self, key_name, headers=None):
        """
        Check to see if a particular key exists within the bucket.  This
        method uses a HEAD request to check for the existance of the key.
        Returns: An instance of a Key object or None
        
        :type key_name: string
        :param key_name: The name of the key to retrieve
        
        :rtype: :class:`boto.s3.key.Key`
        :returns: A Key object from this bucket.
        """
        response = self.connection.make_request('HEAD', self.name, key_name, headers=headers)
        if response.status == 200:
            body = response.read()
            k = self.key_class(self)
            k.metadata = boto.utils.get_aws_metadata(response.msg)
            k.etag = response.getheader('etag')
            k.content_type = response.getheader('content-type')
            k.content_encoding = response.getheader('content-encoding')
            k.last_modified = response.getheader('last-modified')
            k.size = int(response.getheader('content-length'))
            k.name = key_name
            return k
        else:
            if response.status == 404:
                body = response.read()
                return None
            else:
                raise S3ResponseError(response.status, response.reason, '')

    def list(self, prefix='', delimiter='', marker='', headers=None):
        """
        List key objects within a bucket.  This returns an instance of an
        BucketListResultSet that automatically handles all of the result
        paging, etc. from S3.  You just need to keep iterating until
        there are no more results.
        Called with no arguments, this will return an iterator object across
        all keys within the bucket.
        
        :type prefix: string
        :param prefix: allows you to limit the listing to a particular
                        prefix.  For example, if you call the method with prefix='/foo/'
                        then the iterator will only cycle through the keys that begin with
                        the string '/foo/'.
                        
        :type delimiter: string
        :param delimiter: can be used in conjunction with the prefix
                        to allow you to organize and browse your keys hierarchically. See:
                        http://docs.amazonwebservices.com/AmazonS3/2006-03-01/
                        for more details.
                        
        :type marker: string
        :param marker: The "marker" of where you are in the result set
        
        :rtype: :class:`boto.s3.bucketlistresultset.BucketListResultSet`
        :return: an instance of a BucketListResultSet that handles paging, etc
        """
        return BucketListResultSet(self, prefix, delimiter, marker, headers)

    def get_all_keys(self, headers=None, **params):
        """
        A lower-level method for listing contents of a bucket.  This closely models the actual S3
        API and requires you to manually handle the paging of results.  For a higher-level method
        that handles the details of paging for you, you can use the list method.
        
        :type maxkeys: int
        :param maxkeys: The maximum number of keys to retrieve
        
        :type prefix: string
        :param prefix: The prefix of the keys you want to retrieve
        
        :type marker: string
        :param marker: The "marker" of where you are in the result set
        
        :type delimiter: string 
        :param delimiter: "If this optional, Unicode string parameter is included with your request, then keys that contain the same string between the prefix and the first occurrence of the delimiter will be rolled up into a single result element in the CommonPrefixes collection. These rolled-up keys are not returned elsewhere in the response."

        :rtype: ResultSet
        :return: The result from S3 listing the keys requested
        
        """
        l = []
        for k,v in params.items():
            if  k == 'maxkeys':
                k = 'max-keys'
            if isinstance(v, unicode):
                v = v.encode('utf-8')
            if v is not None:
                l.append('%s=%s' % (urllib.quote(k), urllib.quote(str(v))))
        if len(l):
            s = '&'.join(l)
        else:
            s = None
        response = self.connection.make_request('GET', self.name,
                headers=headers, query_args=s)
        body = response.read()
        boto.log.debug(body)
        if response.status == 200:
            rs = ResultSet([('Contents', self.key_class),
                            ('CommonPrefixes', Prefix)])
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def new_key(self, key_name=None):
        """
        Creates a new key
        
        :type key_name: string
        :param key_name: The name of the key to create
        
        :rtype: :class:`boto.s3.key.Key` or subclass
        :returns: An instance of the newly created key object
        """
        return self.key_class(self, key_name)

    def generate_url(self, expires_in, method='GET', headers=None, force_http=False):
        return self.connection.generate_url(expires_in, method, self.name, headers=headers,
                                            force_http=force_http)

    def delete_key(self, key_name, headers=None):
        """
        Deletes a key from the bucket.
        
        :type key_name: string
        :param key_name: The key name to delete
        """
        response = self.connection.make_request('DELETE', self.name, key_name, headers=headers)
        body = response.read()
        if response.status != 204:
            raise S3ResponseError(response.status, response.reason, body)

    def copy_key(self, new_key_name, src_bucket_name, src_key_name, metadata=None):
        """
        Create a new key in the bucket by copying another existing key.

        :type new_key_name: string
        :param new_key_name: The name of the new key

        :type src_bucket_name: string
        :param src_bucket_name: The name of the source bucket

        :type src_key_name: string
        :param src_key_name: The name of the source key

        :type metadata: dict
        :param metadata: Metadata to be associated with new key.
                         If metadata is supplied, it will replace the
                         metadata of the source key being copied.
                         If no metadata is supplied, the source key's
                         metadata will be copied to the new key.

        :rtype: :class:`boto.s3.key.Key` or subclass
        :returns: An instance of the newly created key object
        """
        src = '%s/%s' % (src_bucket_name, urllib.quote(src_key_name))
        if metadata:
            headers = {'x-amz-copy-source' : src,
                       'x-amz-metadata-directive' : 'REPLACE'}
            headers = boto.utils.merge_meta(headers, metadata)
        else:
            headers = {'x-amz-copy-source' : src,
                       'x-amz-metadata-directive' : 'COPY'}
        response = self.connection.make_request('PUT', self.name, new_key_name,
                                                headers=headers)
        body = response.read()
        if response.status == 200:
            key = self.new_key(new_key_name)
            h = handler.XmlHandler(key, self)
            xml.sax.parseString(body, h)
            if hasattr(key, 'Error'):
                raise S3CopyError(key.Code, key.Message, body)
            return key
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def set_canned_acl(self, acl_str, key_name='', headers=None):
        assert acl_str in CannedACLStrings

        if headers:
            headers['x-amz-acl'] = acl_str
        else:
            headers={'x-amz-acl': acl_str}

        response = self.connection.make_request('PUT', self.name, key_name,
                headers=headers, query_args='acl')
        body = response.read()
        if response.status != 200:
            raise S3ResponseError(response.status, response.reason, body)

    def get_xml_acl(self, key_name='', headers=None):
        response = self.connection.make_request('GET', self.name, key_name,
                                                query_args='acl', headers=headers)
        body = response.read()
        if response.status != 200:
            raise S3ResponseError(response.status, response.reason, body)
        return body

    def set_xml_acl(self, acl_str, key_name='', headers=None):
        response = self.connection.make_request('PUT', self.name, key_name,
                data=acl_str, query_args='acl', headers=headers)
        body = response.read()
        if response.status != 200:
            raise S3ResponseError(response.status, response.reason, body)

    def set_acl(self, acl_or_str, key_name='', headers=None):
        if isinstance(acl_or_str, Policy):
            self.set_xml_acl(acl_or_str.to_xml(), key_name, headers=headers)
        else:
            self.set_canned_acl(acl_or_str, key_name, headers=headers)

    def get_acl(self, key_name='', headers=None):
        response = self.connection.make_request('GET', self.name, key_name,
                query_args='acl', headers=headers)
        body = response.read()
        if response.status == 200:
            policy = Policy(self)
            h = handler.XmlHandler(policy, self)
            xml.sax.parseString(body, h)
            return policy
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def make_public(self, recursive=False, headers=None):
        self.set_canned_acl('public-read', headers=headers)
        if recursive:
            for key in self:
                self.set_canned_acl('public-read', key.name, headers=headers)

    def add_email_grant(self, permission, email_address, recursive=False, headers=None):
        """
        Convenience method that provides a quick way to add an email grant to a bucket.
        This method retrieves the current ACL, creates a new grant based on the parameters
        passed in, adds that grant to the ACL and then PUT's the new ACL back to S3.
        
        :param permission: The permission being granted. Should be one of: (READ, WRITE, READ_ACP, WRITE_ACP, FULL_CONTROL).
             See http://docs.amazonwebservices.com/AmazonS3/2006-03-01/UsingAuthAccess.html for more details on permissions.
        :type permission: string
        
        :param email_address: The email address associated with the AWS account your are granting
            the permission to.
        :type email_address: string
        
        :param recursive: A boolean value to controls whether the command will apply the
            grant to all keys within the bucket or not.  The default value is False.
            By passing a True value, the call will iterate through all keys in the
            bucket and apply the same grant to each key.
            CAUTION: If you have a lot of keys, this could take a long time!
        :type recursive: boolean
        """
        if permission not in S3Permissions:
            raise S3PermissionsError('Unknown Permission: %s' % permission)
        policy = self.get_acl(headers=headers)
        policy.acl.add_email_grant(permission, email_address)
        self.set_acl(policy, headers=headers)
        if recursive:
            for key in self:
                key.add_email_grant(permission, email_address, headers=headers)

    def add_user_grant(self, permission, user_id, recursive=False, headers=None):
        """
        Convenience method that provides a quick way to add a canonical user grant to a bucket.
        This method retrieves the current ACL, creates a new grant based on the parameters
        passed in, adds that grant to the ACL and then PUT's the new ACL back to S3.
        
        :type permission: string
        :param permission:  The permission being granted.  Should be one of:
                            READ|WRITE|READ_ACP|WRITE_ACP|FULL_CONTROL
                            See http://docs.amazonwebservices.com/AmazonS3/2006-03-01/UsingAuthAccess.html
                            for more details on permissions.
                            
        :type user_id: string
        :param user_id:     The canonical user id associated with the AWS account your are granting
                            the permission to.
                            
        :type recursive: bool
        :param recursive:   A boolean value that controls whether the command will apply the
                            grant to all keys within the bucket or not.  The default value is False.
                            By passing a True value, the call will iterate through all keys in the
                            bucket and apply the same grant to each key.
                            CAUTION: If you have a lot of keys, this could take a long time!
        """
        if permission not in S3Permissions:
            raise S3PermissionsError('Unknown Permission: %s' % permission)
        policy = self.get_acl(headers=headers)
        policy.acl.add_user_grant(permission, user_id)
        self.set_acl(policy, headers=headers)
        if recursive:
            for key in self:
                key.add_user_grant(permission, user_id, headers=headers)

    def list_grants(self, headers=None):
        policy = self.get_acl(headers=headers)
        return policy.acl.grants

    def get_location(self):
        """
        Returns the LocationConstraint for the bucket.

        :rtype: str
        :return: The LocationConstraint for the bucket or the empty string if
                 no constraint was specified when bucket was created.
        """
        response = self.connection.make_request('GET', self.name,
                                                query_args='location')
        body = response.read()
        if response.status == 200:
            rs = ResultSet(self)
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs.LocationConstraint
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def enable_logging(self, target_bucket, target_prefix='', headers=None):
        if isinstance(target_bucket, Bucket):
            target_bucket = target_bucket.name
        body = self.BucketLoggingBody % (target_bucket, target_prefix)
        response = self.connection.make_request('PUT', self.name, data=body,
                query_args='logging', headers=headers)
        body = response.read()
        if response.status == 200:
            return True
        else:
            raise S3ResponseError(response.status, response.reason, body)
        
    def disable_logging(self, headers=None):
        body = self.EmptyBucketLoggingBody
        response = self.connection.make_request('PUT', self.name, data=body,
                query_args='logging', headers=headers)
        body = response.read()
        if response.status == 200:
            return True
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def get_logging_status(self, headers=None):
        response = self.connection.make_request('GET', self.name,
                query_args='logging', headers=headers)
        body = response.read()
        if response.status == 200:
            return body
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def set_as_logging_target(self, headers=None):
        policy = self.get_acl(headers=headers)
        g1 = Grant(permission='WRITE', type='Group', uri=self.LoggingGroup)
        g2 = Grant(permission='READ_ACP', type='Group', uri=self.LoggingGroup)
        policy.acl.add_grant(g1)
        policy.acl.add_grant(g2)
        self.set_acl(policy, headers=headers)

    def disable_logging(self, headers=None):
        body = self.EmptyBucketLoggingBody
        response = self.connection.make_request('PUT', self.name, data=body,
                query_args='logging', headers=headers)
        body = response.read()
        if response.status == 200:
            return True
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def get_request_payment(self, headers=None):
        response = self.connection.make_request('GET', self.name,
                query_args='requestPayment', headers=headers)
        body = response.read()
        if response.status == 200:
            return body
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def set_request_payment(self, payer='BucketOwner', headers=None):
        body = self.BucketPaymentBody % payer
        response = self.connection.make_request('PUT', self.name, data=body,
                query_args='requestPayment', headers=headers)
        body = response.read()
        if response.status == 200:
            return True
        else:
            raise S3ResponseError(response.status, response.reason, body)
        
    def delete(self, headers=None):
        return self.connection.delete_bucket(self.name, headers=headers)
