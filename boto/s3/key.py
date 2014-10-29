# Copyright (c) 2006-2012 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2011, Nexenta Systems Inc.
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
import email.utils
import errno
import hashlib
from io import RawIOBase
import json
import mimetypes
import os
import re
import base64
import binascii
import math
import hashlib
import urlparse
from Crypto.Cipher import AES
import boto.utils
from boto.compat import BytesIO, six, urllib, encodebytes

from boto.exception import BotoClientError
from boto.exception import StorageDataError
from boto.exception import PleaseRetryException
from boto.provider import Provider
from boto.s3.keyfile import KeyFile
from boto.s3.user import User
from boto import UserAgent
from boto.utils import compute_md5, compute_hash
from boto.utils import find_matching_headers
from boto.utils import merge_headers_by_name


class _AESBase(RawIOBase):

    def __init__(self, stream, encryption_key, iv=None, add_padding=True):
        super(RawIOBase, self).__init__()
        self._stream = stream
        self._encryption_key = encryption_key
        self._iv = iv
        self._cipher = None
        self._initial_position = None
        self._add_padding = add_padding
        self._padding_size = None  # Undefined until the last block has been processed
        self._init()

    def _init(self):
        self._cipher = AES.new(self._encryption_key, AES.MODE_CBC, self._iv)
        self._initial_position = self._stream.tell() if hasattr(self._stream, 'tell') else None
        self._padding_size = None

    @property
    def padding_size(self):
        if not self._add_padding:
            return 0
        if self._padding_size is None:
            raise BotoClientError('padding_size will contains a valid value after the last block has been processed')
        return self._padding_size

    def _ensure_read_multiple_of_16(self, n):
        if n % 16:
            raise BotoClientError('Please read in multiples of 16 bytes. Got {}'.format(n))


class _AESEncryptor(_AESBase):
    """
    Encrypt the underlying stream.
    """

    def tell(self):
        return self._stream.tell() + (16 - self._stream.tell() % 16) % 16

    def seek(self, offset, whence=0):
        if whence == 0 and offset < self.tell():
            if offset < self._initial_position:
                raise IOError('Offset too low (offet = {} and spos = {})'.format(offset, self._initial_position))
            elif offset < self.tell():
                self._stream.seek(self._initial_position)
                self._init()
                self.seek(offset, whence)
            elif offset > self.tell():
                chunk_size = 5 * 1024 * 1024
                n_bytes_to_read = offset - self._initial_position
                self.read(n_bytes_to_read % chunk_size)
                for _ in xrange(n_bytes_to_read / chunk_size):
                    self.read(chunk_size)
        if whence != 0 and offset != 0:
            raise IOError('seek({}, {}) not supported'.format(offset, whence))

    def read(self, n=-1):
        self._ensure_read_multiple_of_16(n)
        current_block = self._stream.read(n)

        if len(current_block) % 16 > 0 and not self._add_padding:
            raise IOError('the length of the content is not a multiple of the AES block size (16) '
                          'and padding is disabled')

        if len(current_block) < n and self._add_padding and self._padding_size is None:
            # End of the stream, add the padding
            self._padding_size = padding_size = 16 - len(current_block) % 16
            # Note: the size of the current block will never be greater than n because:
            # n % 16 == 0 && len(current_block) % 16 == 0 && len(current_block) < n -> len(current_block) <= n-16
            current_block += ''.join([chr(padding_size)] * padding_size)

        if current_block:
            current_block = self._cipher.encrypt(current_block)
        return current_block


class _AESDecryptor(_AESBase):
    """
    Decrypt the underlying stream.
    """

    def __init__(self, *args, **kwargs):
        super(_AESDecryptor, self).__init__(*args, **kwargs)
        self._next_block = None

    def read(self, n=-1):
        if n == -1:
            # Read until the end of the stream
            if self._next_block:
                current_block = self._next_block + self._stream.read()
            else:
                current_block = self._stream.read()
        else:
            self._ensure_read_multiple_of_16(n)
            if self._next_block:
                if len(self._next_block) > n:
                    current_block = self._next_block[:n]
                    self._next_block = self._next_block[n:]
                else:
                    if len(self._next_block) < n:
                        self._next_block += self._stream.read(n-len(self._next_block))
                    current_block = self._next_block
                    self._next_block = self._stream.read(n)
            else:
                current_block = self._stream.read(n)
                self._next_block = self._stream.read(n)

        if len(current_block) > 0:
            current_block = self._cipher.decrypt(current_block)
            if not self._next_block:
                # Last block, contains the padding
                self._padding_size = ord(current_block[-1])

                # There's always at least on byte of padding which contains its size.
                # All the bytes of the padding block should be identical.
                #
                # Getting the wrong values could mean that the file was not encrypted properly or that
                # the encryption key/iv are not the ones used to encrypt the files.
                #
                # This is a weak integrity check. The probability of passing this test with a random file is at
                # least 1/256 (with a padding of size 1). In such a case, the content will be truncated/expanded.
                padding_block = current_block[-self._padding_size:]
                expected_padding_block = ''.join([chr(self._padding_size)] * self._padding_size)
                if self._padding_size < 1 or self._padding_size > 16 or padding_block != expected_padding_block:
                    raise BotoClientError('Given final block not properly padded. ' +
                                          'Please check that you are using the right encryption key.')

                current_block = current_block[:-self._padding_size]
            return current_block


class _Delegator(object):

    def __init__(self, delegate, parent):
        self._delegate = delegate
        self._parent = parent

    def __getattr__(self, key):
        if hasattr(self._delegate, key):
            return getattr(self._delegate, key)
        if hasattr(self._parent, key):
            return getattr(self._parent, key)
        # Default behaviour
        raise AttributeError(key)


class MaxSizeFileWrapper(object):
    """
    Read at most until the current position + size from the underlying stream
    """
    def __init__(self, fp, size=None):
        self._fp = fp
        self._size = size
        self._initial_position = fp.tell()

    def read(self, n=-1):
        if self._size is None:
            return self._fp.read(n)

        max_n = self._size - (self._fp.tell() - self._initial_position)
        if n == -1:
            return self._fp.read(max_n)
        else:
            return self._fp.read(min(n, max_n))

    def __getattr__(self, key):
        return getattr(self._fp, key)


class Key(object):
    """
    Represents a key (object) in an S3 bucket.

    :ivar bucket: The parent :class:`boto.s3.bucket.Bucket`.
    :ivar name: The name of this Key object.
    :ivar metadata: A dictionary containing user metadata that you
        wish to store with the object or that has been retrieved from
        an existing object.
    :ivar cache_control: The value of the `Cache-Control` HTTP header.
    :ivar content_type: The value of the `Content-Type` HTTP header.
    :ivar content_encoding: The value of the `Content-Encoding` HTTP header.
    :ivar content_disposition: The value of the `Content-Disposition` HTTP
        header.
    :ivar content_language: The value of the `Content-Language` HTTP header.
    :ivar etag: The `etag` associated with this object.
    :ivar last_modified: The string timestamp representing the last
        time this object was modified in S3.
    :ivar owner: The ID of the owner of this object.
    :ivar storage_class: The storage class of the object.  Currently, one of:
        STANDARD | REDUCED_REDUNDANCY | GLACIER
    :ivar md5: The MD5 hash of the contents of the object.
    :ivar size: The size, in bytes, of the object.
    :ivar version_id: The version ID of this object, if it is a versioned
        object.
    :ivar encrypted: Whether the object is encrypted while at rest on
        the server.
    """

    DefaultContentType = 'application/octet-stream'

    RestoreBody = """<?xml version="1.0" encoding="UTF-8"?>
      <RestoreRequest xmlns="http://s3.amazonaws.com/doc/2006-03-01">
        <Days>%s</Days>
      </RestoreRequest>"""


    BufferSize = boto.config.getint('Boto', 'key_buffer_size', 8192)

    # The object metadata fields a user can set, other than custom metadata
    # fields (i.e., those beginning with a provider-specific prefix like
    # x-amz-meta).
    base_user_settable_fields = set(["cache-control", "content-disposition",
                                    "content-encoding", "content-language",
                                    "content-md5", "content-type",
                                     "x-robots-tag", "expires"])
    _underscore_base_user_settable_fields = set()
    for f in base_user_settable_fields:
      _underscore_base_user_settable_fields.add(f.replace('-', '_'))
    # Metadata fields, whether user-settable or not, other than custom
    # metadata fields (i.e., those beginning with a provider specific prefix
    # like x-amz-meta).
    base_fields = (base_user_settable_fields |
                   set(["last-modified", "content-length", "date", "etag"]))



    def __init__(self, bucket=None, name=None):
        self.bucket = bucket
        self.name = name
        self.metadata = {}
        self.cache_control = None
        self.content_type = self.DefaultContentType
        self.content_encoding = None
        self.content_disposition = None
        self.content_language = None
        self.filename = None
        self.etag = None
        self.is_latest = False
        self.last_modified = None
        self.owner = None
        self._storage_class = None
        self.path = None
        self.resp = None
        self.mode = None
        self.size = None
        self.version_id = None
        self.source_version_id = None
        self.delete_marker = False
        self.encrypted = None
        # If the object is being restored, this attribute will be set to True.
        # If the object is restored, it will be set to False.  Otherwise this
        # value will be None. If the restore is completed (ongoing_restore =
        # False), the expiry_date will be populated with the expiry date of the
        # restored object.
        self.ongoing_restore = None
        self.expiry_date = None
        self.local_hashes = {}

    def __repr__(self):
        if self.bucket:
            name = u'<Key: %s,%s>' % (self.bucket.name, self.name)
        else:
            name = u'<Key: None,%s>' % self.name

        # Encode to bytes for Python 2 to prevent display decoding issues
        if not isinstance(name, str):
            name = name.encode('utf-8')

        return name

    def __iter__(self):
        return self

    @property
    def provider(self):
        provider = None
        if self.bucket and self.bucket.connection:
            provider = self.bucket.connection.provider
        return provider

    def _get_key(self):
        return self.name

    def _set_key(self, value):
        self.name = value

    key = property(_get_key, _set_key);

    def _get_md5(self):
        if 'md5' in self.local_hashes and self.local_hashes['md5']:
            return binascii.b2a_hex(self.local_hashes['md5'])

    def _set_md5(self, value):
        if value:
            self.local_hashes['md5'] = binascii.a2b_hex(value)
        elif 'md5' in self.local_hashes:
            self.local_hashes.pop('md5', None)

    md5 = property(_get_md5, _set_md5);

    def _get_base64md5(self):
        if 'md5' in self.local_hashes and self.local_hashes['md5']:
            md5 = self.local_hashes['md5']
            if not isinstance(md5, bytes):
                md5 = md5.encode('utf-8')
            return binascii.b2a_base64(md5).decode('utf-8').rstrip('\n')

    def _set_base64md5(self, value):
        if value:
            if not isinstance(value, six.string_types):
                value = value.decode('utf-8')
            self.local_hashes['md5'] = binascii.a2b_base64(value)
        elif 'md5' in self.local_hashes:
            del self.local_hashes['md5']

    base64md5 = property(_get_base64md5, _set_base64md5);

    def _get_storage_class(self):
        if self._storage_class is None and self.bucket:
            # Attempt to fetch storage class
            list_items = list(self.bucket.list(self.name.encode('utf-8')))
            if len(list_items) and getattr(list_items[0], '_storage_class',
                                           None):
                self._storage_class = list_items[0]._storage_class
            else:
                # Key is not yet saved? Just use default...
                self._storage_class = 'STANDARD'

        return self._storage_class

    def _set_storage_class(self, value):
        self._storage_class = value

    storage_class = property(_get_storage_class, _set_storage_class)

    def get_md5_from_hexdigest(self, md5_hexdigest):
        """
        A utility function to create the 2-tuple (md5hexdigest, base64md5)
        from just having a precalculated md5_hexdigest.
        """
        digest = binascii.unhexlify(md5_hexdigest)
        base64md5 = encodebytes(digest)
        if base64md5[-1] == '\n':
            base64md5 = base64md5[0:-1]
        return (md5_hexdigest, base64md5)

    def handle_encryption_headers(self, resp):
        provider = self.bucket.connection.provider
        if provider.server_side_encryption_header:
            self.encrypted = resp.getheader(
                provider.server_side_encryption_header, None)
        else:
            self.encrypted = None

    def handle_version_headers(self, resp, force=False):
        provider = self.bucket.connection.provider
        # If the Key object already has a version_id attribute value, it
        # means that it represents an explicit version and the user is
        # doing a get_contents_*(version_id=<foo>) to retrieve another
        # version of the Key.  In that case, we don't really want to
        # overwrite the version_id in this Key object.  Comprende?
        if self.version_id is None or force:
            self.version_id = resp.getheader(provider.version_id, None)
        self.source_version_id = resp.getheader(provider.copy_source_version_id,
                                                None)
        if resp.getheader(provider.delete_marker, 'false') == 'true':
            self.delete_marker = True
        else:
            self.delete_marker = False

    def handle_restore_headers(self, response):
        provider = self.bucket.connection.provider
        header = response.getheader(provider.restore_header)
        if header is None:
            return
        parts = header.split(',', 1)
        for part in parts:
            key, val = [i.strip() for i in part.split('=')]
            val = val.replace('"', '')
            if key == 'ongoing-request':
                self.ongoing_restore = True if val.lower() == 'true' else False
            elif key == 'expiry-date':
                self.expiry_date = val

    def handle_addl_headers(self, headers):
        """
        Used by Key subclasses to do additional, provider-specific
        processing of response headers. No-op for this base class.
        """
        pass

    def open_read(self, headers=None, query_args='',
                  override_num_retries=None, response_headers=None):
        """
        Open this key for reading

        :type headers: dict
        :param headers: Headers to pass in the web request

        :type query_args: string
        :param query_args: Arguments to pass in the query string
            (ie, 'torrent')

        :type override_num_retries: int
        :param override_num_retries: If not None will override configured
            num_retries parameter for underlying GET.

        :type response_headers: dict
        :param response_headers: A dictionary containing HTTP
            headers/values that will override any headers associated
            with the stored object in the response.  See
            http://goo.gl/EWOPb for details.
        """
        if self.resp is None:
            self.mode = 'r'

            provider = self.bucket.connection.provider
            self.resp = self.bucket.connection.make_request(
                'GET', self.bucket.name, self.name, headers,
                query_args=query_args,
                override_num_retries=override_num_retries)
            if self.resp.status < 199 or self.resp.status > 299:
                body = self.resp.read()
                raise provider.storage_response_error(self.resp.status,
                                                      self.resp.reason, body)
            response_headers = self.resp.msg
            self.metadata = boto.utils.get_aws_metadata(response_headers,
                                                        provider)

            master_key = self.bucket.connection.client_side_encryption_key
            if master_key and self.get_metadata('x-amz-key'):
                iv_base64 = self.get_metadata('x-amz-iv')
                iv = base64.b64decode(iv_base64)

                envelope_key_base64_with_padding = self.get_metadata('x-amz-key')
                envelope_key_encrypted = base64.b64decode(envelope_key_base64_with_padding)[:-16]
                envelope_key = AES.new(master_key, AES.MODE_ECB).decrypt(envelope_key_encrypted)

                matdesc = self.get_metadata('x-amz-matdesc')
                if matdesc != '{}':
                    raise BotoClientError('This key was encrypted by a different client using non-default ' +
                                          'parameters. This is not supported. Got: {}'.format(matdesc))

                decryptor = _AESDecryptor(self.resp, envelope_key, iv)
                self.resp = _Delegator(decryptor, self.resp)

            for name, value in response_headers.items():
                # To get correct size for Range GETs, use Content-Range
                # header if one was returned. If not, use Content-Length
                # header.
                if (name.lower() == 'content-length' and
                    'Content-Range' not in response_headers):
                    self.size = int(value)
                elif name.lower() == 'content-range':
                    end_range = re.sub('.*/(.*)', '\\1', value)
                    self.size = int(end_range)
                elif name.lower() in Key.base_fields:
                    self.__dict__[name.lower().replace('-', '_')] = value

            if master_key:
                size_as_string = self.get_metadata('x-amz-unencrypted-content-length')
                if size_as_string:
                    self.size = int(size_as_string)
                else:
                    # If the file was sent
                    #    - from a stream, the size won't be set
                    #    - using the java sdk, the size may not be set
                    self.size = None

            self.handle_version_headers(self.resp)
            self.handle_encryption_headers(self.resp)
            self.handle_restore_headers(self.resp)
            self.handle_addl_headers(self.resp.getheaders())

    def open_write(self, headers=None, override_num_retries=None):
        """
        Open this key for writing.
        Not yet implemented

        :type headers: dict
        :param headers: Headers to pass in the write request

        :type override_num_retries: int
        :param override_num_retries: If not None will override configured
            num_retries parameter for underlying PUT.
        """
        raise BotoClientError('Not Implemented')

    def open(self, mode='r', headers=None, query_args=None,
             override_num_retries=None):
        if mode == 'r':
            self.mode = 'r'
            self.open_read(headers=headers, query_args=query_args,
                           override_num_retries=override_num_retries)
        elif mode == 'w':
            self.mode = 'w'
            self.open_write(headers=headers,
                            override_num_retries=override_num_retries)
        else:
            raise BotoClientError('Invalid mode: %s' % mode)

    closed = False

    def close(self, fast=False):
        """
        Close this key.

        :type fast: bool
        :param fast: True if you want the connection to be closed without first
        reading the content. This should only be used in cases where subsequent
        calls don't need to return the content from the open HTTP connection.
        Note: As explained at
        http://docs.python.org/2/library/httplib.html#httplib.HTTPConnection.getresponse,
        callers must read the whole response before sending a new request to the
        server. Calling Key.close(fast=True) and making a subsequent request to
        the server will work because boto will get an httplib exception and
        close/reopen the connection.

        """
        if self.resp and not fast:
            self.resp.read()
        self.resp = None
        self.mode = None
        self.closed = True

    def next(self):
        """
        By providing a next method, the key object supports use as an iterator.
        For example, you can now say:

        for bytes in key:
            write bytes to a file or whatever

        All of the HTTP connection stuff is handled for you.
        """
        self.open_read()
        data = self.resp.read(self.BufferSize)
        if not data:
            self.close()
            raise StopIteration
        return data

    # Python 3 iterator support
    __next__ = next

    def read(self, size=0):
        self.open_read()
        if size == 0:
            data = self.resp.read()
        else:
            data = self.resp.read(size)
        if not data:
            self.close()
        return data

    def change_storage_class(self, new_storage_class, dst_bucket=None,
                             validate_dst_bucket=True):
        """
        Change the storage class of an existing key.
        Depending on whether a different destination bucket is supplied
        or not, this will either move the item within the bucket, preserving
        all metadata and ACL info bucket changing the storage class or it
        will copy the item to the provided destination bucket, also
        preserving metadata and ACL info.

        :type new_storage_class: string
        :param new_storage_class: The new storage class for the Key.
            Possible values are:
            * STANDARD
            * REDUCED_REDUNDANCY

        :type dst_bucket: string
        :param dst_bucket: The name of a destination bucket.  If not
            provided the current bucket of the key will be used.

        :type validate_dst_bucket: bool
        :param validate_dst_bucket: If True, will validate the dst_bucket
            by using an extra list request.
        """
        if new_storage_class == 'STANDARD':
            return self.copy(self.bucket.name, self.name,
                             reduced_redundancy=False, preserve_acl=True,
                             validate_dst_bucket=validate_dst_bucket)
        elif new_storage_class == 'REDUCED_REDUNDANCY':
            return self.copy(self.bucket.name, self.name,
                             reduced_redundancy=True, preserve_acl=True,
                             validate_dst_bucket=validate_dst_bucket)
        else:
            raise BotoClientError('Invalid storage class: %s' %
                                  new_storage_class)

    def copy(self, dst_bucket, dst_key, metadata=None,
             reduced_redundancy=False, preserve_acl=False,
             encrypt_key=False, validate_dst_bucket=True):
        """
        Copy this Key to another bucket.

        :type dst_bucket: string
        :param dst_bucket: The name of the destination bucket

        :type dst_key: string
        :param dst_key: The name of the destination key

        :type metadata: dict
        :param metadata: Metadata to be associated with new key.  If
            metadata is supplied, it will replace the metadata of the
            source key being copied.  If no metadata is supplied, the
            source key's metadata will be copied to the new key.

        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will force the
            storage class of the new Key to be REDUCED_REDUNDANCY
            regardless of the storage class of the key being copied.
            The Reduced Redundancy Storage (RRS) feature of S3,
            provides lower redundancy at lower storage cost.

        :type preserve_acl: bool
        :param preserve_acl: If True, the ACL from the source key will
            be copied to the destination key.  If False, the
            destination key will have the default ACL.  Note that
            preserving the ACL in the new key object will require two
            additional API calls to S3, one to retrieve the current
            ACL and one to set that ACL on the new object.  If you
            don't care about the ACL, a value of False will be
            significantly more efficient.

        :type encrypt_key: bool
        :param encrypt_key: If True, the new copy of the object will
            be encrypted on the server-side by S3 and will be stored
            in an encrypted form while at rest in S3.

        :type validate_dst_bucket: bool
        :param validate_dst_bucket: If True, will validate the dst_bucket
            by using an extra list request.

        :rtype: :class:`boto.s3.key.Key` or subclass
        :returns: An instance of the newly created key object
        """
        dst_bucket = self.bucket.connection.lookup(dst_bucket,
                                                   validate_dst_bucket)
        if reduced_redundancy:
            storage_class = 'REDUCED_REDUNDANCY'
        else:
            storage_class = self.storage_class
        return dst_bucket.copy_key(dst_key, self.bucket.name,
                                   self.name, metadata,
                                   storage_class=storage_class,
                                   preserve_acl=preserve_acl,
                                   encrypt_key=encrypt_key)

    def startElement(self, name, attrs, connection):
        if name == 'Owner':
            self.owner = User(self)
            return self.owner
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'Key':
            self.name = value
        elif name == 'ETag':
            self.etag = value
        elif name == 'IsLatest':
            if value == 'true':
                self.is_latest = True
            else:
                self.is_latest = False
        elif name == 'LastModified':
            self.last_modified = value
        elif name == 'Size':
            self.size = int(value)
        elif name == 'StorageClass':
            self.storage_class = value
        elif name == 'Owner':
            pass
        elif name == 'VersionId':
            self.version_id = value
        else:
            setattr(self, name, value)

    def exists(self, headers=None):
        """
        Returns True if the key exists

        :rtype: bool
        :return: Whether the key exists on S3
        """
        return bool(self.bucket.lookup(self.name, headers=headers))

    def delete(self, headers=None):
        """
        Delete this key from S3
        """
        return self.bucket.delete_key(self.name, version_id=self.version_id,
                                      headers=headers)

    def get_metadata(self, name):
        return self.metadata.get(name)

    def set_metadata(self, name, value):
        # Ensure that metadata that is vital to signing is in the correct
        # case. Applies to ``Content-Type`` & ``Content-MD5``.
        if name.lower() == 'content-type':
            self.metadata['Content-Type'] = value
        elif name.lower() == 'content-md5':
            self.metadata['Content-MD5'] = value
        else:
            self.metadata[name] = value
        if name.lower() in Key.base_user_settable_fields:
            self.__dict__[name.lower().replace('-', '_')] = value

    def update_metadata(self, d):
        self.metadata.update(d)

    def delete_metadata(self, name):
        self.metadata.pop(name, None)

    # convenience methods for setting/getting ACL
    def set_acl(self, acl_str, headers=None):
        if self.bucket is not None:
            self.bucket.set_acl(acl_str, self.name, headers=headers)

    def get_acl(self, headers=None):
        if self.bucket is not None:
            return self.bucket.get_acl(self.name, headers=headers)

    def get_xml_acl(self, headers=None):
        if self.bucket is not None:
            return self.bucket.get_xml_acl(self.name, headers=headers)

    def set_xml_acl(self, acl_str, headers=None):
        if self.bucket is not None:
            return self.bucket.set_xml_acl(acl_str, self.name, headers=headers)

    def set_canned_acl(self, acl_str, headers=None):
        return self.bucket.set_canned_acl(acl_str, self.name, headers)

    def get_redirect(self):
        """Return the redirect location configured for this key.

        If no redirect is configured (via set_redirect), then None
        will be returned.

        """
        response = self.bucket.connection.make_request(
            'HEAD', self.bucket.name, self.name)
        if response.status == 200:
            return response.getheader('x-amz-website-redirect-location')
        else:
            raise self.provider.storage_response_error(
                response.status, response.reason, response.read())

    def set_redirect(self, redirect_location, headers=None):
        """Configure this key to redirect to another location.

        When the bucket associated with this key is accessed from the website
        endpoint, a 301 redirect will be issued to the specified
        `redirect_location`.

        :type redirect_location: string
        :param redirect_location: The location to redirect.

        """
        if headers is None:
            headers = {}
        else:
            headers = headers.copy()

        headers['x-amz-website-redirect-location'] = redirect_location
        response = self.bucket.connection.make_request('PUT', self.bucket.name,
                                                       self.name, headers)
        if response.status == 200:
            return True
        else:
            raise self.provider.storage_response_error(
                response.status, response.reason, response.read())

    def make_public(self, headers=None):
        return self.bucket.set_canned_acl('public-read', self.name, headers)

    def generate_url(self, expires_in, method='GET', headers=None,
                     query_auth=True, force_http=False, response_headers=None,
                     expires_in_absolute=False, version_id=None,
                     policy=None, reduced_redundancy=False, encrypt_key=False):
        """
        Generate a URL to access this key.

        :type expires_in: int
        :param expires_in: How long the url is valid for, in seconds

        :type method: string
        :param method: The method to use for retrieving the file
            (default is GET)

        :type headers: dict
        :param headers: Any headers to pass along in the request

        :type query_auth: bool
        :param query_auth:

        :type force_http: bool
        :param force_http: If True, http will be used instead of https.

        :type response_headers: dict
        :param response_headers: A dictionary containing HTTP
            headers/values that will override any headers associated
            with the stored object in the response.  See
            http://goo.gl/EWOPb for details.

        :type expires_in_absolute: bool
        :param expires_in_absolute:

        :type version_id: string
        :param version_id: The version_id of the object to GET. If specified
            this overrides any value in the key.

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the
            new key in S3.

        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will set the storage
            class of the new Key to be REDUCED_REDUNDANCY. The Reduced
            Redundancy Storage (RRS) feature of S3, provides lower
            redundancy at lower storage cost.

        :type encrypt_key: bool
        :param encrypt_key: If True, the new copy of the object will
            be encrypted on the server-side by S3 and will be stored
            in an encrypted form while at rest in S3.

        :rtype: string
        :return: The URL to access the key
        """
        provider = self.bucket.connection.provider
        version_id = version_id or self.version_id
        if headers is None:
            headers = {}
        else:
            headers = headers.copy()

        # add headers accordingly (usually PUT case)
        if policy:
            headers[provider.acl_header] = policy
        if reduced_redundancy:
            self.storage_class = 'REDUCED_REDUNDANCY'
            if provider.storage_class_header:
                headers[provider.storage_class_header] = self.storage_class
        if encrypt_key:
            headers[provider.server_side_encryption_header] = 'AES256'
        headers = boto.utils.merge_meta(headers, self.metadata, provider)

        return self.bucket.connection.generate_url(expires_in, method,
                                                   self.bucket.name, self.name,
                                                   headers, query_auth,
                                                   force_http,
                                                   response_headers,
                                                   expires_in_absolute,
                                                   version_id)

    def send_file(self, fp, headers=None, cb=None, num_cb=10,
                  query_args=None, chunked_transfer=False, size=None):
        """
        Upload a file to a key into a bucket on S3.

        :type fp: file
        :param fp: The file pointer to upload. The file pointer must
            point point at the offset from which you wish to upload.
            ie. if uploading the full file, it should point at the
            start of the file. Normally when a file is opened for
            reading, the fp will point at the first byte.  See the
            bytes parameter below for more info.

        :type headers: dict
        :param headers: The headers to pass along with the PUT request

        :type num_cb: int
        :param num_cb: (optional) If a callback is specified with the
            cb parameter this parameter determines the granularity of
            the callback by defining the maximum number of times the
            callback will be called during the file
            transfer. Providing a negative integer will cause your
            callback to be called with each buffer read.

        :type query_args: string
        :param query_args: (optional) Arguments to pass in the query string.

        :type chunked_transfer: boolean
        :param chunked_transfer: (optional) If true, we use chunked
            Transfer-Encoding.

        :type size: int
        :param size: (optional) The Maximum number of bytes to read
            from the file pointer (fp). This is useful when uploading
            a file in multiple parts where you are splitting the file
            up into different ranges to be uploaded. If not specified,
            the default behaviour is to read all bytes from the file
            pointer. Less bytes may be available.
        """
        self._send_file_internal(fp, headers=headers, cb=cb, num_cb=num_cb,
                                 query_args=query_args,
                                 chunked_transfer=chunked_transfer, size=size)

    def _send_file_internal(self, fp, headers=None, cb=None, num_cb=10,
                            query_args=None, chunked_transfer=False, size=None,
                            hash_algs=None):
        provider = self.bucket.connection.provider
        try:
            spos = fp.tell()
        except IOError:
            spos = None
            self.read_from_stream = False

        size, size_before_padding = size if size is not None else self.size, size if size is not None else self.size
        md5, base64md5 = self.md5, self.base64md5
        iv, envelope_key, master_key,  = None, None, self.bucket.connection.client_side_encryption_key
        add_padding, next_iv_key = True, None
        self.delete_metadata('x-amz-iv')
        self.delete_metadata('x-amz-key')
        self.delete_metadata('x-amz-matdesc')
        self.delete_metadata('x-amz-unencrypted-content-length')
        if master_key:
            if not query_args or 'uploadId' not in query_args:
                # Generate the key
                iv = os.urandom(16)
                iv_base64 = base64.b64encode(iv)
                envelope_key = bytes(os.urandom(256/8))
                # Maximum padding because the key size is a multiple of 16
                envelope_key_padded = envelope_key + ''.join([chr(16)] * 16)
                envelope_key_encrypted = AES.new(master_key, AES.MODE_ECB).encrypt(envelope_key_padded)
                envelope_key_encrypted_base64 = base64.b64encode(envelope_key_encrypted)

                # Add the encryption headers
                self.set_metadata('x-amz-iv', iv_base64)
                self.set_metadata('x-amz-key', envelope_key_encrypted_base64)
                self.set_metadata('x-amz-matdesc', '{}')
                if size:
                    self.set_metadata('x-amz-unencrypted-content-length', size)

            else:
                # Multipart upload
                query_args_dict = urlparse.parse_qs(query_args)
                upload_id = query_args_dict['uploadId'][0]
                part_number = int(query_args_dict['partNumber'][0])

                final_part_key = '{}-{}-final'.format(self.bucket.name, upload_id)
                final_part_number = self.bucket.connection.client_side_encryption_registry.get(final_part_key, None)

                if size is None or chunked_transfer:
                    # This is not supported because we need to know if we have to add the padding
                    # before instantiating the encryptor.
                    #
                    # Only the last black can be smaller than 5MB. Therefore, if the last block is smaller than
                    # 5MB and we don't know that we are processing it, we won't add the padding and we won't
                    # be able to add it later because S3 won't accept a second part of less than 5MB.
                    raise BotoClientError('Multipart upload with client-side encryption and '
                                          'chuncked transfer are exclusive')

                if final_part_number is not None and final_part_number < part_number:
                    raise BotoClientError(
                        'Invalid part. Please check that the size of part {} was greater than '
                        '5MB and a multiple of the AES block size (16).'.format(final_part_number))

                iv_key = '{}-{}-{}'.format(self.bucket.name, upload_id, part_number-1)
                if not iv_key in self.bucket.connection.client_side_encryption_registry:
                    raise BotoClientError(
                        'Previous initialisation vector not found. Please upload the parts in order when '
                        'using client-side encryption')

                iv_base64 = self.bucket.connection.client_side_encryption_registry[iv_key]
                iv = base64.b64decode(iv_base64)
                next_iv_key = '{}-{}-{}'.format(self.bucket.name, upload_id, part_number)

                metadata_key = '{}-{}-metadata'.format(self.bucket.name, upload_id)
                metadata = json.loads(self.bucket.connection.client_side_encryption_registry[metadata_key])
                envelope_key_base64_with_padding = metadata['x-amz-key']
                envelope_key_encrypted = base64.b64decode(envelope_key_base64_with_padding)[:-16]
                envelope_key = AES.new(master_key, AES.MODE_ECB).decrypt(envelope_key_encrypted)

                if size < 5e6 or size % 16 > 0:
                    # The first time we see a file with these characteristics, we can't tell if it's the last part
                    # of the file or an error of the user (part too small or size not a multiple of the block size).
                    #
                    # The part will be treated as the last part of the file and if it's not, the user
                    # will get an error message when trying to upload the next part.
                    add_padding = True
                    self.bucket.connection.client_side_encryption_registry[final_part_key] = part_number
                else:
                    # The part could be a regular or the last part of the file.
                    #
                    # It will be treated as a regular part and if it's not, a padding-only part will be added when
                    # completing the upload.
                    add_padding = False

            # Adjust the size to take the padding into account
            # If the size is a multiple of the block size (16 bytes), a full block will be added
            if size is not None and not chunked_transfer and add_padding:
                size += 16 - size % 16

            # Adjust the md5
            if base64md5:
                encryptor = _AESEncryptor(MaxSizeFileWrapper(fp, size_before_padding), envelope_key, iv, add_padding)
                md5, base64md5, _ = compute_hash(encryptor, size=size)

        # If hash_algs is unset and the MD5 hasn't already been computed,
        # default to an MD5 hash_alg to hash the data on-the-fly.
        if hash_algs is None and not self.md5:
            hash_algs = {'md5': hashlib.md5}
        digesters = dict((alg, hash_algs[alg]()) for alg in hash_algs or {})

        def sender(http_conn, method, path, data, headers):
            # This function is called repeatedly for temporary retries
            # so we must be sure the file pointer is pointing at the
            # start of the data.
            if spos is not None and spos != fp.tell():
                fp.seek(spos)
            elif spos is None and self.read_from_stream:
                # if seek is not supported, and we've read from this
                # stream already, then we need to abort retries to
                # avoid setting bad data.
                raise provider.storage_data_error(
                    'Cannot retry failed request. fp does not support seeking.')
            sender_fp = fp

            if master_key:
                # Replace the stream
                sender_fp = _AESEncryptor(MaxSizeFileWrapper(fp, size_before_padding), envelope_key, iv, add_padding)

            # If the caller explicitly specified host header, tell putrequest
            # not to add a second host header. Similarly for accept-encoding.
            skips = {}
            if boto.utils.find_matching_headers('host', headers):
              skips['skip_host'] = 1
            if boto.utils.find_matching_headers('accept-encoding', headers):
              skips['skip_accept_encoding'] = 1
            http_conn.putrequest(method, path, **skips)
            for key in headers:
                http_conn.putheader(key, headers[key])
            http_conn.endheaders()

            save_debug = self.bucket.connection.debug
            self.bucket.connection.debug = 0
            # If the debuglevel < 4 we don't want to show connection
            # payload, so turn off HTTP connection-level debug output (to
            # be restored below).
            # Use the getattr approach to allow this to work in AppEngine.
            if getattr(http_conn, 'debuglevel', 0) < 4:
                http_conn.set_debuglevel(0)

            data_len = 0
            if cb:
                if size:
                    cb_size = size
                elif self.size:
                    cb_size = self.size
                else:
                    cb_size = 0
                if chunked_transfer and cb_size == 0:
                    # For chunked Transfer, we call the cb for every 1MB
                    # of data transferred, except when we know size.
                    cb_count = (1024 * 1024) / self.BufferSize
                elif num_cb > 1:
                    cb_count = int(
                        math.ceil(cb_size / self.BufferSize / (num_cb - 1.0)))
                elif num_cb < 0:
                    cb_count = -1
                else:
                    cb_count = 0
                i = 0
                cb(data_len, cb_size)

            bytes_togo = size
            if bytes_togo is not None and bytes_togo < self.BufferSize:
                chunk = sender_fp.read(bytes_togo)
            else:
                chunk = sender_fp.read(self.BufferSize)

            if not isinstance(chunk, bytes):
                chunk = chunk.encode('utf-8')

            if spos is None:
                # read at least something from a non-seekable fp.
                self.read_from_stream = True
            while chunk:
                chunk_len = len(chunk)
                data_len += chunk_len
                if chunked_transfer:
                    http_conn.send('%x;\r\n' % chunk_len)
                    http_conn.send(chunk)
                    http_conn.send('\r\n')
                else:
                    http_conn.send(chunk)
                for alg in digesters:
                    digesters[alg].update(chunk)
                if bytes_togo:
                    bytes_togo -= chunk_len
                    if bytes_togo <= 0:
                        break
                if cb:
                    i += 1
                    if i == cb_count or cb_count == -1:
                        cb(data_len, cb_size)
                        i = 0
                if bytes_togo and bytes_togo < self.BufferSize:
                    chunk = sender_fp.read(bytes_togo)
                else:
                    chunk = sender_fp.read(self.BufferSize)

                if not isinstance(chunk, bytes):
                    chunk = chunk.encode('utf-8')

            self.size = data_len
            if master_key:
                self.size = self.size - sender_fp.padding_size
                if next_iv_key is not None:
                    next_iv_base64 = base64.b64encode(chunk[-16:])
                    self.bucket.connection.client_side_encryption_registry[next_iv_key] = next_iv_base64

            for alg in digesters:
                self.local_hashes[alg] = digesters[alg].digest()

            if chunked_transfer:
                http_conn.send('0\r\n')
                    # http_conn.send("Content-MD5: %s\r\n" % self.base64md5)
                http_conn.send('\r\n')

            if cb and (cb_count <= 1 or i > 0) and data_len > 0:
                cb(data_len, cb_size)

            http_conn.set_debuglevel(save_debug)
            self.bucket.connection.debug = save_debug
            response = http_conn.getresponse()
            body = response.read()

            if not self.should_retry(response, chunked_transfer, md5):
                raise provider.storage_response_error(
                    response.status, response.reason, body)

            return response

        if not headers:
            headers = {}
        else:
            headers = headers.copy()
        # Overwrite user-supplied user-agent.
        for header in find_matching_headers('User-Agent', headers):
            del headers[header]
        headers['User-Agent'] = UserAgent
        # If storage_class is None, then a user has not explicitly requested
        # a storage class, so we can assume STANDARD here
        if self._storage_class not in [None, 'STANDARD']:
            headers[provider.storage_class_header] = self.storage_class
        if find_matching_headers('Content-Encoding', headers):
            self.content_encoding = merge_headers_by_name(
                'Content-Encoding', headers)
        if find_matching_headers('Content-Language', headers):
            self.content_language = merge_headers_by_name(
                'Content-Language', headers)
        content_type_headers = find_matching_headers('Content-Type', headers)
        if content_type_headers:
            # Some use cases need to suppress sending of the Content-Type
            # header and depend on the receiving server to set the content
            # type. This can be achieved by setting headers['Content-Type']
            # to None when calling this method.
            if (len(content_type_headers) == 1 and
                headers[content_type_headers[0]] is None):
                # Delete null Content-Type value to skip sending that header.
                del headers[content_type_headers[0]]
            else:
                self.content_type = merge_headers_by_name(
                    'Content-Type', headers)
        elif self.path:
            self.content_type = mimetypes.guess_type(self.path)[0]
            if self.content_type is None:
                self.content_type = self.DefaultContentType
            headers['Content-Type'] = self.content_type
        else:
            headers['Content-Type'] = self.content_type
        if base64md5:
            headers['Content-MD5'] = base64md5
        if chunked_transfer:
            headers['Transfer-Encoding'] = 'chunked'
            #if not self.base64md5:
            #    headers['Trailer'] = "Content-MD5"
        else:
            headers['Content-Length'] = str(size)
        # This is terrible. We need a SHA256 of the body for SigV4, but to do
        # the chunked ``sender`` behavior above, the ``fp`` isn't available to
        # the auth mechanism (because closures). Detect if it's SigV4 & embelish
        # while we can before the auth calculations occur.
        if 'hmac-v4-s3' in self.bucket.connection._required_auth_capability():
            headers['_sha256'] = compute_hash(fp, hash_algorithm=hashlib.sha256)[0]
        headers['Expect'] = '100-Continue'
        headers = boto.utils.merge_meta(headers, self.metadata, provider)
        resp = self.bucket.connection.make_request(
            'PUT',
            self.bucket.name,
            self.name,
            headers,
            sender=sender,
            query_args=query_args
        )
        self.handle_version_headers(resp, force=True)
        self.handle_addl_headers(resp.getheaders())

    def should_retry(self, response, chunked_transfer=False, md5=None):
        provider = self.bucket.connection.provider

        if not chunked_transfer:
            if response.status in [500, 503]:
                # 500 & 503 can be plain retries.
                return True

            if response.getheader('location'):
                # If there's a redirect, plain retry.
                return True

        if 200 <= response.status <= 299:
            self.etag = response.getheader('etag')
            md5 = md5 or self.md5
            if isinstance(md5, bytes):
                md5 = md5.decode('utf-8')

            # If you use customer-provided encryption keys, the ETag value that
            # Amazon S3 returns in the response will not be the MD5 of the
            # object.
            server_side_encryption_customer_algorithm = response.getheader(
                'x-amz-server-side-encryption-customer-algorithm', None)
            if server_side_encryption_customer_algorithm is None:
                if self.etag != '"%s"' % md5:
                    raise provider.storage_data_error(
                        'ETag from S3 did not match computed MD5. '
                        '%s vs. %s' % (self.etag, self.md5))

            return True

        if response.status == 400:
            # The 400 must be trapped so the retry handler can check to
            # see if it was a timeout.
            # If ``RequestTimeout`` is present, we'll retry. Otherwise, bomb
            # out.
            body = response.read()
            err = provider.storage_response_error(
                response.status,
                response.reason,
                body
            )

            if err.error_code in ['RequestTimeout']:
                raise PleaseRetryException(
                    "Saw %s, retrying" % err.error_code,
                    response=response
                )

        return False

    def compute_md5(self, fp, size=None):
        """
        :type fp: file
        :param fp: File pointer to the file to MD5 hash.  The file
            pointer will be reset to the same position before the
            method returns.

        :type size: int
        :param size: (optional) The Maximum number of bytes to read
            from the file pointer (fp). This is useful when uploading
            a file in multiple parts where the file is being split
            in place into different parts. Less bytes may be available.
        """
        hex_digest, b64_digest, data_size = compute_md5(fp, size=size)
        # Returned values are MD5 hash, base64 encoded MD5 hash, and data size.
        # The internal implementation of compute_md5() needs to return the
        # data size but we don't want to return that value to the external
        # caller because it changes the class interface (i.e. it might
        # break some code) so we consume the third tuple value here and
        # return the remainder of the tuple to the caller, thereby preserving
        # the existing interface.
        self.size = data_size
        return (hex_digest, b64_digest)

    def set_contents_from_stream(self, fp, headers=None, replace=True,
                                 cb=None, num_cb=10, policy=None,
                                 reduced_redundancy=False, query_args=None,
                                 size=None):
        """
        Store an object using the name of the Key object as the key in
        cloud and the contents of the data stream pointed to by 'fp' as
        the contents.

        The stream object is not seekable and total size is not known.
        This has the implication that we can't specify the
        Content-Size and Content-MD5 in the header. So for huge
        uploads, the delay in calculating MD5 is avoided but with a
        penalty of inability to verify the integrity of the uploaded
        data.

        :type fp: file
        :param fp: the file whose contents are to be uploaded

        :type headers: dict
        :param headers: additional HTTP headers to be sent with the
            PUT request.

        :type replace: bool
        :param replace: If this parameter is False, the method will first check
            to see if an object exists in the bucket with the same key. If it
            does, it won't overwrite it. The default value is True which will
            overwrite the object.

        :type cb: function
        :param cb: a callback function that will be called to report
            progress on the upload. The callback should accept two integer
            parameters, the first representing the number of bytes that have
            been successfully transmitted to GS and the second representing the
            total number of bytes that need to be transmitted.

        :type num_cb: int
        :param num_cb: (optional) If a callback is specified with the
            cb parameter, this parameter determines the granularity of
            the callback by defining the maximum number of times the
            callback will be called during the file transfer.

        :type policy: :class:`boto.gs.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the new key
            in GS.

        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will set the storage
            class of the new Key to be REDUCED_REDUNDANCY. The Reduced
            Redundancy Storage (RRS) feature of S3, provides lower
            redundancy at lower storage cost.

        :type size: int
        :param size: (optional) The Maximum number of bytes to read from
            the file pointer (fp). This is useful when uploading a
            file in multiple parts where you are splitting the file up
            into different ranges to be uploaded. If not specified,
            the default behaviour is to read all bytes from the file
            pointer. Less bytes may be available.
        """

        provider = self.bucket.connection.provider
        if not provider.supports_chunked_transfer():
            raise BotoClientError('%s does not support chunked transfer'
                % provider.get_provider_name())

        # Name of the Object should be specified explicitly for Streams.
        if not self.name or self.name == '':
            raise BotoClientError('Cannot determine the destination '
                                'object name for the given stream')

        if headers is None:
            headers = {}
        if policy:
            headers[provider.acl_header] = policy

        if reduced_redundancy:
            self.storage_class = 'REDUCED_REDUNDANCY'
            if provider.storage_class_header:
                headers[provider.storage_class_header] = self.storage_class

        if self.bucket is not None:
            if not replace:
                if self.bucket.lookup(self.name):
                    return
            self.send_file(fp, headers, cb, num_cb, query_args,
                           chunked_transfer=True, size=size)

    def set_contents_from_file(self, fp, headers=None, replace=True,
                               cb=None, num_cb=10, policy=None, md5=None,
                               reduced_redundancy=False, query_args=None,
                               encrypt_key=False, size=None, rewind=False):
        """
        Store an object in S3 using the name of the Key object as the
        key in S3 and the contents of the file pointed to by 'fp' as the
        contents. The data is read from 'fp' from its current position until
        'size' bytes have been read or EOF.

        :type fp: file
        :param fp: the file whose contents to upload

        :type headers: dict
        :param headers: Additional HTTP headers that will be sent with
            the PUT request.

        :type replace: bool
        :param replace: If this parameter is False, the method will
            first check to see if an object exists in the bucket with
            the same key.  If it does, it won't overwrite it.  The
            default value is True which will overwrite the object.

        :type cb: function
        :param cb: a callback function that will be called to report
            progress on the upload.  The callback should accept two
            integer parameters, the first representing the number of
            bytes that have been successfully transmitted to S3 and
            the second representing the size of the to be transmitted
            object.

        :type num_cb: int
        :param num_cb: (optional) If a callback is specified with the
            cb parameter this parameter determines the granularity of
            the callback by defining the maximum number of times the
            callback will be called during the file transfer.

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the
            new key in S3.

        :type md5: A tuple containing the hexdigest version of the MD5
            checksum of the file as the first element and the
            Base64-encoded version of the plain checksum as the second
            element.  This is the same format returned by the
            compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason
            prior to upload, it's silly to have to do it twice so this
            param, if present, will be used as the MD5 values of the
            file.  Otherwise, the checksum will be computed.

        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will set the storage
            class of the new Key to be REDUCED_REDUNDANCY. The Reduced
            Redundancy Storage (RRS) feature of S3, provides lower
            redundancy at lower storage cost.

        :type encrypt_key: bool
        :param encrypt_key: If True, the new copy of the object will
            be encrypted on the server-side by S3 and will be stored
            in an encrypted form while at rest in S3.

        :type size: int
        :param size: (optional) The Maximum number of bytes to read
            from the file pointer (fp). This is useful when uploading
            a file in multiple parts where you are splitting the file
            up into different ranges to be uploaded. If not specified,
            the default behaviour is to read all bytes from the file
            pointer. Less bytes may be available.

        :type rewind: bool
        :param rewind: (optional) If True, the file pointer (fp) will
            be rewound to the start before any bytes are read from
            it. The default behaviour is False which reads from the
            current position of the file pointer (fp).

        :rtype: int
        :return: The number of bytes written to the key.
        """
        provider = self.bucket.connection.provider
        headers = headers or {}
        if policy:
            headers[provider.acl_header] = policy
        if encrypt_key:
            headers[provider.server_side_encryption_header] = 'AES256'

        if rewind:
            # caller requests reading from beginning of fp.
            fp.seek(0, os.SEEK_SET)
        else:
            # The following seek/tell/seek logic is intended
            # to detect applications using the older interface to
            # set_contents_from_file(), which automatically rewound the
            # file each time the Key was reused. This changed with commit
            # 14ee2d03f4665fe20d19a85286f78d39d924237e, to support uploads
            # split into multiple parts and uploaded in parallel, and at
            # the time of that commit this check was added because otherwise
            # older programs would get a success status and upload an empty
            # object. Unfortuantely, it's very inefficient for fp's implemented
            # by KeyFile (used, for example, by gsutil when copying between
            # providers). So, we skip the check for the KeyFile case.
            # TODO: At some point consider removing this seek/tell/seek
            # logic, after enough time has passed that it's unlikely any
            # programs remain that assume the older auto-rewind interface.
            if not isinstance(fp, KeyFile):
                spos = fp.tell()
                fp.seek(0, os.SEEK_END)
                if fp.tell() == spos:
                    fp.seek(0, os.SEEK_SET)
                    if fp.tell() != spos:
                        # Raise an exception as this is likely a programming
                        # error whereby there is data before the fp but nothing
                        # after it.
                        fp.seek(spos)
                        raise AttributeError('fp is at EOF. Use rewind option '
                                             'or seek() to data start.')
                # seek back to the correct position.
                fp.seek(spos)

        if reduced_redundancy:
            self.storage_class = 'REDUCED_REDUNDANCY'
            if provider.storage_class_header:
                headers[provider.storage_class_header] = self.storage_class
                # TODO - What if provider doesn't support reduced reduncancy?
                # What if different providers provide different classes?
        if hasattr(fp, 'name'):
            self.path = fp.name
        if self.bucket is not None:
            if not md5 and provider.supports_chunked_transfer():
                # defer md5 calculation to on the fly and
                # we don't know anything about size yet.
                chunked_transfer = True
                self.size = None
            else:
                chunked_transfer = False
                if isinstance(fp, KeyFile):
                    # Avoid EOF seek for KeyFile case as it's very inefficient.
                    key = fp.getkey()
                    size = key.size - fp.tell()
                    self.size = size
                    # At present both GCS and S3 use MD5 for the etag for
                    # non-multipart-uploaded objects. If the etag is 32 hex
                    # chars use it as an MD5, to avoid having to read the file
                    # twice while transferring.
                    if (re.match('^"[a-fA-F0-9]{32}"$', key.etag)):
                        etag = key.etag.strip('"')
                        md5 = (etag, base64.b64encode(binascii.unhexlify(etag)))
                if not md5:
                    # compute_md5() and also set self.size to actual
                    # size of the bytes read computing the md5.
                    md5 = self.compute_md5(fp, size)
                    # adjust size if required
                    size = self.size
                elif size:
                    self.size = size
                else:
                    # If md5 is provided, still need to size so
                    # calculate based on bytes to end of content
                    spos = fp.tell()
                    fp.seek(0, os.SEEK_END)
                    self.size = fp.tell() - spos
                    fp.seek(spos)
                    size = self.size
                self.md5 = md5[0]
                self.base64md5 = md5[1]

            if self.name is None:
                self.name = self.md5
            if not replace:
                if self.bucket.lookup(self.name):
                    return

            self.send_file(fp, headers=headers, cb=cb, num_cb=num_cb,
                           query_args=query_args,
                           chunked_transfer=chunked_transfer, size=size)
            # return number of bytes written.
            return self.size

    def set_contents_from_filename(self, filename, headers=None, replace=True,
                                   cb=None, num_cb=10, policy=None, md5=None,
                                   reduced_redundancy=False,
                                   encrypt_key=False):
        """
        Store an object in S3 using the name of the Key object as the
        key in S3 and the contents of the file named by 'filename'.
        See set_contents_from_file method for details about the
        parameters.

        :type filename: string
        :param filename: The name of the file that you want to put onto S3

        :type headers: dict
        :param headers: Additional headers to pass along with the
            request to AWS.

        :type replace: bool
        :param replace: If True, replaces the contents of the file
            if it already exists.

        :type cb: function
        :param cb: a callback function that will be called to report
            progress on the upload.  The callback should accept two
            integer parameters, the first representing the number of
            bytes that have been successfully transmitted to S3 and
            the second representing the size of the to be transmitted
            object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with the
            cb parameter this parameter determines the granularity of
            the callback by defining the maximum number of times the
            callback will be called during the file transfer.

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the
            new key in S3.

        :type md5: A tuple containing the hexdigest version of the MD5
            checksum of the file as the first element and the
            Base64-encoded version of the plain checksum as the second
            element.  This is the same format returned by the
            compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason
            prior to upload, it's silly to have to do it twice so this
            param, if present, will be used as the MD5 values of the
            file.  Otherwise, the checksum will be computed.

        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will set the storage
            class of the new Key to be REDUCED_REDUNDANCY. The Reduced
            Redundancy Storage (RRS) feature of S3, provides lower
            redundancy at lower storage cost.  :type encrypt_key: bool
            :param encrypt_key: If True, the new copy of the object
            will be encrypted on the server-side by S3 and will be
            stored in an encrypted form while at rest in S3.

        :rtype: int
        :return: The number of bytes written to the key.
        """
        with open(filename, 'rb') as fp:
            return self.set_contents_from_file(fp, headers, replace, cb,
                                               num_cb, policy, md5,
                                               reduced_redundancy,
                                               encrypt_key=encrypt_key)

    def set_contents_from_string(self, string_data, headers=None, replace=True,
                                 cb=None, num_cb=10, policy=None, md5=None,
                                 reduced_redundancy=False,
                                 encrypt_key=False):
        """
        Store an object in S3 using the name of the Key object as the
        key in S3 and the string 's' as the contents.
        See set_contents_from_file method for details about the
        parameters.

        :type headers: dict
        :param headers: Additional headers to pass along with the
            request to AWS.

        :type replace: bool
        :param replace: If True, replaces the contents of the file if
            it already exists.

        :type cb: function
        :param cb: a callback function that will be called to report
            progress on the upload.  The callback should accept two
            integer parameters, the first representing the number of
            bytes that have been successfully transmitted to S3 and
            the second representing the size of the to be transmitted
            object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with the
            cb parameter this parameter determines the granularity of
            the callback by defining the maximum number of times the
            callback will be called during the file transfer.

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the
            new key in S3.

        :type md5: A tuple containing the hexdigest version of the MD5
            checksum of the file as the first element and the
            Base64-encoded version of the plain checksum as the second
            element.  This is the same format returned by the
            compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason
            prior to upload, it's silly to have to do it twice so this
            param, if present, will be used as the MD5 values of the
            file.  Otherwise, the checksum will be computed.

        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will set the storage
            class of the new Key to be REDUCED_REDUNDANCY. The Reduced
            Redundancy Storage (RRS) feature of S3, provides lower
            redundancy at lower storage cost.

        :type encrypt_key: bool
        :param encrypt_key: If True, the new copy of the object will
            be encrypted on the server-side by S3 and will be stored
            in an encrypted form while at rest in S3.
        """
        if not isinstance(string_data, bytes):
            string_data = string_data.encode("utf-8")
        fp = BytesIO(string_data)
        r = self.set_contents_from_file(fp, headers, replace, cb, num_cb,
                                        policy, md5, reduced_redundancy,
                                        encrypt_key=encrypt_key)
        fp.close()
        return r

    def get_file(self, fp, headers=None, cb=None, num_cb=10,
                 torrent=False, version_id=None, override_num_retries=None,
                 response_headers=None):
        """
        Retrieves a file from an S3 Key

        :type fp: file
        :param fp: File pointer to put the data into

        :type headers: string
        :param: headers to send when retrieving the files

        :type cb: function
        :param cb: a callback function that will be called to report
            progress on the upload.  The callback should accept two
            integer parameters, the first representing the number of
            bytes that have been successfully transmitted to S3 and
            the second representing the size of the to be transmitted
            object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with the
            cb parameter this parameter determines the granularity of
            the callback by defining the maximum number of times the
            callback will be called during the file transfer.

        :type torrent: bool
        :param torrent: Flag for whether to get a torrent for the file

        :type override_num_retries: int
        :param override_num_retries: If not None will override configured
            num_retries parameter for underlying GET.

        :type response_headers: dict
        :param response_headers: A dictionary containing HTTP
            headers/values that will override any headers associated
            with the stored object in the response.  See
            http://goo.gl/EWOPb for details.

        :type version_id: str
        :param version_id: The ID of a particular version of the object.
            If this parameter is not supplied but the Key object has
            a ``version_id`` attribute, that value will be used when
            retrieving the object.  You can set the Key object's
            ``version_id`` attribute to None to always grab the latest
            version from a version-enabled bucket.
        """
        self._get_file_internal(fp, headers=headers, cb=cb, num_cb=num_cb,
                                torrent=torrent, version_id=version_id,
                                override_num_retries=override_num_retries,
                                response_headers=response_headers,
                                hash_algs=None,
                                query_args=None)

    def _get_file_internal(self, fp, headers=None, cb=None, num_cb=10,
                 torrent=False, version_id=None, override_num_retries=None,
                 response_headers=None, hash_algs=None, query_args=None):
        if headers is None:
            headers = {}
        save_debug = self.bucket.connection.debug
        if self.bucket.connection.debug == 1:
            self.bucket.connection.debug = 0

        query_args = query_args or []
        if torrent:
            query_args.append('torrent')

        if hash_algs is None and not torrent:
            hash_algs = {'md5': hashlib.md5}
        digesters = dict((alg, hash_algs[alg]()) for alg in hash_algs or {})

        # If a version_id is passed in, use that.  If not, check to see
        # if the Key object has an explicit version_id and, if so, use that.
        # Otherwise, don't pass a version_id query param.
        if version_id is None:
            version_id = self.version_id
        if version_id:
            query_args.append('versionId=%s' % version_id)
        if response_headers:
            for key in response_headers:
                query_args.append('%s=%s' % (
                    key, urllib.parse.quote(response_headers[key])))
        query_args = '&'.join(query_args)
        self.open('r', headers, query_args=query_args,
                  override_num_retries=override_num_retries)

        data_len = 0
        if cb:
            if self.size is None:
                cb_size = 0
            else:
                cb_size = self.size
            if self.size is None and num_cb != -1:
                # If size is not available due to chunked transfer for example,
                # we'll call the cb for every 1MB of data transferred.
                cb_count = (1024 * 1024) / self.BufferSize
            elif num_cb > 1:
                cb_count = int(math.ceil(cb_size/self.BufferSize/(num_cb-1.0)))
            elif num_cb < 0:
                cb_count = -1
            else:
                cb_count = 0
            i = 0
            cb(data_len, cb_size)
        try:
            for bytes in self:
                fp.write(bytes)
                data_len += len(bytes)
                for alg in digesters:
                    digesters[alg].update(bytes)
                if cb:
                    if cb_size > 0 and data_len >= cb_size:
                        break
                    i += 1
                    if i == cb_count or cb_count == -1:
                        cb(data_len, cb_size)
                        i = 0
        except IOError as e:
            if e.errno == errno.ENOSPC:
                raise StorageDataError('Out of space for destination file '
                                       '%s' % fp.name)
            raise
        if cb and (cb_count <= 1 or i > 0) and data_len > 0:
            cb(data_len, cb_size)
        for alg in digesters:
          self.local_hashes[alg] = digesters[alg].digest()
        if self.size is None and not torrent and "Range" not in headers:
            self.size = data_len
        self.close()
        self.bucket.connection.debug = save_debug

    def get_torrent_file(self, fp, headers=None, cb=None, num_cb=10):
        """
        Get a torrent file (see to get_file)

        :type fp: file
        :param fp: The file pointer of where to put the torrent

        :type headers: dict
        :param headers: Headers to be passed

        :type cb: function
        :param cb: a callback function that will be called to report
            progress on the upload.  The callback should accept two
            integer parameters, the first representing the number of
            bytes that have been successfully transmitted to S3 and
            the second representing the size of the to be transmitted
            object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with the
            cb parameter this parameter determines the granularity of
            the callback by defining the maximum number of times the
            callback will be called during the file transfer.

        """
        return self.get_file(fp, headers, cb, num_cb, torrent=True)

    def get_contents_to_file(self, fp, headers=None,
                             cb=None, num_cb=10,
                             torrent=False,
                             version_id=None,
                             res_download_handler=None,
                             response_headers=None):
        """
        Retrieve an object from S3 using the name of the Key object as the
        key in S3.  Write the contents of the object to the file pointed
        to by 'fp'.

        :type fp: File -like object
        :param fp:

        :type headers: dict
        :param headers: additional HTTP headers that will be sent with
            the GET request.

        :type cb: function
        :param cb: a callback function that will be called to report
            progress on the upload.  The callback should accept two
            integer parameters, the first representing the number of
            bytes that have been successfully transmitted to S3 and
            the second representing the size of the to be transmitted
            object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with the
            cb parameter this parameter determines the granularity of
            the callback by defining the maximum number of times the
            callback will be called during the file transfer.

        :type torrent: bool
        :param torrent: If True, returns the contents of a torrent
            file as a string.

        :type res_upload_handler: ResumableDownloadHandler
        :param res_download_handler: If provided, this handler will
            perform the download.

        :type response_headers: dict
        :param response_headers: A dictionary containing HTTP
            headers/values that will override any headers associated
            with the stored object in the response.  See
            http://goo.gl/EWOPb for details.

        :type version_id: str
        :param version_id: The ID of a particular version of the object.
            If this parameter is not supplied but the Key object has
            a ``version_id`` attribute, that value will be used when
            retrieving the object.  You can set the Key object's
            ``version_id`` attribute to None to always grab the latest
            version from a version-enabled bucket.
        """
        if self.bucket is not None:
            if res_download_handler:
                res_download_handler.get_file(self, fp, headers, cb, num_cb,
                                              torrent=torrent,
                                              version_id=version_id)
            else:
                self.get_file(fp, headers, cb, num_cb, torrent=torrent,
                              version_id=version_id,
                              response_headers=response_headers)

    def get_contents_to_filename(self, filename, headers=None,
                                 cb=None, num_cb=10,
                                 torrent=False,
                                 version_id=None,
                                 res_download_handler=None,
                                 response_headers=None):
        """
        Retrieve an object from S3 using the name of the Key object as the
        key in S3.  Store contents of the object to a file named by 'filename'.
        See get_contents_to_file method for details about the
        parameters.

        :type filename: string
        :param filename: The filename of where to put the file contents

        :type headers: dict
        :param headers: Any additional headers to send in the request

        :type cb: function
        :param cb: a callback function that will be called to report
            progress on the upload.  The callback should accept two
            integer parameters, the first representing the number of
            bytes that have been successfully transmitted to S3 and
            the second representing the size of the to be transmitted
            object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with the
            cb parameter this parameter determines the granularity of
            the callback by defining the maximum number of times the
            callback will be called during the file transfer.

        :type torrent: bool
        :param torrent: If True, returns the contents of a torrent file
            as a string.

        :type res_upload_handler: ResumableDownloadHandler
        :param res_download_handler: If provided, this handler will
            perform the download.

        :type response_headers: dict
        :param response_headers: A dictionary containing HTTP
            headers/values that will override any headers associated
            with the stored object in the response.  See
            http://goo.gl/EWOPb for details.

        :type version_id: str
        :param version_id: The ID of a particular version of the object.
            If this parameter is not supplied but the Key object has
            a ``version_id`` attribute, that value will be used when
            retrieving the object.  You can set the Key object's
            ``version_id`` attribute to None to always grab the latest
            version from a version-enabled bucket.
        """
        try:
            with open(filename, 'wb') as fp:
                self.get_contents_to_file(fp, headers, cb, num_cb,
                                          torrent=torrent,
                                          version_id=version_id,
                                          res_download_handler=res_download_handler,
                                          response_headers=response_headers)
        except Exception:
            os.remove(filename)
            raise
        # if last_modified date was sent from s3, try to set file's timestamp
        if self.last_modified is not None:
            try:
                modified_tuple = email.utils.parsedate_tz(self.last_modified)
                modified_stamp = int(email.utils.mktime_tz(modified_tuple))
                os.utime(fp.name, (modified_stamp, modified_stamp))
            except Exception:
                pass

    def get_contents_as_string(self, headers=None,
                               cb=None, num_cb=10,
                               torrent=False,
                               version_id=None,
                               response_headers=None, encoding=None):
        """
        Retrieve an object from S3 using the name of the Key object as the
        key in S3.  Return the contents of the object as a string.
        See get_contents_to_file method for details about the
        parameters.

        :type headers: dict
        :param headers: Any additional headers to send in the request

        :type cb: function
        :param cb: a callback function that will be called to report
            progress on the upload.  The callback should accept two
            integer parameters, the first representing the number of
            bytes that have been successfully transmitted to S3 and
            the second representing the size of the to be transmitted
            object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with the
            cb parameter this parameter determines the granularity of
            the callback by defining the maximum number of times the
            callback will be called during the file transfer.

        :type torrent: bool
        :param torrent: If True, returns the contents of a torrent file
            as a string.

        :type response_headers: dict
        :param response_headers: A dictionary containing HTTP
            headers/values that will override any headers associated
            with the stored object in the response.  See
            http://goo.gl/EWOPb for details.

        :type version_id: str
        :param version_id: The ID of a particular version of the object.
            If this parameter is not supplied but the Key object has
            a ``version_id`` attribute, that value will be used when
            retrieving the object.  You can set the Key object's
            ``version_id`` attribute to None to always grab the latest
            version from a version-enabled bucket.

        :type encoding: str
        :param encoding: The text encoding to use, such as ``utf-8``
            or ``iso-8859-1``. If set, then a string will be returned.
            Defaults to ``None`` and returns bytes.

        :rtype: bytes or str
        :returns: The contents of the file as bytes or a string
        """
        fp = BytesIO()
        self.get_contents_to_file(fp, headers, cb, num_cb, torrent=torrent,
                                  version_id=version_id,
                                  response_headers=response_headers)
        value = fp.getvalue()

        if encoding is not None:
            value = value.decode(encoding)

        return value

    def add_email_grant(self, permission, email_address, headers=None):
        """
        Convenience method that provides a quick way to add an email grant
        to a key. This method retrieves the current ACL, creates a new
        grant based on the parameters passed in, adds that grant to the ACL
        and then PUT's the new ACL back to S3.

        :type permission: string
        :param permission: The permission being granted. Should be one of:
            (READ, WRITE, READ_ACP, WRITE_ACP, FULL_CONTROL).

        :type email_address: string
        :param email_address: The email address associated with the AWS
            account your are granting the permission to.

        :type recursive: boolean
        :param recursive: A boolean value to controls whether the
            command will apply the grant to all keys within the bucket
            or not.  The default value is False.  By passing a True
            value, the call will iterate through all keys in the
            bucket and apply the same grant to each key.  CAUTION: If
            you have a lot of keys, this could take a long time!
        """
        policy = self.get_acl(headers=headers)
        policy.acl.add_email_grant(permission, email_address)
        self.set_acl(policy, headers=headers)

    def add_user_grant(self, permission, user_id, headers=None,
                       display_name=None):
        """
        Convenience method that provides a quick way to add a canonical
        user grant to a key.  This method retrieves the current ACL,
        creates a new grant based on the parameters passed in, adds that
        grant to the ACL and then PUT's the new ACL back to S3.

        :type permission: string
        :param permission: The permission being granted. Should be one of:
            (READ, WRITE, READ_ACP, WRITE_ACP, FULL_CONTROL).

        :type user_id: string
        :param user_id: The canonical user id associated with the AWS
            account your are granting the permission to.

        :type display_name: string
        :param display_name: An option string containing the user's
            Display Name.  Only required on Walrus.
        """
        policy = self.get_acl(headers=headers)
        policy.acl.add_user_grant(permission, user_id,
                                  display_name=display_name)
        self.set_acl(policy, headers=headers)

    def _normalize_metadata(self, metadata):
        if type(metadata) == set:
            norm_metadata = set()
            for k in metadata:
                norm_metadata.add(k.lower())
        else:
            norm_metadata = {}
            for k in metadata:
                norm_metadata[k.lower()] = metadata[k]
        return norm_metadata

    def _get_remote_metadata(self, headers=None):
        """
        Extracts metadata from existing URI into a dict, so we can
        overwrite/delete from it to form the new set of metadata to apply to a
        key.
        """
        metadata = {}
        for underscore_name in self._underscore_base_user_settable_fields:
            if hasattr(self, underscore_name):
                value = getattr(self, underscore_name)
                if value:
                    # Generate HTTP field name corresponding to "_" named field.
                    field_name = underscore_name.replace('_', '-')
                    metadata[field_name.lower()] = value
        # self.metadata contains custom metadata, which are all user-settable.
        prefix = self.provider.metadata_prefix
        for underscore_name in self.metadata:
            field_name = underscore_name.replace('_', '-')
            metadata['%s%s' % (prefix, field_name.lower())] = (
                self.metadata[underscore_name])
        return metadata

    def set_remote_metadata(self, metadata_plus, metadata_minus, preserve_acl,
                            headers=None):
        metadata_plus = self._normalize_metadata(metadata_plus)
        metadata_minus = self._normalize_metadata(metadata_minus)
        metadata = self._get_remote_metadata()
        metadata.update(metadata_plus)
        for h in metadata_minus:
            if h in metadata:
                del metadata[h]
        src_bucket = self.bucket
        # Boto prepends the meta prefix when adding headers, so strip prefix in
        # metadata before sending back in to copy_key() call.
        rewritten_metadata = {}
        for h in metadata:
            if (h.startswith('x-goog-meta-') or h.startswith('x-amz-meta-')):
                rewritten_h = (h.replace('x-goog-meta-', '')
                               .replace('x-amz-meta-', ''))
            else:
                rewritten_h = h
            rewritten_metadata[rewritten_h] = metadata[h]
        metadata = rewritten_metadata
        src_bucket.copy_key(self.name, self.bucket.name, self.name,
                            metadata=metadata, preserve_acl=preserve_acl,
                            headers=headers)

    def restore(self, days, headers=None):
        """Restore an object from an archive.

        :type days: int
        :param days: The lifetime of the restored object (must
            be at least 1 day).  If the object is already restored
            then this parameter can be used to readjust the lifetime
            of the restored object.  In this case, the days
            param is with respect to the initial time of the request.
            If the object has not been restored, this param is with
            respect to the completion time of the request.

        """
        response = self.bucket.connection.make_request(
            'POST', self.bucket.name, self.name,
            data=self.RestoreBody % days,
            headers=headers, query_args='restore')
        if response.status not in (200, 202):
            provider = self.bucket.connection.provider
            raise provider.storage_response_error(response.status,
                                                  response.reason,
                                                  response.read())
