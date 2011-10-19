# Copyright 2010 Google Inc.
# Copyright (c) 2011, Nexenta Systems Inc.
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
import os
from boto.exception import BotoClientError
from boto.exception import InvalidUriError


class StorageUri(object):
    """
    Base class for representing storage provider-independent bucket and
    object name with a shorthand URI-like syntax.

    This is an abstract class: the constructor cannot be called (throws an
    exception if you try).
    """

    connection = None
    # Optional args that can be set from one of the concrete subclass
    # constructors, to change connection behavior (e.g., to override
    # https_connection_factory).
    connection_args = None

    def __init__(self):
        """Uncallable constructor on abstract base StorageUri class.
        """
        raise BotoClientError('Attempt to instantiate abstract StorageUri '
                              'class')

    def __repr__(self):
        """Returns string representation of URI."""
        return self.uri

    def equals(self, uri):
        """Returns true if two URIs are equal."""
        return self.uri == uri.uri

    def check_response(self, resp, level, uri):
        if resp is None:
            raise InvalidUriError('Attempt to get %s for "%s" failed. This '
                                  'probably indicates the URI is invalid' %
                                  (level, uri))

    def connect(self, access_key_id=None, secret_access_key=None, **kwargs):
        """
        Opens a connection to appropriate provider, depending on provider
        portion of URI. Requires Credentials defined in boto config file (see
        boto/pyami/config.py).
        @type storage_uri: StorageUri
        @param storage_uri: StorageUri specifying a bucket or a bucket+object
        @rtype: L{AWSAuthConnection<boto.gs.connection.AWSAuthConnection>}
        @return: A connection to storage service provider of the given URI.
        """

        connection_args = dict(self.connection_args or ())
        # Use OrdinaryCallingFormat instead of boto-default
        # SubdomainCallingFormat because the latter changes the hostname
        # that's checked during cert validation for HTTPS connections,
        # which will fail cert validation (when cert validation is enabled).
        # Note: the following import can't be moved up to the start of
        # this file else it causes a config import failure when run from
        # the resumable upload/download tests.
        from boto.s3.connection import OrdinaryCallingFormat
        connection_args['calling_format'] = OrdinaryCallingFormat()
        connection_args.update(kwargs)
        if not self.connection:
            if self.scheme == 's3':
                from boto.s3.connection import S3Connection
                self.connection = S3Connection(access_key_id,
                                               secret_access_key,
                                               **connection_args)
            elif self.scheme == 'gs':
                from boto.gs.connection import GSConnection
                self.connection = GSConnection(access_key_id,
                                               secret_access_key,
                                               **connection_args)
            elif self.scheme == 'file':
                from boto.file.connection import FileConnection
                self.connection = FileConnection(self)
            else:
                raise InvalidUriError('Unrecognized scheme "%s"' %
                                      self.scheme)
        self.connection.debug = self.debug
        return self.connection

    def delete_key(self, validate=True, headers=None, version_id=None,
                   mfa_token=None):
        if not self.object_name:
            raise InvalidUriError('delete_key on object-less URI (%s)' %
                                  self.uri)
        bucket = self.get_bucket(validate, headers)
        return bucket.delete_key(self.object_name, headers, version_id,
                                 mfa_token)

    def get_all_keys(self, validate=True, headers=None):
        bucket = self.get_bucket(validate, headers)
        return bucket.get_all_keys(headers)

    def get_bucket(self, validate=True, headers=None):
        if self.bucket_name is None:
            raise InvalidUriError('get_bucket on bucket-less URI (%s)' %
                                  self.uri)
        conn = self.connect()
        bucket = conn.get_bucket(self.bucket_name, validate, headers)
        self.check_response(bucket, 'bucket', self.uri)
        return bucket

    def get_key(self, validate=True, headers=None, version_id=None):
        if not self.object_name:
            raise InvalidUriError('get_key on object-less URI (%s)' % self.uri)
        bucket = self.get_bucket(validate, headers)
        key = bucket.get_key(self.object_name, headers, version_id)
        self.check_response(key, 'key', self.uri)
        return key

    def new_key(self, validate=True, headers=None):
        if not self.object_name:
            raise InvalidUriError('new_key on object-less URI (%s)' % self.uri)
        bucket = self.get_bucket(validate, headers)
        return bucket.new_key(self.object_name)

    def get_contents_as_string(self, validate=True, headers=None, cb=None,
                               num_cb=10, torrent=False, version_id=None):
        if not self.object_name:
            raise InvalidUriError('get_contents_as_string on object-less URI '
                                  '(%s)' % self.uri)
        key = self.get_key(validate, headers)
        self.check_response(key, 'key', self.uri)
        return key.get_contents_as_string(headers, cb, num_cb, torrent,
                                          version_id)

    def acl_class(self):
        if self.bucket_name is None:
            raise InvalidUriError('acl_class on bucket-less URI (%s)' %
                                  self.uri)
        conn = self.connect()
        acl_class = conn.provider.acl_class
        self.check_response(acl_class, 'acl_class', self.uri)
        return acl_class

    def canned_acls(self):
        if self.bucket_name is None:
            raise InvalidUriError('canned_acls on bucket-less URI (%s)' %
                                  self.uri)
        conn = self.connect()
        canned_acls = conn.provider.canned_acls
        self.check_response(canned_acls, 'canned_acls', self.uri)
        return canned_acls


class BucketStorageUri(StorageUri):
    """
    StorageUri subclass that handles bucket storage providers.
    Callers should instantiate this class by calling boto.storage_uri().
    """

    def __init__(self, scheme, bucket_name=None, object_name=None,
                 debug=0, connection_args=None):
        """Instantiate a BucketStorageUri from scheme,bucket,object tuple.

        @type scheme: string
        @param scheme: URI scheme naming the storage provider (gs, s3, etc.)
        @type bucket_name: string
        @param bucket_name: bucket name
        @type object_name: string
        @param object_name: object name
        @type debug: int
        @param debug: debug level to pass in to connection (range 0..2)
        @type connection_args: map
        @param connection_args: optional map containing args to be
            passed to {S3,GS}Connection constructor (e.g., to override
            https_connection_factory).

        After instantiation the components are available in the following
        fields: uri, scheme, bucket_name, object_name.
        """

        self.scheme = scheme
        self.bucket_name = bucket_name
        self.object_name = object_name
        if connection_args:
            self.connection_args = connection_args
        if self.bucket_name and self.object_name:
            self.uri = ('%s://%s/%s' % (self.scheme, self.bucket_name,
                                        self.object_name))
        elif self.bucket_name:
            self.uri = ('%s://%s/' % (self.scheme, self.bucket_name))
        else:
            self.uri = ('%s://' % self.scheme)
        self.debug = debug

    def clone_replace_name(self, new_name):
        """Instantiate a BucketStorageUri from the current BucketStorageUri,
        but replacing the object_name.

        @type new_name: string
        @param new_name: new object name
        """
        if not self.bucket_name:
            raise InvalidUriError('clone_replace_name() on bucket-less URI %s' %
                                  self.uri)
        return BucketStorageUri(self.scheme, self.bucket_name, new_name,
                                self.debug)

    def get_acl(self, validate=True, headers=None, version_id=None):
        if not self.bucket_name:
            raise InvalidUriError('get_acl on bucket-less URI (%s)' % self.uri)
        bucket = self.get_bucket(validate, headers)
        # This works for both bucket- and object- level ACLs (former passes
        # key_name=None):
        acl = bucket.get_acl(self.object_name, headers, version_id)
        self.check_response(acl, 'acl', self.uri)
        return acl

    def get_location(self, validate=True, headers=None):
        if not self.bucket_name:
            raise InvalidUriError('get_location on bucket-less URI (%s)' %
                                  self.uri)
        bucket = self.get_bucket(validate, headers)
        return bucket.get_location()

    def get_subresource(self, subresource, validate=True, headers=None,
                        version_id=None):
        if not self.bucket_name:
            raise InvalidUriError(
                'get_subresource on bucket-less URI (%s)' % self.uri)
        bucket = self.get_bucket(validate, headers)
        return bucket.get_subresource(subresource, self.object_name, headers,
                                      version_id)

    def add_group_email_grant(self, permission, email_address, recursive=False,
                              validate=True, headers=None):
        if self.scheme != 'gs':
              raise ValueError('add_group_email_grant() not supported for %s '
                               'URIs.' % self.scheme)
        if self.object_name:
            if recursive:
              raise ValueError('add_group_email_grant() on key-ful URI cannot '
                               'specify recursive=True')
            key = self.get_key(validate, headers)
            self.check_response(key, 'key', self.uri)
            key.add_group_email_grant(permission, email_address, headers)
        elif self.bucket_name:
            bucket = self.get_bucket(validate, headers)
            bucket.add_group_email_grant(permission, email_address, recursive,
                                         headers)
        else:
            raise InvalidUriError('add_group_email_grant() on bucket-less URI %s' %
                                  self.uri)

    def add_email_grant(self, permission, email_address, recursive=False,
                        validate=True, headers=None):
        if not self.bucket_name:
            raise InvalidUriError('add_email_grant on bucket-less URI (%s)' %
                                  self.uri)
        if not self.object_name:
            bucket = self.get_bucket(validate, headers)
            bucket.add_email_grant(permission, email_address, recursive,
                                   headers)
        else:
            key = self.get_key(validate, headers)
            self.check_response(key, 'key', self.uri)
            key.add_email_grant(permission, email_address)

    def add_user_grant(self, permission, user_id, recursive=False,
                       validate=True, headers=None):
        if not self.bucket_name:
            raise InvalidUriError('add_user_grant on bucket-less URI (%s)' %
                                  self.uri)
        if not self.object_name:
            bucket = self.get_bucket(validate, headers)
            bucket.add_user_grant(permission, user_id, recursive, headers)
        else:
            key = self.get_key(validate, headers)
            self.check_response(key, 'key', self.uri)
            key.add_user_grant(permission, user_id)

    def list_grants(self, headers=None):
        if not self.bucket_name:
            raise InvalidUriError('list_grants on bucket-less URI (%s)' %
                                  self.uri)
        bucket = self.get_bucket(headers)
        return bucket.list_grants(headers)

    def names_container(self):
        """Returns True if this URI names a bucket (vs. an object).
        """
        return not self.object_name

    def names_singleton(self):
        """Returns True if this URI names an object (vs. a bucket).
        """
        return self.object_name

    def is_file_uri(self):
        return False

    def is_cloud_uri(self):
        return True

    def create_bucket(self, headers=None, location='', policy=None):
        if self.bucket_name is None:
            raise InvalidUriError('create_bucket on bucket-less URI (%s)' %
                                  self.uri)
        conn = self.connect()
        return conn.create_bucket(self.bucket_name, headers, location, policy)

    def delete_bucket(self, headers=None):
        if self.bucket_name is None:
            raise InvalidUriError('delete_bucket on bucket-less URI (%s)' %
                                  self.uri)
        conn = self.connect()
        return conn.delete_bucket(self.bucket_name, headers)

    def get_all_buckets(self, headers=None):
        conn = self.connect()
        return conn.get_all_buckets(headers)

    def get_provider(self):
        conn = self.connect()
        provider = conn.provider
        self.check_response(provider, 'provider', self.uri)
        return provider

    def set_acl(self, acl_or_str, key_name='', validate=True, headers=None,
                version_id=None):
        if not self.bucket_name:
            raise InvalidUriError('set_acl on bucket-less URI (%s)' %
                                  self.uri)
        self.get_bucket(validate, headers).set_acl(acl_or_str, key_name,
                                                   headers, version_id)

    def set_canned_acl(self, acl_str, validate=True, headers=None,
                       version_id=None):
        if not self.object_name:
            raise InvalidUriError('set_canned_acl on object-less URI (%s)' %
                                  self.uri)
        key = self.get_key(validate, headers)
        self.check_response(key, 'key', self.uri)
        key.set_canned_acl(acl_str, headers, version_id)

    def set_subresource(self, subresource, value, validate=True, headers=None,
                        version_id=None):
        if not self.bucket_name:
            raise InvalidUriError(
                'set_subresource on bucket-less URI (%s)' % self.uri)
        bucket = self.get_bucket(validate, headers)
        bucket.set_subresource(subresource, value, self.object_name, headers,
                               version_id)

    def set_contents_from_string(self, s, headers=None, replace=True,
                                 cb=None, num_cb=10, policy=None, md5=None,
                                 reduced_redundancy=False):
        key = self.new_key(headers=headers)
        key.set_contents_from_string(s, headers, replace, cb, num_cb, policy,
                                     md5, reduced_redundancy)

    def enable_logging(self, target_bucket, target_prefix=None,
                       canned_acl=None, validate=True, headers=None,
                       version_id=None):
        if not self.bucket_name:
            raise InvalidUriError(
                'disable_logging on bucket-less URI (%s)' % self.uri)
        bucket = self.get_bucket(validate, headers)
        bucket.enable_logging(target_bucket, target_prefix, headers=headers,
                              canned_acl=canned_acl)

    def disable_logging(self, validate=True, headers=None, version_id=None):
        if not self.bucket_name:
            raise InvalidUriError(
                'disable_logging on bucket-less URI (%s)' % self.uri)
        bucket = self.get_bucket(validate, headers)
        bucket.disable_logging(headers=headers)



class FileStorageUri(StorageUri):
    """
    StorageUri subclass that handles files in the local file system.
    Callers should instantiate this class by calling boto.storage_uri().

    See file/README about how we map StorageUri operations onto a file system.
    """

    def __init__(self, object_name, debug, is_stream=False):
        """Instantiate a FileStorageUri from a path name.

        @type object_name: string
        @param object_name: object name
        @type debug: boolean
        @param debug: whether to enable debugging on this StorageUri

        After instantiation the components are available in the following
        fields: uri, scheme, bucket_name (always blank for this "anonymous"
        bucket), object_name.
        """

        self.scheme = 'file'
        self.bucket_name = ''
        self.object_name = object_name
        self.uri = 'file://' + object_name
        self.debug = debug
        self.stream = is_stream

    def clone_replace_name(self, new_name):
        """Instantiate a FileStorageUri from the current FileStorageUri,
        but replacing the object_name.

        @type new_name: string
        @param new_name: new object name
        """
        return FileStorageUri(new_name, self.debug, self.stream)

    def names_container(self):
        """Returns True if this URI is not representing input/output stream
        and names a directory.
        """
        if not self.stream:
            return os.path.isdir(self.object_name)
        else:
            return False

    def names_singleton(self):
        """Returns True if this URI names a file or
        if URI represents input/output stream.
        """
        if self.stream:
            return True
        else:
            return os.path.isfile(self.object_name)

    def is_file_uri(self):
        return True

    def is_cloud_uri(self):
        return False

    def is_stream(self):
        """Retruns True if this URI represents input/output stream.
        """
        return self.stream
