# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
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

import mimetypes
import os
import re
import rfc822
import StringIO
import base64
import urllib
import boto.utils
from boto.exception import BotoClientError
from boto.provider import Provider
from boto.s3.user import User
from boto import UserAgent
from boto.utils import compute_md5
try:
    from hashlib import md5
except ImportError:
    from md5 import md5


class Key(object):

    DefaultContentType = 'application/octet-stream'

    BufferSize = 8192

    def __init__(self, bucket=None, name=None):
        self.bucket = bucket
        self.name = name
        self.metadata = {}
        self.cache_control = None
        self.content_type = self.DefaultContentType
        self.content_encoding = None
        self.filename = None
        self.etag = None
        self.is_latest = False
        self.last_modified = None
        self.owner = None
        self.storage_class = 'STANDARD'
        self.md5 = None
        self.base64md5 = None
        self.path = None
        self.resp = None
        self.mode = None
        self.size = None
        self.version_id = None
        self.source_version_id = None
        self.delete_marker = False
        self.encrypted = None

    def __repr__(self):
        if self.bucket:
            return '<Key: %s,%s>' % (self.bucket.name, self.name)
        else:
            return '<Key: None,%s>' % self.name

    def __getattr__(self, name):
        if name == 'key':
            return self.name
        else:
            raise AttributeError

    def __setattr__(self, name, value):
        if name == 'key':
            self.__dict__['name'] = value
        else:
            self.__dict__[name] = value

    def __iter__(self):
        return self

    @property
    def provider(self):
        provider = None
        if self.bucket:
            if self.bucket.connection:
                provider = self.bucket.connection.provider
        return provider

    def get_md5_from_hexdigest(self, md5_hexdigest):
        """
        A utility function to create the 2-tuple (md5hexdigest, base64md5)
        from just having a precalculated md5_hexdigest.
        """
        import binascii
        digest = binascii.unhexlify(md5_hexdigest)
        base64md5 = base64.encodestring(digest)
        if base64md5[-1] == '\n':
            base64md5 = base64md5[0:-1]
        return (md5_hexdigest, base64md5)

    def handle_encryption_headers(self, resp):
        provider = self.bucket.connection.provider
        if provider.server_side_encryption_header:
            self.encrypted = resp.getheader(provider.server_side_encryption_header, None)
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

    def open_read(self, headers=None, query_args='',
                  override_num_retries=None, response_headers=None):
        """
        Open this key for reading

        :type headers: dict
        :param headers: Headers to pass in the web request

        :type query_args: string
        :param query_args: Arguments to pass in the query string (ie, 'torrent')

        :type override_num_retries: int
        :param override_num_retries: If not None will override configured
                                     num_retries parameter for underlying GET.

        :type response_headers: dict
        :param response_headers: A dictionary containing HTTP headers/values
                                 that will override any headers associated with
                                 the stored object in the response.
                                 See http://goo.gl/EWOPb for details.
        """
        if self.resp == None:
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
            for name,value in response_headers.items():
                # To get correct size for Range GETs, use Content-Range
                # header if one was returned. If not, use Content-Length
                # header.
                if (name.lower() == 'content-length' and
                    'Content-Range' not in response_headers):
                    self.size = int(value)
                elif name.lower() == 'content-range':
                    end_range = re.sub('.*/(.*)', '\\1', value)
                    self.size = int(end_range)
                elif name.lower() == 'etag':
                    self.etag = value
                elif name.lower() == 'content-type':
                    self.content_type = value
                elif name.lower() == 'content-encoding':
                    self.content_encoding = value
                elif name.lower() == 'last-modified':
                    self.last_modified = value
                elif name.lower() == 'cache-control':
                    self.cache_control = value
            self.handle_version_headers(self.resp)
            self.handle_encryption_headers(self.resp)

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
    def close(self):
        if self.resp:
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

    def read(self, size=0):
        self.open_read()
        if size == 0:
            data = self.resp.read()
        else:
            data = self.resp.read(size)
        if not data:
            self.close()
        return data

    def change_storage_class(self, new_storage_class, dst_bucket=None):
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
                           provided the current bucket of the key
                           will be used.

        """
        if new_storage_class == 'STANDARD':
            return self.copy(self.bucket.name, self.name,
                             reduced_redundancy=False, preserve_acl=True)
        elif new_storage_class == 'REDUCED_REDUNDANCY':
            return self.copy(self.bucket.name, self.name,
                             reduced_redundancy=True, preserve_acl=True)
        else:
            raise BotoClientError('Invalid storage class: %s' %
                                  new_storage_class)

    def copy(self, dst_bucket, dst_key, metadata=None,
             reduced_redundancy=False, preserve_acl=False,
             encrypt_key=False):
        """
        Copy this Key to another bucket.

        :type dst_bucket: string
        :param dst_bucket: The name of the destination bucket

        :type dst_key: string
        :param dst_key: The name of the destination key

        :type metadata: dict
        :param metadata: Metadata to be associated with new key.
                         If metadata is supplied, it will replace the
                         metadata of the source key being copied.
                         If no metadata is supplied, the source key's
                         metadata will be copied to the new key.

        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will force the storage
                                   class of the new Key to be
                                   REDUCED_REDUNDANCY regardless of the
                                   storage class of the key being copied.
                                   The Reduced Redundancy Storage (RRS)
                                   feature of S3, provides lower
                                   redundancy at lower storage cost.

        :type preserve_acl: bool
        :param preserve_acl: If True, the ACL from the source key
                             will be copied to the destination
                             key.  If False, the destination key
                             will have the default ACL.
                             Note that preserving the ACL in the
                             new key object will require two
                             additional API calls to S3, one to
                             retrieve the current ACL and one to
                             set that ACL on the new object.  If
                             you don't care about the ACL, a value
                             of False will be significantly more
                             efficient.

        :type encrypt_key: bool
        :param encrypt_key: If True, the new copy of the object will
                            be encrypted on the server-side by S3 and
                            will be stored in an encrypted form while
                            at rest in S3.
                            
        :rtype: :class:`boto.s3.key.Key` or subclass
        :returns: An instance of the newly created key object
        """
        dst_bucket = self.bucket.connection.lookup(dst_bucket)
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

    def exists(self):
        """
        Returns True if the key exists

        :rtype: bool
        :return: Whether the key exists on S3
        """
        return bool(self.bucket.lookup(self.name))

    def delete(self):
        """
        Delete this key from S3
        """
        return self.bucket.delete_key(self.name, version_id=self.version_id)

    def get_metadata(self, name):
        return self.metadata.get(name)

    def set_metadata(self, name, value):
        self.metadata[name] = value

    def update_metadata(self, d):
        self.metadata.update(d)

    # convenience methods for setting/getting ACL
    def set_acl(self, acl_str, headers=None):
        if self.bucket != None:
            self.bucket.set_acl(acl_str, self.name, headers=headers)

    def get_acl(self, headers=None):
        if self.bucket != None:
            return self.bucket.get_acl(self.name, headers=headers)

    def get_xml_acl(self, headers=None):
        if self.bucket != None:
            return self.bucket.get_xml_acl(self.name, headers=headers)

    def set_xml_acl(self, acl_str, headers=None):
        if self.bucket != None:
            return self.bucket.set_xml_acl(acl_str, self.name, headers=headers)

    def set_canned_acl(self, acl_str, headers=None):
        return self.bucket.set_canned_acl(acl_str, self.name, headers)

    def make_public(self, headers=None):
        return self.bucket.set_canned_acl('public-read', self.name, headers)

    def generate_url(self, expires_in, method='GET', headers=None,
                     query_auth=True, force_http=False, response_headers=None,
                     expires_in_absolute=False):
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

        :rtype: string
        :return: The URL to access the key
        """
        return self.bucket.connection.generate_url(expires_in, method,
                                                   self.bucket.name, self.name,
                                                   headers, query_auth,
                                                   force_http,
                                                   response_headers,
                                                   expires_in_absolute)

    def send_file(self, fp, headers=None, cb=None, num_cb=10,
                  query_args=None, chunked_transfer=False):
        """
        Upload a file to a key into a bucket on S3.

        :type fp: file
        :param fp: The file pointer to upload

        :type headers: dict
        :param headers: The headers to pass along with the PUT request

        :type cb: function
        :param cb: a callback function that will be called to report
                   progress on the upload.  The callback should accept
                   two integer parameters, the first representing the
                   number of bytes that have been successfully
                   transmitted to S3 and the second representing the
                   size of the to be transmitted object.

        :type num_cb: int
        :param num_cb: (optional) If a callback is specified with the cb
                       parameter this parameter determines the granularity
                       of the callback by defining the maximum number of
                       times the callback will be called during the file
                       transfer. Providing a negative integer will cause
                       your callback to be called with each buffer read.

        """
        provider = self.bucket.connection.provider

        def sender(http_conn, method, path, data, headers):
            http_conn.putrequest(method, path)
            for key in headers:
                http_conn.putheader(key, headers[key])
            http_conn.endheaders()
            if chunked_transfer:
                # MD5 for the stream has to be calculated on the fly, as
                # we don't know the size of the stream before hand.
                m = md5()
            else:
                fp.seek(0)

            save_debug = self.bucket.connection.debug
            self.bucket.connection.debug = 0
            # If the debuglevel < 3 we don't want to show connection
            # payload, so turn off HTTP connection-level debug output (to
            # be restored below).
            # Use the getattr approach to allow this to work in AppEngine.
            if getattr(http_conn, 'debuglevel', 0) < 3:
                http_conn.set_debuglevel(0)
            if cb:
                if chunked_transfer:
                    # For chunked Transfer, we call the cb for every 1MB
                    # of data transferred.
                    cb_count = (1024 * 1024)/self.BufferSize
                    self.size = 0
                elif num_cb > 2:
                    cb_count = self.size / self.BufferSize / (num_cb-2)
                elif num_cb < 0:
                    cb_count = -1
                else:
                    cb_count = 0
                i = total_bytes = 0
                cb(total_bytes, self.size)
            l = fp.read(self.BufferSize)
            while len(l) > 0:
                if chunked_transfer:
                    http_conn.send('%x;\r\n' % len(l))
                    http_conn.send(l)
                    http_conn.send('\r\n')
                else:
                    http_conn.send(l)
                if cb:
                    total_bytes += len(l)
                    i += 1
                    if i == cb_count or cb_count == -1:
                        cb(total_bytes, self.size)
                        i = 0
                if chunked_transfer:
                    m.update(l)
                l = fp.read(self.BufferSize)
            if chunked_transfer:
                http_conn.send('0\r\n')
                http_conn.send('\r\n')
                if cb:
                    self.size = total_bytes
                # Get the md5 which is calculated on the fly.
                self.md5 = m.hexdigest()
            else:
                fp.seek(0)
            if cb:
                cb(total_bytes, self.size)
            response = http_conn.getresponse()
            body = response.read()
            http_conn.set_debuglevel(save_debug)
            self.bucket.connection.debug = save_debug
            if ((response.status == 500 or response.status == 503 or
                    response.getheader('location')) and not chunked_transfer):
                # we'll try again.
                return response
            elif response.status >= 200 and response.status <= 299:
                self.etag = response.getheader('etag')
                if self.etag != '"%s"'  % self.md5:
                    raise provider.storage_data_error(
                        'ETag from S3 did not match computed MD5')
                return response
            else:
                raise provider.storage_response_error(
                    response.status, response.reason, body)

        if not headers:
            headers = {}
        else:
            headers = headers.copy()
        headers['User-Agent'] = UserAgent
        if self.base64md5:
            headers['Content-MD5'] = self.base64md5
        if self.storage_class != 'STANDARD':
            headers[provider.storage_class_header] = self.storage_class
        if headers.has_key('Content-Encoding'):
            self.content_encoding = headers['Content-Encoding']
        if headers.has_key('Content-Type'):
            # Some use cases need to suppress sending of the Content-Type 
            # header and depend on the receiving server to set the content
            # type. This can be achieved by setting headers['Content-Type'] 
            # to None when calling this method.
            if headers['Content-Type']:
                self.content_type = headers['Content-Type']
            else:
                # Delete null Content-Type value to skip sending that header.
                del headers['Content-Type']
        elif self.path:
            self.content_type = mimetypes.guess_type(self.path)[0]
            if self.content_type == None:
                self.content_type = self.DefaultContentType
            headers['Content-Type'] = self.content_type
        else:
            headers['Content-Type'] = self.content_type
        if not chunked_transfer:
            headers['Content-Length'] = str(self.size)
        headers['Expect'] = '100-Continue'
        headers = boto.utils.merge_meta(headers, self.metadata, provider)
        resp = self.bucket.connection.make_request('PUT', self.bucket.name,
                                                   self.name, headers,
                                                   sender=sender,
                                                   query_args=query_args)
        self.handle_version_headers(resp, force=True)

    def compute_md5(self, fp):
        """
        :type fp: file
        :param fp: File pointer to the file to MD5 hash.  The file pointer
                   will be reset to the beginning of the file before the
                   method returns.

        :rtype: tuple
        :return: A tuple containing the hex digest version of the MD5 hash
                 as the first element and the base64 encoded version of the
                 plain digest as the second element.
        """
        tup = compute_md5(fp)
        # Returned values are MD5 hash, base64 encoded MD5 hash, and file size.
        # The internal implementation of compute_md5() needs to return the 
        # file size but we don't want to return that value to the external 
        # caller because it changes the class interface (i.e. it might        
        # break some code) so we consume the third tuple value here and 
        # return the remainder of the tuple to the caller, thereby preserving 
        # the existing interface.
        self.size = tup[2]
        return tup[0:2]

    def set_contents_from_stream(self, fp, headers=None, replace=True,
                                 cb=None, num_cb=10, policy=None,
                                 reduced_redundancy=False, query_args=None):
        """
        Store an object using the name of the Key object as the key in
        cloud and the contents of the data stream pointed to by 'fp' as
        the contents.
        The stream object is not seekable and total size is not known.
        This has the implication that we can't specify the Content-Size and
        Content-MD5 in the header. So for huge uploads, the delay in calculating
        MD5 is avoided but with a penalty of inability to verify the integrity
        of the uploaded data.

        :type fp: file
        :param fp: the file whose contents are to be uploaded

        :type headers: dict
        :param headers: additional HTTP headers to be sent with the PUT request.

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
        :param num_cb: (optional) If a callback is specified with the cb
            parameter, this parameter determines the granularity of the callback
            by defining the maximum number of times the callback will be called
            during the file transfer.

        :type policy: :class:`boto.gs.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the new key
            in GS.

        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will set the storage
                                   class of the new Key to be
                                   REDUCED_REDUNDANCY. The Reduced Redundancy
                                   Storage (RRS) feature of S3, provides lower
                                   redundancy at lower storage cost.
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

        # Set the Transfer Encoding for Streams.
        headers['Transfer-Encoding'] = 'chunked'

        if reduced_redundancy:
            self.storage_class = 'REDUCED_REDUNDANCY'
            if provider.storage_class_header:
                headers[provider.storage_class_header] = self.storage_class

        if self.bucket != None:
            if not replace:
                k = self.bucket.lookup(self.name)
                if k:
                    return
            self.send_file(fp, headers, cb, num_cb, query_args,
                                            chunked_transfer=True)

    def set_contents_from_file(self, fp, headers=None, replace=True,
                               cb=None, num_cb=10, policy=None, md5=None,
                               reduced_redundancy=False, query_args=None,
                               encrypt_key=False):
        """
        Store an object in S3 using the name of the Key object as the
        key in S3 and the contents of the file pointed to by 'fp' as the
        contents.

        :type fp: file
        :param fp: the file whose contents to upload

        :type headers: dict
        :param headers: Additional HTTP headers that will be sent with
                        the PUT request.

        :type replace: bool
        :param replace: If this parameter is False, the method
                        will first check to see if an object exists in the
                        bucket with the same key.  If it does, it won't
                        overwrite it.  The default value is True which will
                        overwrite the object.

        :type cb: function
        :param cb: a callback function that will be called to report
                   progress on the upload.  The callback should accept
                   two integer parameters, the first representing the
                   number of bytes that have been successfully
                   transmitted to S3 and the second representing the
                   size of the to be transmitted object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with the cb
                       parameter this parameter determines the granularity
                       of the callback by defining the maximum number of
                       times the callback will be called during the
                       file transfer.

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the
                       new key in S3.

        :type md5: A tuple containing the hexdigest version of the MD5
                   checksum of the file as the first element and the
                   Base64-encoded version of the plain checksum as the
                   second element.  This is the same format returned by
                   the compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason prior
                    to upload, it's silly to have to do it twice so this
                    param, if present, will be used as the MD5 values of
                    the file.  Otherwise, the checksum will be computed.

        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will set the storage
                                   class of the new Key to be
                                   REDUCED_REDUNDANCY. The Reduced Redundancy
                                   Storage (RRS) feature of S3, provides lower
                                   redundancy at lower storage cost.

        :type encrypt_key: bool
        :param encrypt_key: If True, the new copy of the object will
                            be encrypted on the server-side by S3 and
                            will be stored in an encrypted form while
                            at rest in S3.
        """
        provider = self.bucket.connection.provider
        if headers is None:
            headers = {}
        if policy:
            headers[provider.acl_header] = policy
        if encrypt_key:
            headers[provider.server_side_encryption_header] = 'AES256'

        if reduced_redundancy:
            self.storage_class = 'REDUCED_REDUNDANCY'
            if provider.storage_class_header:
                headers[provider.storage_class_header] = self.storage_class
                # TODO - What if provider doesn't support reduced reduncancy?
                # What if different providers provide different classes?
        if hasattr(fp, 'name'):
            self.path = fp.name
        if self.bucket != None:
            if not md5:
                md5 = self.compute_md5(fp)
            else:
                # even if md5 is provided, still need to set size of content
                fp.seek(0, 2)
                self.size = fp.tell()
                fp.seek(0)
            self.md5 = md5[0]
            self.base64md5 = md5[1]
            if self.name == None:
                self.name = self.md5
            if not replace:
                k = self.bucket.lookup(self.name)
                if k:
                    return
            self.send_file(fp, headers, cb, num_cb, query_args)

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
                   progress on the upload.  The callback should accept
                   two integer parameters, the first representing the
                   number of bytes that have been successfully
                   transmitted to S3 and the second representing the
                   size of the to be transmitted object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with
                       the cb parameter this parameter determines the
                       granularity of the callback by defining
                       the maximum number of times the callback will
                       be called during the file transfer.

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the
                       new key in S3.

        :type md5: A tuple containing the hexdigest version of the MD5
                   checksum of the file as the first element and the
                   Base64-encoded version of the plain checksum as the
                   second element.  This is the same format returned by
                   the compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason prior
                    to upload, it's silly to have to do it twice so this
                    param, if present, will be used as the MD5 values
                    of the file.  Otherwise, the checksum will be computed.

        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will set the storage
                                   class of the new Key to be
                                   REDUCED_REDUNDANCY. The Reduced Redundancy
                                   Storage (RRS) feature of S3, provides lower
                                   redundancy at lower storage cost.
        :type encrypt_key: bool
        :param encrypt_key: If True, the new copy of the object will
                            be encrypted on the server-side by S3 and
                            will be stored in an encrypted form while
                            at rest in S3.
        """
        fp = open(filename, 'rb')
        self.set_contents_from_file(fp, headers, replace, cb, num_cb,
                                    policy, md5, reduced_redundancy,
                                    encrypt_key=encrypt_key)
        fp.close()

    def set_contents_from_string(self, s, headers=None, replace=True,
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
                   progress on the upload.  The callback should accept
                   two integer parameters, the first representing the
                   number of bytes that have been successfully
                   transmitted to S3 and the second representing the
                   size of the to be transmitted object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with
                       the cb parameter this parameter determines the
                       granularity of the callback by defining
                       the maximum number of times the callback will
                       be called during the file transfer.

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the
                       new key in S3.

        :type md5: A tuple containing the hexdigest version of the MD5
                   checksum of the file as the first element and the
                   Base64-encoded version of the plain checksum as the
                   second element.  This is the same format returned by
                   the compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason prior
                    to upload, it's silly to have to do it twice so this
                    param, if present, will be used as the MD5 values
                    of the file.  Otherwise, the checksum will be computed.

        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will set the storage
                                   class of the new Key to be
                                   REDUCED_REDUNDANCY. The Reduced Redundancy
                                   Storage (RRS) feature of S3, provides lower
                                   redundancy at lower storage cost.
        :type encrypt_key: bool
        :param encrypt_key: If True, the new copy of the object will
                            be encrypted on the server-side by S3 and
                            will be stored in an encrypted form while
                            at rest in S3.
        """
        if isinstance(s, unicode):
            s = s.encode("utf-8")
        fp = StringIO.StringIO(s)
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
                   progress on the upload.  The callback should accept
                   two integer parameters, the first representing the
                   number of bytes that have been successfully
                   transmitted to S3 and the second representing the
                   size of the to be transmitted object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with
                       the cb parameter this parameter determines the
                       granularity of the callback by defining
                       the maximum number of times the callback will
                       be called during the file transfer.

        :type torrent: bool
        :param torrent: Flag for whether to get a torrent for the file

        :type override_num_retries: int
        :param override_num_retries: If not None will override configured
                                     num_retries parameter for underlying GET.

        :type response_headers: dict
        :param response_headers: A dictionary containing HTTP headers/values
                                 that will override any headers associated with
                                 the stored object in the response.
                                 See http://goo.gl/EWOPb for details.
        """
        if cb:
            if num_cb > 2:
                cb_count = self.size / self.BufferSize / (num_cb-2)
            elif num_cb < 0:
                cb_count = -1
            else:
                cb_count = 0
            i = total_bytes = 0
            cb(total_bytes, self.size)
        save_debug = self.bucket.connection.debug
        if self.bucket.connection.debug == 1:
            self.bucket.connection.debug = 0

        query_args = []
        if torrent:
            query_args.append('torrent')
        # If a version_id is passed in, use that.  If not, check to see
        # if the Key object has an explicit version_id and, if so, use that.
        # Otherwise, don't pass a version_id query param.
        if version_id is None:
            version_id = self.version_id
        if version_id:
            query_args.append('versionId=%s' % version_id)
        if response_headers:
            for key in response_headers:
                query_args.append('%s=%s' % (key, urllib.quote(response_headers[key])))
        query_args = '&'.join(query_args)
        self.open('r', headers, query_args=query_args,
                  override_num_retries=override_num_retries)
        for bytes in self:
            fp.write(bytes)
            if cb:
                total_bytes += len(bytes)
                i += 1
                if i == cb_count or cb_count == -1:
                    cb(total_bytes, self.size)
                    i = 0
        if cb:
            cb(total_bytes, self.size)
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
                   progress on the upload.  The callback should accept
                   two integer parameters, the first representing the
                   number of bytes that have been successfully
                   transmitted to S3 and the second representing the
                   size of the to be transmitted object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with
                       the cb parameter this parameter determines the
                       granularity of the callback by defining
                       the maximum number of times the callback will
                       be called during the file transfer.

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
                   progress on the upload.  The callback should accept
                   two integer parameters, the first representing the
                   number of bytes that have been successfully
                   transmitted to S3 and the second representing the
                   size of the to be transmitted object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with
                       the cb parameter this parameter determines the
                       granularity of the callback by defining
                       the maximum number of times the callback will
                       be called during the file transfer.

        :type torrent: bool
        :param torrent: If True, returns the contents of a torrent
                        file as a string.

        :type res_upload_handler: ResumableDownloadHandler
        :param res_download_handler: If provided, this handler will
                                     perform the download.

        :type response_headers: dict
        :param response_headers: A dictionary containing HTTP headers/values
                                 that will override any headers associated with
                                 the stored object in the response.
                                 See http://goo.gl/EWOPb for details.
        """
        if self.bucket != None:
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
                   progress on the upload.  The callback should accept
                   two integer parameters, the first representing the
                   number of bytes that have been successfully
                   transmitted to S3 and the second representing the
                   size of the to be transmitted object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with
                       the cb parameter this parameter determines the
                       granularity of the callback by defining
                       the maximum number of times the callback will
                       be called during the file transfer.

        :type torrent: bool
        :param torrent: If True, returns the contents of a torrent file
                        as a string.

        :type res_upload_handler: ResumableDownloadHandler
        :param res_download_handler: If provided, this handler will
                                     perform the download.

        :type response_headers: dict
        :param response_headers: A dictionary containing HTTP headers/values
                                 that will override any headers associated with
                                 the stored object in the response.
                                 See http://goo.gl/EWOPb for details.
        """
        fp = open(filename, 'wb')
        self.get_contents_to_file(fp, headers, cb, num_cb, torrent=torrent,
                                  version_id=version_id,
                                  res_download_handler=res_download_handler,
                                  response_headers=response_headers)
        fp.close()
        # if last_modified date was sent from s3, try to set file's timestamp
        if self.last_modified != None:
            try:
                modified_tuple = rfc822.parsedate_tz(self.last_modified)
                modified_stamp = int(rfc822.mktime_tz(modified_tuple))
                os.utime(fp.name, (modified_stamp, modified_stamp))
            except Exception: pass

    def get_contents_as_string(self, headers=None,
                               cb=None, num_cb=10,
                               torrent=False,
                               version_id=None,
                               response_headers=None):
        """
        Retrieve an object from S3 using the name of the Key object as the
        key in S3.  Return the contents of the object as a string.
        See get_contents_to_file method for details about the
        parameters.

        :type headers: dict
        :param headers: Any additional headers to send in the request

        :type cb: function
        :param cb: a callback function that will be called to report
                   progress on the upload.  The callback should accept
                   two integer parameters, the first representing the
                   number of bytes that have been successfully
                   transmitted to S3 and the second representing the
                   size of the to be transmitted object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with
                       the cb parameter this parameter determines the
                       granularity of the callback by defining
                       the maximum number of times the callback will
                       be called during the file transfer.

        :type torrent: bool
        :param torrent: If True, returns the contents of a torrent file
                        as a string.

        :type response_headers: dict
        :param response_headers: A dictionary containing HTTP headers/values
                                 that will override any headers associated with
                                 the stored object in the response.
                                 See http://goo.gl/EWOPb for details.

        :rtype: string
        :returns: The contents of the file as a string
        """
        fp = StringIO.StringIO()
        self.get_contents_to_file(fp, headers, cb, num_cb, torrent=torrent,
                                  version_id=version_id,
                                  response_headers=response_headers)
        return fp.getvalue()

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
        :param recursive: A boolean value to controls whether the command
                          will apply the grant to all keys within the bucket
                          or not.  The default value is False.  By passing a
                          True value, the call will iterate through all keys
                          in the bucket and apply the same grant to each key.
                          CAUTION: If you have a lot of keys, this could take
                          a long time!
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
        :param user_id:     The canonical user id associated with the AWS
                            account your are granting the permission to.

        :type display_name: string
        :param display_name: An option string containing the user's
                             Display Name.  Only required on Walrus.
        """
        policy = self.get_acl()
        policy.acl.add_user_grant(permission, user_id,
                                  display_name=display_name)
        self.set_acl(policy, headers=headers)
