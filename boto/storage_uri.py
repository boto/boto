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
import sys
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

    # Map of provider scheme ('s3' or 'gs') to AWSAuthConnection object. We
    # maintain a pool here in addition to the connection pool implemented
    # in AWSAuthConnection because the latter re-creates its connection pool
    # every time that class is instantiated (so the current pool is used to
    # avoid re-instantiating AWSAuthConnection).
    provider_pool = {}

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
            raise InvalidUriError('Attempt to get %s for "%s" failed.\nThis '
                                  'can happen if the URI refers to a non-'
                                  'existent object or if you meant to\noperate '
                                  'on a directory (e.g., leaving off -R option '
                                  'on gsutil cp, mv, or ls of a\nbucket)' %
                                  (level, uri))

    def _check_bucket_uri(self, function_name):
        if issubclass(type(self), BucketStorageUri) and not self.bucket_name:
            raise InvalidUriError(
                '%s on bucket-less URI (%s)' % (function_name, self.uri))

    def _check_object_uri(self, function_name):
        if issubclass(type(self), BucketStorageUri) and not self.object_name:
            raise InvalidUriError('%s on object-less URI (%s)' %
                                  (function_name, self.uri))

    def _warn_about_args(self, function_name, **args):
        for arg in args:
            if args[arg]:
                sys.stderr.write(
                        'Warning: %s ignores argument: %s=%s\n' %
                        (function_name, arg, str(args[arg])))

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
        if (hasattr(self, 'suppress_consec_slashes') and
            'suppress_consec_slashes' not in connection_args):
            connection_args['suppress_consec_slashes'] = (
                self.suppress_consec_slashes)
        connection_args.update(kwargs)
        if not self.connection:
            if self.scheme in self.provider_pool:
                self.connection = self.provider_pool[self.scheme]
            elif self.scheme == 's3':
                from boto.s3.connection import S3Connection
                self.connection = S3Connection(access_key_id,
                                               secret_access_key,
                                               **connection_args)
                self.provider_pool[self.scheme] = self.connection
            elif self.scheme == 'gs':
                from boto.gs.connection import GSConnection
                self.connection = GSConnection(access_key_id,
                                               secret_access_key,
                                               **connection_args)
                self.provider_pool[self.scheme] = self.connection
            elif self.scheme == 'file':
                from boto.file.connection import FileConnection
                self.connection = FileConnection(self)
            else:
                raise InvalidUriError('Unrecognized scheme "%s"' %
                                      self.scheme)
        self.connection.debug = self.debug
        return self.connection

    def delete_key(self, validate=False, headers=None, version_id=None,
                   mfa_token=None):
        self._check_object_uri('delete_key')
        bucket = self.get_bucket(validate, headers)
        return bucket.delete_key(self.object_name, headers, version_id,
                                 mfa_token)

    def list_bucket(self, prefix='', delimiter='', headers=None):
        self._check_bucket_uri('list_bucket')
        return self.get_bucket(headers=headers).list(prefix=prefix,
                                                     delimiter=delimiter,
                                                     headers=headers)

    def get_all_keys(self, validate=False, headers=None, prefix=None):
        bucket = self.get_bucket(validate, headers)
        return bucket.get_all_keys(headers)

    def get_bucket(self, validate=False, headers=None):
        self._check_bucket_uri('get_bucket')
        conn = self.connect()
        bucket = conn.get_bucket(self.bucket_name, validate, headers)
        self.check_response(bucket, 'bucket', self.uri)
        return bucket

    def get_key(self, validate=False, headers=None, version_id=None):
        self._check_object_uri('get_key')
        bucket = self.get_bucket(validate, headers)
        key = bucket.get_key(self.object_name, headers, version_id)
        self.check_response(key, 'key', self.uri)
        return key

    def new_key(self, validate=False, headers=None):
        self._check_object_uri('new_key')
        bucket = self.get_bucket(validate, headers)
        return bucket.new_key(self.object_name)

    def get_contents_to_stream(self, fp, headers=None, version_id=None):
        self._check_object_uri('get_key')
        self._warn_about_args('get_key', validate=False)
        key = self.get_key(None, headers)
        self.check_response(key, 'key', self.uri)
        return key.get_contents_to_file(fp, headers, version_id=version_id)

    def get_contents_to_file(self, fp, headers=None, cb=None, num_cb=10,
                             torrent=False, version_id=None,
                             res_download_handler=None, response_headers=None):
        self._check_object_uri('get_contents_to_file')
        key = self.get_key(None, headers)
        self.check_response(key, 'key', self.uri)
        key.get_contents_to_file(fp, headers, cb, num_cb, torrent, version_id,
                                 res_download_handler, response_headers)

    def get_contents_as_string(self, validate=False, headers=None, cb=None,
                               num_cb=10, torrent=False, version_id=None):
        self._check_object_uri('get_contents_as_string')
        key = self.get_key(validate, headers)
        self.check_response(key, 'key', self.uri)
        return key.get_contents_as_string(headers, cb, num_cb, torrent,
                                          version_id)

    def acl_class(self):
        conn = self.connect()
        acl_class = conn.provider.acl_class
        self.check_response(acl_class, 'acl_class', self.uri)
        return acl_class

    def canned_acls(self):
        conn = self.connect()
        canned_acls = conn.provider.canned_acls
        self.check_response(canned_acls, 'canned_acls', self.uri)
        return canned_acls


class BucketStorageUri(StorageUri):
    """
    StorageUri subclass that handles bucket storage providers.
    Callers should instantiate this class by calling boto.storage_uri().
    """

    delim = '/'
    capabilities = set([]) # A set of additional capabilities.

    def __init__(self, scheme, bucket_name=None, object_name=None,
                 debug=0, connection_args=None, suppress_consec_slashes=True):
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
        @param suppress_consec_slashes: If provided, controls whether
            consecutive slashes will be suppressed in key paths.

        After instantiation the components are available in the following
        fields: uri, scheme, bucket_name, object_name.
        """

        self.scheme = scheme
        self.bucket_name = bucket_name
        self.object_name = object_name
        if connection_args:
            self.connection_args = connection_args
        self.suppress_consec_slashes = suppress_consec_slashes
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
        self._check_bucket_uri('clone_replace_name')
        return BucketStorageUri(
            self.scheme, bucket_name=self.bucket_name, object_name=new_name,
            debug=self.debug,
            suppress_consec_slashes=self.suppress_consec_slashes)

    def get_acl(self, validate=False, headers=None, version_id=None):
        """returns a bucket's acl"""
        self._check_bucket_uri('get_acl')
        bucket = self.get_bucket(validate, headers)
        # This works for both bucket- and object- level ACLs (former passes
        # key_name=None):
        key_name = self.object_name or ''
        acl = bucket.get_acl(key_name, headers, version_id)
        self.check_response(acl, 'acl', self.uri)
        return acl

    def get_def_acl(self, validate=False, headers=None):
        """returns a bucket's default object acl"""
        self._check_bucket_uri('get_def_acl')
        bucket = self.get_bucket(validate, headers)
        # This works for both bucket- and object- level ACLs (former passes
        # key_name=None):
        acl = bucket.get_def_acl('', headers)
        self.check_response(acl, 'acl', self.uri)
        return acl

    def get_cors(self, validate=False, headers=None):
        """returns a bucket's CORS XML"""
        self._check_bucket_uri('get_cors')
        bucket = self.get_bucket(validate, headers)
        cors = bucket.get_cors(headers)
        self.check_response(cors, 'cors', self.uri)
        return cors

    def set_cors(self, cors, validate=False, headers=None):
        """sets or updates a bucket's CORS XML"""
        self._check_bucket_uri('set_cors ')
        bucket = self.get_bucket(validate, headers)
        bucket.set_cors(cors.to_xml(), headers)

    def get_location(self, validate=False, headers=None):
        self._check_bucket_uri('get_location')
        bucket = self.get_bucket(validate, headers)
        return bucket.get_location()

    def get_subresource(self, subresource, validate=False, headers=None,
                        version_id=None):
        self._check_bucket_uri('get_subresource')
        bucket = self.get_bucket(validate, headers)
        return bucket.get_subresource(subresource, self.object_name, headers,
                                      version_id)

    def add_group_email_grant(self, permission, email_address, recursive=False,
                              validate=False, headers=None):
        self._check_bucket_uri('add_group_email_grant')
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
            raise InvalidUriError('add_group_email_grant() on bucket-less URI '
                                  '%s' % self.uri)

    def add_email_grant(self, permission, email_address, recursive=False,
                        validate=False, headers=None):
        self._check_bucket_uri('add_email_grant')
        if not self.object_name:
            bucket = self.get_bucket(validate, headers)
            bucket.add_email_grant(permission, email_address, recursive,
                                   headers)
        else:
            key = self.get_key(validate, headers)
            self.check_response(key, 'key', self.uri)
            key.add_email_grant(permission, email_address)

    def add_user_grant(self, permission, user_id, recursive=False,
                       validate=False, headers=None):
        self._check_bucket_uri('add_user_grant')
        if not self.object_name:
            bucket = self.get_bucket(validate, headers)
            bucket.add_user_grant(permission, user_id, recursive, headers)
        else:
            key = self.get_key(validate, headers)
            self.check_response(key, 'key', self.uri)
            key.add_user_grant(permission, user_id)

    def list_grants(self, headers=None):
        self._check_bucket_uri('list_grants ')
        bucket = self.get_bucket(headers)
        return bucket.list_grants(headers)

    def is_file_uri(self):
        """Returns True if this URI names a file or directory."""
        return False

    def is_cloud_uri(self):
        """Returns True if this URI names a bucket or object."""
        return True

    def names_container(self):
        """
        Returns True if this URI names a directory or bucket. Will return
        False for bucket subdirs; providing bucket subdir semantics needs to
        be done by the caller (like gsutil does).
        """
        return bool(not self.object_name)

    def names_singleton(self):
        """Returns True if this URI names a file or object."""
        return bool(self.object_name)

    def names_directory(self):
        """Returns True if this URI names a directory."""
        return False

    def names_provider(self):
        """Returns True if this URI names a provider."""
        return bool(not self.bucket_name)

    def names_bucket(self):
        """Returns True if this URI names a bucket."""
        return self.names_container()

    def names_file(self):
        """Returns True if this URI names a file."""
        return False

    def names_object(self):
        """Returns True if this URI names an object."""
        return self.names_singleton()

    def is_stream(self):
        """Returns True if this URI represents input/output stream."""
        return False

    def create_bucket(self, headers=None, location='', policy=None):
        self._check_bucket_uri('create_bucket ')
        conn = self.connect()
        return conn.create_bucket(self.bucket_name, headers, location, policy)

    def delete_bucket(self, headers=None):
        self._check_bucket_uri('delete_bucket')
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

    def set_acl(self, acl_or_str, key_name='', validate=False, headers=None,
                version_id=None):
        """sets or updates a bucket's acl"""
        self._check_bucket_uri('set_acl')
        key_name = key_name or self.object_name or ''
        self.get_bucket(validate, headers).set_acl(acl_or_str, key_name,
                                                   headers, version_id)

    def set_def_acl(self, acl_or_str, key_name='', validate=False,
                    headers=None, version_id=None):
        """sets or updates a bucket's default object acl"""
        self._check_bucket_uri('set_def_acl')
        self.get_bucket(validate, headers).set_def_acl(acl_or_str, '', headers)

    def set_canned_acl(self, acl_str, validate=False, headers=None,
                       version_id=None):
        """sets or updates a bucket's acl to a predefined (canned) value"""
        self._check_object_uri('set_canned_acl')
        self._warn_about_args('set_canned_acl', version_id=version_id)
        key = self.get_key(validate, headers)
        self.check_response(key, 'key', self.uri)
        key.set_canned_acl(acl_str, headers)

    def set_def_canned_acl(self, acl_str, validate=False, headers=None,
                           version_id=None):
        """sets or updates a bucket's default object acl to a predefined
           (canned) value"""
        self._check_bucket_uri('set_def_canned_acl ')
        key = self.get_key(validate, headers)
        self.check_response(key, 'key', self.uri)
        key.set_def_canned_acl(acl_str, headers, version_id)

    def set_subresource(self, subresource, value, validate=False, headers=None,
                        version_id=None):
        self._check_bucket_uri('set_subresource')
        bucket = self.get_bucket(validate, headers)
        bucket.set_subresource(subresource, value, self.object_name, headers,
                               version_id)

    def set_contents_from_string(self, s, headers=None, replace=True,
                                 cb=None, num_cb=10, policy=None, md5=None,
                                 reduced_redundancy=False):
        self._check_object_uri('set_contents_from_string')
        key = self.new_key(headers=headers)
        if self.scheme == 'gs':
            if reduced_redundancy:
                sys.stderr.write('Warning: GCS does not support '
                                 'reduced_redundancy; argument ignored by '
                                 'set_contents_from_string')
            key.set_contents_from_string(s, headers, replace, cb, num_cb,
                                         policy, md5)
        else:
            key.set_contents_from_string(s, headers, replace, cb, num_cb,
                                         policy, md5, reduced_redundancy)

    def set_contents_from_file(self, fp, headers=None, replace=True, cb=None,
                               num_cb=10, policy=None, md5=None, size=None,
                               rewind=False, res_upload_handler=None):
        self._check_object_uri('set_contents_from_file')
        key = self.new_key(headers=headers)
        if self.scheme == 'gs':
            return key.set_contents_from_file(
                    fp, headers, replace, cb, num_cb, policy, md5, size=size,
                    rewind=rewind, res_upload_handler=res_upload_handler)
        else:
            self._warn_about_args('set_contents_from_file',
                                  res_upload_handler=res_upload_handler)
            return key.set_contents_from_file(fp, headers, replace, cb, num_cb,
                                              policy, md5, size=size,
                                              rewind=rewind)

    def set_contents_from_stream(self, fp, headers=None, replace=True, cb=None,
                                 policy=None, reduced_redundancy=False):
        self._check_object_uri('set_contents_from_stream')
        dst_key = self.new_key(False, headers)
        dst_key.set_contents_from_stream(fp, headers, replace, cb,
                                         policy=policy,
                                         reduced_redundancy=reduced_redundancy)

    def copy_key(self, src_bucket_name, src_key_name, metadata=None,
                 src_version_id=None, storage_class='STANDARD',
                 preserve_acl=False, encrypt_key=False, headers=None,
                 query_args=None):
        self._check_object_uri('copy_key')
        dst_bucket = self.get_bucket(validate=False, headers=headers)
        dst_bucket.copy_key(new_key_name=self.object_name,
                            src_bucket_name=src_bucket_name,
                            src_key_name=src_key_name, metadata=metadata,
                            src_version_id=src_version_id,
                            storage_class=storage_class,
                            preserve_acl=preserve_acl, encrypt_key=encrypt_key,
                            headers=headers, query_args=query_args)

    def enable_logging(self, target_bucket, target_prefix=None, validate=False,
                       headers=None, version_id=None):
        self._check_bucket_uri('enable_logging')
        bucket = self.get_bucket(validate, headers)
        bucket.enable_logging(target_bucket, target_prefix, headers=headers)

    def disable_logging(self, validate=False, headers=None, version_id=None):
        self._check_bucket_uri('disable_logging')
        bucket = self.get_bucket(validate, headers)
        bucket.disable_logging(headers=headers)

    def set_website_config(self, main_page_suffix=None, error_key=None,
                           validate=False, headers=None):
        bucket = self.get_bucket(validate, headers)
        if not (main_page_suffix or error_key):
            bucket.delete_website_configuration(headers)
        else:
            bucket.configure_website(main_page_suffix, error_key, headers)

    def get_website_config(self, validate=False, headers=None):
        bucket = self.get_bucket(validate, headers)
        return bucket.get_website_configuration_with_xml(headers)


class FileStorageUri(StorageUri):
    """
    StorageUri subclass that handles files in the local file system.
    Callers should instantiate this class by calling boto.storage_uri().

    See file/README about how we map StorageUri operations onto a file system.
    """

    delim = os.sep

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

    def is_file_uri(self):
        """Returns True if this URI names a file or directory."""
        return True

    def is_cloud_uri(self):
        """Returns True if this URI names a bucket or object."""
        return False

    def names_container(self):
        """Returns True if this URI names a directory or bucket."""
        return self.names_directory()

    def names_singleton(self):
        """Returns True if this URI names a file (or stream) or object."""
        return not self.names_container()

    def names_directory(self):
        """Returns True if this URI names a directory."""
        if self.stream:
            return False
        return os.path.isdir(self.object_name)

    def names_provider(self):
        """Returns True if this URI names a provider."""
        return False

    def names_bucket(self):
        """Returns True if this URI names a bucket."""
        return False

    def names_file(self):
        """Returns True if this URI names a file."""
        return self.names_singleton()

    def names_object(self):
        """Returns True if this URI names an object."""
        return False

    def is_stream(self):
        """Returns True if this URI represents input/output stream.
        """
        return bool(self.stream)

    def close(self):
        """Closes the underlying file.
        """
        self.get_key().close()
