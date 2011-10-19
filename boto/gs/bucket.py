# Copyright 2010 Google Inc.
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
from boto.exception import InvalidAclError
from boto.gs.acl import ACL, CannedACLStrings
from boto.gs.acl import SupportedPermissions as GSPermissions
from boto.gs.key import Key as GSKey
from boto.s3.acl import Policy
from boto.s3.bucket import Bucket as S3Bucket
import xml.sax

class Bucket(S3Bucket):

    def __init__(self, connection=None, name=None, key_class=GSKey):
        super(Bucket, self).__init__(connection, name, key_class)

    def set_acl(self, acl_or_str, key_name='', headers=None, version_id=None):
        if isinstance(acl_or_str, Policy):
            raise InvalidAclError('Attempt to set S3 Policy on GS ACL')
        elif isinstance(acl_or_str, ACL):
            self.set_xml_acl(acl_or_str.to_xml(), key_name, headers=headers)
        else:
            self.set_canned_acl(acl_or_str, key_name, headers=headers)

    def get_acl(self, key_name='', headers=None, version_id=None):
        response = self.connection.make_request('GET', self.name, key_name,
                query_args='acl', headers=headers)
        body = response.read()
        if response.status == 200:
            acl = ACL(self)
            h = handler.XmlHandler(acl, self)
            xml.sax.parseString(body, h)
            return acl
        else:
            raise self.connection.provider.storage_response_error(
                response.status, response.reason, body)

    def set_canned_acl(self, acl_str, key_name='', headers=None,
                       version_id=None):
        assert acl_str in CannedACLStrings

        if headers:
            headers[self.connection.provider.acl_header] = acl_str
        else:
            headers={self.connection.provider.acl_header: acl_str}

        query_args='acl'
        if version_id:
            query_args += '&versionId=%s' % version_id
        response = self.connection.make_request('PUT', self.name, key_name,
                headers=headers, query_args=query_args)
        body = response.read()
        if response.status != 200:
            raise self.connection.provider.storage_response_error(
                response.status, response.reason, body)

    # Method with same signature as boto.s3.bucket.Bucket.add_email_grant(),
    # to allow polymorphic treatment at application layer.
    def add_email_grant(self, permission, email_address,
                        recursive=False, headers=None):
        """
        Convenience method that provides a quick way to add an email grant
        to a bucket. This method retrieves the current ACL, creates a new
        grant based on the parameters passed in, adds that grant to the ACL
        and then PUT's the new ACL back to GS.
        
        :type permission: string
        :param permission: The permission being granted. Should be one of:
                           (READ, WRITE, FULL_CONTROL).
        
        :type email_address: string
        :param email_address: The email address associated with the GS
                              account your are granting the permission to.
        
        :type recursive: boolean
        :param recursive: A boolean value to controls whether the call
                          will apply the grant to all keys within the bucket
                          or not.  The default value is False.  By passing a
                          True value, the call will iterate through all keys
                          in the bucket and apply the same grant to each key.
                          CAUTION: If you have a lot of keys, this could take
                          a long time!
        """
        if permission not in GSPermissions:
            raise self.connection.provider.storage_permissions_error(
                'Unknown Permission: %s' % permission)
        acl = self.get_acl(headers=headers)
        acl.add_email_grant(permission, email_address)
        self.set_acl(acl, headers=headers)
        if recursive:
            for key in self:
                key.add_email_grant(permission, email_address, headers=headers)

    # Method with same signature as boto.s3.bucket.Bucket.add_user_grant(),
    # to allow polymorphic treatment at application layer.
    def add_user_grant(self, permission, user_id, recursive=False, headers=None):
        """
        Convenience method that provides a quick way to add a canonical user grant to a bucket.
        This method retrieves the current ACL, creates a new grant based on the parameters
        passed in, adds that grant to the ACL and then PUTs the new ACL back to GS.
        
        :type permission: string
        :param permission:  The permission being granted.  Should be one of:
                            (READ|WRITE|FULL_CONTROL)
        
        :type user_id: string
        :param user_id:     The canonical user id associated with the GS account you are granting
                            the permission to.
                            
        :type recursive: bool
        :param recursive: A boolean value to controls whether the call
                          will apply the grant to all keys within the bucket
                          or not.  The default value is False.  By passing a
                          True value, the call will iterate through all keys
                          in the bucket and apply the same grant to each key.
                          CAUTION: If you have a lot of keys, this could take
                          a long time!
        """
        if permission not in GSPermissions:
            raise self.connection.provider.storage_permissions_error(
                'Unknown Permission: %s' % permission)
        acl = self.get_acl(headers=headers)
        acl.add_user_grant(permission, user_id)
        self.set_acl(acl, headers=headers)
        if recursive:
            for key in self:
                key.add_user_grant(permission, user_id, headers=headers)

    def add_group_email_grant(self, permission, email_address, recursive=False,
                              headers=None):
        """
        Convenience method that provides a quick way to add an email group
        grant to a bucket. This method retrieves the current ACL, creates a new
        grant based on the parameters passed in, adds that grant to the ACL and
        then PUT's the new ACL back to GS.

        :type permission: string
        :param permission: The permission being granted. Should be one of:
            READ|WRITE|FULL_CONTROL
            See http://code.google.com/apis/storage/docs/developer-guide.html#authorization
            for more details on permissions.

        :type email_address: string
        :param email_address: The email address associated with the Google
            Group to which you are granting the permission.

        :type recursive: bool
        :param recursive: A boolean value to controls whether the call
                          will apply the grant to all keys within the bucket
                          or not.  The default value is False.  By passing a
                          True value, the call will iterate through all keys
                          in the bucket and apply the same grant to each key.
                          CAUTION: If you have a lot of keys, this could take
                          a long time!
        """
        if permission not in GSPermissions:
            raise self.connection.provider.storage_permissions_error(
                'Unknown Permission: %s' % permission)
        acl = self.get_acl(headers=headers)
        acl.add_group_email_grant(permission, email_address)
        self.set_acl(acl, headers=headers)
        if recursive:
            for key in self:
                key.add_group_email_grant(permission, email_address,
                                          headers=headers)

    # Method with same input signature as boto.s3.bucket.Bucket.list_grants()
    # (but returning different object type), to allow polymorphic treatment
    # at application layer.
    def list_grants(self, headers=None):
        acl = self.get_acl(headers=headers)
        return acl.entries

    def disable_logging(self, headers=None):
        xml_str = '<?xml version="1.0" encoding="UTF-8"?><Logging/>'
        self.set_subresource('logging', xml_str, headers=headers)

    def enable_logging(self, target_bucket, target_prefix=None, headers=None,
                       canned_acl=None):
        if isinstance(target_bucket, Bucket):
            target_bucket = target_bucket.name
        xml_str = '<?xml version="1.0" encoding="UTF-8"?><Logging>'
        xml_str = (xml_str + '<LogBucket>%s</LogBucket>' % target_bucket)
        if target_prefix:
            xml_str = (xml_str +
                       '<LogObjectPrefix>%s</LogObjectPrefix>' % target_prefix)
        if canned_acl:
            xml_str = (xml_str +
                       '<PredefinedAcl>%s</PredefinedAcl>' % canned_acl)
        xml_str = xml_str + '</Logging>'

        self.set_subresource('logging', xml_str, headers=headers)
