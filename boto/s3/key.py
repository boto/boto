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

import mimetypes
import os
import rfc822
import StringIO
import base64
import boto.utils
from boto.exception import S3ResponseError, S3DataError, BotoClientError
from boto.s3.user import User
from boto import UserAgent
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

    def handle_version_headers(self, resp):
        provider = self.bucket.connection.provider
        self.version_id = resp.getheader(provider.version_id, None)
        self.source_version_id = resp.getheader(provider.copy_source_version_id, None)
        if resp.getheader(provider.delete_marker, 'false') == 'true':
            self.delete_marker = True
        else:
            self.delete_marker = False

    def open_read(self, headers=None, query_args=None):
        """
        Open this key for reading
        
        :type headers: dict
        :param headers: Headers to pass in the web request
        
        :type query_args: string
        :param query_args: Arguments to pass in the query string (ie, 'torrent')
        """
        if self.resp == None:
            self.mode = 'r'
            
            self.resp = self.bucket.connection.make_request('GET',
                                                            self.bucket.name,
                                                            self.name, headers,
                                                            query_args=query_args)
            if self.resp.status < 199 or self.resp.status > 299:
                body = self.resp.read()
                raise S3ResponseError(self.resp.status, self.resp.reason, body)
            response_headers = self.resp.msg
            provider = self.bucket.connection.provider
            self.metadata = boto.utils.get_aws_metadata(response_headers,
                                                        provider)
            for name,value in response_headers.items():
                if name.lower() == 'content-length':
                    self.size = int(value)
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

    def open_write(self, headers=None):
        """
        Open this key for writing. 
        Not yet implemented
        
        :type headers: dict
        :param headers: Headers to pass in the write request
        """
        raise BotoClientError('Not Implemented')

    def open(self, mode='r', headers=None, query_args=None):
        if mode == 'r':
            self.mode = 'r'
            self.open_read(headers=headers, query_args=query_args)
        elif mode == 'w':
            self.mode = 'w'
            self.open_write(headers=headers)
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
        if size == 0:
            size = self.BufferSize
        self.open_read()
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
        self.storage_class = new_storage_class
        return self.copy(self.bucket.name, self.name,
                         reduced_redundancy=True, preserve_acl=True)

    def copy(self, dst_bucket, dst_key, metadata=None,
             reduced_redundancy=False, preserve_acl=False):
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
                                   preserve_acl=preserve_acl)

    def startElement(self, name, attrs, connection):
        if name == 'Owner':
            self.owner = User(self)
            return self.owner
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'Key':
            self.name = value.encode('utf-8')
        elif name == 'ETag':
            self.etag = value
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
        return self.bucket.delete_key(self.name)

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
                     query_auth=True, force_http=False):
        """
        Generate a URL to access this key.
        
        :type expires_in: int
        :param expires_in: How long the url is valid for, in seconds
        
        :type method: string
        :param method: The method to use for retrieving the file (default is GET)
        
        :type headers: dict
        :param headers: Any headers to pass along in the request
        
        :type query_auth: bool
        :param query_auth: 
        
        :rtype: string
        :return: The URL to access the key
        """
        return self.bucket.connection.generate_url(expires_in, method,
                                                   self.bucket.name, self.name,
                                                   headers, query_auth, force_http)

    def send_file(self, fp, headers=None, cb=None, num_cb=10):
        """
        Upload a file to a key into a bucket on S3.
        
        :type fp: file
        :param fp: The file pointer to upload
        
        :type headers: dict
        :param headers: The headers to pass along with the PUT request
        
        :type cb: function
        :param cb: a callback function that will be called to report
                    progress on the upload.  The callback should accept two integer
                    parameters, the first representing the number of bytes that have
                    been successfully transmitted to S3 and the second representing
                    the total number of bytes that need to be transmitted.
                    
        :type num_cb: int
        :param num_cb: (optional) If a callback is specified with the cb
                       parameter this parameter determines the granularity
                       of the callback by defining the maximum number of
                       times the callback will be called during the file
                       transfer. Providing a negative integer will cause
                       your callback to be called with each buffer read.
             
        """
        def sender(http_conn, method, path, data, headers):
            http_conn.putrequest(method, path)
            for key in headers:
                http_conn.putheader(key, headers[key])
            http_conn.endheaders()
            fp.seek(0)
            save_debug = self.bucket.connection.debug
            self.bucket.connection.debug = 0
            if cb:
                if num_cb > 2:
                    cb_count = self.size / self.BufferSize / (num_cb-2)
                elif num_cb < 0:
                    cb_count = -1
                else:
                    cb_count = 0
                i = total_bytes = 0
                cb(total_bytes, self.size)
            l = fp.read(self.BufferSize)
            while len(l) > 0:
                http_conn.send(l)
                if cb:
                    total_bytes += len(l)
                    i += 1
                    if i == cb_count or cb_count == -1:
                        cb(total_bytes, self.size)
                        i = 0
                l = fp.read(self.BufferSize)
            if cb:
                cb(total_bytes, self.size)
            response = http_conn.getresponse()
            body = response.read()
            fp.seek(0)
            self.bucket.connection.debug = save_debug
            if response.status == 500 or response.status == 503 or \
                    response.getheader('location'):
                # we'll try again
                return response
            elif response.status >= 200 and response.status <= 299:
                self.etag = response.getheader('etag')
                if self.etag != '"%s"'  % self.md5:
                    raise S3DataError('ETag from S3 did not match computed MD5')
                return response
            else:
                raise S3ResponseError(response.status, response.reason, body)

        if not headers:
            headers = {}
        else:
            headers = headers.copy()
        headers['User-Agent'] = UserAgent
        headers['Content-MD5'] = self.base64md5
        if self.storage_class != 'STANDARD':
            provider = self.bucket.connection.provider
            headers[provider.storage_class] = self.storage_class
        if headers.has_key('Content-Type'):
            self.content_type = headers['Content-Type']
        if headers.has_key('Content-Encoding'):
            self.content_encoding = headers['Content-Encoding']
        elif self.path:
            self.content_type = mimetypes.guess_type(self.path)[0]
            if self.content_type == None:
                self.content_type = self.DefaultContentType
            headers['Content-Type'] = self.content_type
        else:
            headers['Content-Type'] = self.content_type
        headers['Content-Length'] = str(self.size)
        headers['Expect'] = '100-Continue'
        headers = boto.utils.merge_meta(headers, self.metadata,
                                        self.bucket.connection.provider)
        resp = self.bucket.connection.make_request('PUT', self.bucket.name,
                                                   self.name, headers,
                                                   sender=sender)
        self.handle_version_headers(resp)

    def compute_md5(self, fp):
        """
        :type fp: file
        :param fp: File pointer to the file to MD5 hash.  The file pointer will be
                   reset to the beginning of the file before the method returns.
        
        :rtype: tuple
        :return: A tuple containing the hex digest version of the MD5 hash
                 as the first element and the base64 encoded version of the
                 plain digest as the second element.
        """
        m = md5()
        fp.seek(0)
        s = fp.read(self.BufferSize)
        while s:
            m.update(s)
            s = fp.read(self.BufferSize)
        hex_md5 = m.hexdigest()
        base64md5 = base64.encodestring(m.digest())
        if base64md5[-1] == '\n':
            base64md5 = base64md5[0:-1]
        self.size = fp.tell()
        fp.seek(0)
        return (hex_md5, base64md5)

    def set_contents_from_file(self, fp, headers=None, replace=True,
                               cb=None, num_cb=10, policy=None, md5=None,
                               reduced_redundancy=False):
        """
        Store an object in S3 using the name of the Key object as the
        key in S3 and the contents of the file pointed to by 'fp' as the
        contents.
        
        :type fp: file
        :param fp: the file whose contents to upload
        
        :type headers: dict
        :param headers: additional HTTP headers that will be sent with the PUT request.

        :type replace: bool
        :param replace: If this parameter is False, the method
                        will first check to see if an object exists in the
                        bucket with the same key.  If it does, it won't
                        overwrite it.  The default value is True which will
                        overwrite the object.
                    
        :type cb: function
        :param cb: a callback function that will be called to report
                    progress on the upload.  The callback should accept two integer
                    parameters, the first representing the number of bytes that have
                    been successfully transmitted to S3 and the second representing
                    the total number of bytes that need to be transmitted.
                    
        :type cb: int
        :param num_cb: (optional) If a callback is specified with the cb parameter
             this parameter determines the granularity of the callback by defining
             the maximum number of times the callback will be called during the file transfer.

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the new key in S3.
             
        :type md5: A tuple containing the hexdigest version of the MD5 checksum of the
                   file as the first element and the Base64-encoded version of the plain
                   checksum as the second element.  This is the same format returned by
                   the compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason prior to upload,
                    it's silly to have to do it twice so this param, if present, will be
                    used as the MD5 values of the file.  Otherwise, the checksum will be computed.
        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will force the storage
                                   class of the new Key to be
                                   REDUCED_REDUNDANCY regardless of the
                                   storage class of the key being copied.
                                   The Reduced Redundancy Storage (RRS)
                                   feature of S3, provides lower
                                   redundancy at lower storage cost.

        """
        provider = self.bucket.connection.provider
        if headers is None:
            headers = {}
        if policy:
            headers[provider.acl_header] = policy
        if reduced_redundancy:
            self.storage_class = 'REDUCED_REDUNDANCY'
            headers[provider.storage_class] = self.storage_class
        if hasattr(fp, 'name'):
            self.path = fp.name
        if self.bucket != None:
            if not md5:
                md5 = self.compute_md5(fp)
            self.md5 = md5[0]
            self.base64md5 = md5[1]
            if self.name == None:
                self.name = self.md5
            if not replace:
                k = self.bucket.lookup(self.name)
                if k:
                    return
            self.send_file(fp, headers, cb, num_cb)

    def set_contents_from_filename(self, filename, headers=None, replace=True,
                                   cb=None, num_cb=10, policy=None, md5=None,
                                   reduced_redundancy=False):
        """
        Store an object in S3 using the name of the Key object as the
        key in S3 and the contents of the file named by 'filename'.
        See set_contents_from_file method for details about the
        parameters.
        
        :type filename: string
        :param filename: The name of the file that you want to put onto S3
        
        :type headers: dict
        :param headers: Additional headers to pass along with the request to AWS.
        
        :type replace: bool
        :param replace: If True, replaces the contents of the file if it already exists.
        
        :type cb: function
        :param cb: (optional) a callback function that will be called to report
             progress on the download.  The callback should accept two integer
             parameters, the first representing the number of bytes that have
             been successfully transmitted from S3 and the second representing
             the total number of bytes that need to be transmitted.        
                    
        :type cb: int
        :param num_cb: (optional) If a callback is specified with the cb parameter
             this parameter determines the granularity of the callback by defining
             the maximum number of times the callback will be called during the file transfer.  
             
        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the new key in S3.
             
        :type md5: A tuple containing the hexdigest version of the MD5 checksum of the
                   file as the first element and the Base64-encoded version of the plain
                   checksum as the second element.  This is the same format returned by
                   the compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason prior to upload,
                    it's silly to have to do it twice so this param, if present, will be
                    used as the MD5 values of the file.  Otherwise, the checksum will be computed.
                    
        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will force the storage
                                   class of the new Key to be
                                   REDUCED_REDUNDANCY regardless of the
                                   storage class of the key being copied.
                                   The Reduced Redundancy Storage (RRS)
                                   feature of S3, provides lower
                                   redundancy at lower storage cost.
        """
        fp = open(filename, 'rb')
        self.set_contents_from_file(fp, headers, replace, cb, num_cb,
                                    policy, md5, reduced_redundancy)
        fp.close()

    def set_contents_from_string(self, s, headers=None, replace=True,
                                 cb=None, num_cb=10, policy=None, md5=None,
                                 reduced_redundancy=False):
        """
        Store an object in S3 using the name of the Key object as the
        key in S3 and the string 's' as the contents.
        See set_contents_from_file method for details about the
        parameters.
        
        :type headers: dict
        :param headers: Additional headers to pass along with the request to AWS.
        
        :type replace: bool
        :param replace: If True, replaces the contents of the file if it already exists.
        
        :type cb: function
        :param cb: (optional) a callback function that will be called to report
             progress on the download.  The callback should accept two integer
             parameters, the first representing the number of bytes that have
             been successfully transmitted from S3 and the second representing
             the total number of bytes that need to be transmitted.        
                    
        :type cb: int
        :param num_cb: (optional) If a callback is specified with the cb parameter
             this parameter determines the granularity of the callback by defining
             the maximum number of times the callback will be called during the file transfer.  
             
        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the new key in S3.
             
        :type md5: A tuple containing the hexdigest version of the MD5 checksum of the
                   file as the first element and the Base64-encoded version of the plain
                   checksum as the second element.  This is the same format returned by
                   the compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason prior to upload,
                    it's silly to have to do it twice so this param, if present, will be
                    used as the MD5 values of the file.  Otherwise, the checksum will be computed.
                    
        :type reduced_redundancy: bool
        :param reduced_redundancy: If True, this will force the storage
                                   class of the new Key to be
                                   REDUCED_REDUNDANCY regardless of the
                                   storage class of the key being copied.
                                   The Reduced Redundancy Storage (RRS)
                                   feature of S3, provides lower
                                   redundancy at lower storage cost.
        """
        fp = StringIO.StringIO(s)
        r = self.set_contents_from_file(fp, headers, replace, cb, num_cb,
                                        policy, md5, reduced_redundancy)
        fp.close()
        return r

    def get_file(self, fp, headers=None, cb=None, num_cb=10,
                 torrent=False, version_id=None):
        """
        Retrieves a file from an S3 Key
        
        :type fp: file
        :param fp: File pointer to put the data into
        
        :type headers: string
        :param: headers to send when retrieving the files
        
        :type cb: function
        :param cb: (optional) a callback function that will be called to report
             progress on the download.  The callback should accept two integer
             parameters, the first representing the number of bytes that have
             been successfully transmitted from S3 and the second representing
             the total number of bytes that need to be transmitted.
        
                    
        :type cb: int
        :param num_cb: (optional) If a callback is specified with the cb parameter
             this parameter determines the granularity of the callback by defining
             the maximum number of times the callback will be called during the file transfer.  
             
        :type torrent: bool
        :param torrent: Flag for whether to get a torrent for the file
        """
        if cb:
            if num_cb > 2:
                cb_count = self.size / self.BufferSize / (num_cb-2)
            else:
                cb_count = 0
            i = total_bytes = 0
            cb(total_bytes, self.size)
        save_debug = self.bucket.connection.debug
        if self.bucket.connection.debug == 1:
            self.bucket.connection.debug = 0
        
        query_args = ''
        if torrent:
            query_args = 'torrent'
        elif version_id:
            query_args = 'versionId=%s' % version_id
        self.open('r', headers, query_args=query_args)
        for bytes in self:
            fp.write(bytes)
            if cb:
                total_bytes += len(bytes)
                i += 1
                if i == cb_count:
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
        :param cb: Callback function to call on retrieved data
        
        :type cb: int
        :param num_cb: (optional) If a callback is specified with the cb parameter
             this parameter determines the granularity of the callback by defining
             the maximum number of times the callback will be called during the file transfer.  
             
        """
        return self.get_file(fp, headers, cb, num_cb, torrent=True)
    
    def get_contents_to_file(self, fp, headers=None,
                             cb=None, num_cb=10,
                             torrent=False,
                             version_id=None):
        """
        Retrieve an object from S3 using the name of the Key object as the
        key in S3.  Write the contents of the object to the file pointed
        to by 'fp'.
        
        :type fp: File -like object
        :param fp:
        
        :type headers: dict
        :param headers: additional HTTP headers that will be sent with the GET request.
        
        :type cb: function
        :param cb: (optional) a callback function that will be called to report
             progress on the download.  The callback should accept two integer
             parameters, the first representing the number of bytes that have
             been successfully transmitted from S3 and the second representing
             the total number of bytes that need to be transmitted.
             
                    
        :type cb: int
        :param num_cb: (optional) If a callback is specified with the cb parameter
             this parameter determines the granularity of the callback by defining
             the maximum number of times the callback will be called during the file transfer.  
             
        :type torrent: bool
        :param torrent: If True, returns the contents of a torrent file as a string.

        """
        if self.bucket != None:
            self.get_file(fp, headers, cb, num_cb, torrent=torrent,
                          version_id=version_id)

    def get_contents_to_filename(self, filename, headers=None,
                                 cb=None, num_cb=10,
                                 torrent=False,
                                 version_id=None):
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
        :param cb: (optional) a callback function that will be called to report
             progress on the download.  The callback should accept two integer
             parameters, the first representing the number of bytes that have
             been successfully transmitted from S3 and the second representing
             the total number of bytes that need to be transmitted.
             
                    
        :type cb: int
        :param num_cb: (optional) If a callback is specified with the cb parameter
             this parameter determines the granularity of the callback by defining
             the maximum number of times the callback will be called during the file transfer.  
             
        :type torrent: bool
        :param torrent: If True, returns the contents of a torrent file as a string.
        
        """
        fp = open(filename, 'wb')
        self.get_contents_to_file(fp, headers, cb, num_cb, torrent=torrent,
                                  version_id=version_id)
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
                               version_id=None):
        """
        Retrieve an object from S3 using the name of the Key object as the
        key in S3.  Return the contents of the object as a string.
        See get_contents_to_file method for details about the
        parameters.
        
        :type headers: dict
        :param headers: Any additional headers to send in the request
        
        :type cb: function
        :param cb: (optional) a callback function that will be called to report
             progress on the download.  The callback should accept two integer
             parameters, the first representing the number of bytes that have
             been successfully transmitted from S3 and the second representing
             the total number of bytes that need to be transmitted.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with the cb parameter
             this parameter determines the granularity of the callback by defining
             the maximum number of times the callback will be called during the file transfer.  
             
                    
        :type cb: int
        :param num_cb: (optional) If a callback is specified with the cb parameter
             this parameter determines the granularity of the callback by defining
             the maximum number of times the callback will be called during the file transfer.  
             
        :type torrent: bool
        :param torrent: If True, returns the contents of a torrent file as a string.
        
        :rtype: string
        :returns: The contents of the file as a string
        """
        fp = StringIO.StringIO()
        self.get_contents_to_file(fp, headers, cb, num_cb, torrent=torrent,
                                  version_id=version_id)
        return fp.getvalue()

    def add_email_grant(self, permission, email_address, headers=None):
        """
        Convenience method that provides a quick way to add an email grant to a key.
        This method retrieves the current ACL, creates a new grant based on the parameters
        passed in, adds that grant to the ACL and then PUT's the new ACL back to S3.
        
        :type permission: string
        :param permission: The permission being granted.  Should be one of:
                            READ|WRITE|READ_ACP|WRITE_ACP|FULL_CONTROL
                            See http://docs.amazonwebservices.com/AmazonS3/2006-03-01/UsingAuthAccess.html
                            for more details on permissions.
        
        :type email_address: string
        :param email_address: The email address associated with the AWS account your are granting
                                the permission to.
        """
        policy = self.get_acl(headers=headers)
        policy.acl.add_email_grant(permission, email_address)
        self.set_acl(policy, headers=headers)

    def add_user_grant(self, permission, user_id):
        """
        Convenience method that provides a quick way to add a canonical user grant to a key.
        This method retrieves the current ACL, creates a new grant based on the parameters
        passed in, adds that grant to the ACL and then PUT's the new ACL back to S3.
        
        :type permission: string
        :param permission: The permission being granted.  Should be one of:
                            READ|WRITE|READ_ACP|WRITE_ACP|FULL_CONTROL
                            See http://docs.amazonwebservices.com/AmazonS3/2006-03-01/UsingAuthAccess.html
                            for more details on permissions.
        
        :type user_id: string
        :param user_id: The canonical user id associated with the AWS account your are granting
                        the permission to.
        """
        policy = self.get_acl()
        policy.acl.add_user_grant(permission, user_id)
        self.set_acl(policy)
