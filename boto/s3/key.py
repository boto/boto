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

import urllib
import socket
import mimetypes
import md5
import os
import rfc822
import StringIO
import time
import base64
import boto
import boto.utils
from boto.exception import S3ResponseError, S3DataError
from boto.s3.user import User

class Key:

    DefaultContentType = 'application/octet-stream'

    BufferSize = 8192

    def __init__(self, bucket=None, name=None):
        self.bucket = bucket
        self.name = name
        self.metadata = {}
        self.content_type = self.DefaultContentType
        self.filename = None
        self.etag = None
        self.last_modified = None
        self.owner = None
        self.storage_class = None
        self.md5 = None
        self.base64md5 = None
        self.path = None

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
        elif name == 'LastModified':
            self.last_modified = value
        elif name == 'Size':
            self.size = value
        elif name == 'StorageClass':
            self.storage_class = value
        elif name == 'Owner':
            pass
        else:
            setattr(self, name, value)

    def exists(self):
        return bool(self.bucket.lookup(self.name))

    def delete(self):
        return self.bucket.delete_key(self.name)

    def get_metadata(self, name):
        return self.metadata[name]

    def set_metadata(self, name, value):
        self.metadata[name] = value

    def update_metadata(self, d):
        self.metadata.update(d)
    
    def generate_url(self, expires_in, method='GET',
                     headers=None, query_auth=True):
        path = '/%s/%s' % (self.bucket.name, self.name)
        path = urllib.quote(path)
        return self.bucket.connection.generate_url(expires_in, method,
                                                   path, headers, query_auth)
    
    def send_file(self, fp, headers=None, cb=None, num_cb=10):
        http_conn = self.bucket.connection.connection
        if not headers:
            headers = {}
        headers['Content-MD5'] = self.base64md5
        if headers.has_key('Content-Type'):
            self.content_type = headers['Content-Type']
        elif self.path:
            self.content_type = mimetypes.guess_type(self.path)[0]
            if self.content_type == None:
                self.content_type = self.DefaultContentType
            headers['Content-Type'] = self.content_type
        else:
            headers['Content-Type'] = self.content_type
        headers['Content-Length'] = self.size
        headers['Expect'] = '100-Continue'
        final_headers = boto.utils.merge_meta(headers, self.metadata);
        path = '/%s/%s' % (self.bucket.name, self.name)
        path = urllib.quote(path)
        self.bucket.connection.add_aws_auth_header(final_headers, 'PUT', path)
        #the prepending of the protocol and true host must occur after
        #the authentication header is computed (line above). The
        #authentication includes the path, which for authentication is
        #only the bucket and key
        if self.bucket.connection.use_proxy:
            path = self.bucket.connection.prefix_proxy_to_path(path)
        try:
            http_conn.putrequest('PUT', path)
            for key in final_headers:
                http_conn.putheader(key,final_headers[key])
            http_conn.endheaders()
            save_debug = self.bucket.connection.debug
            if self.bucket.connection.debug == 1:
                self.bucket.connection.set_debug(0)
            if cb:
                if num_cb > 2:
                    cb_count = self.size / self.BufferSize / (num_cb-2)
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
                    if i == cb_count:
                        cb(total_bytes, self.size)
                        i = 0
                l = fp.read(self.BufferSize)
            if cb:
                cb(total_bytes, self.size)
            response = http_conn.getresponse()
            body = response.read()
            self.bucket.connection.set_debug(save_debug)
        except socket.error, (value, message):
            if value in self.bucket.connection.socket_exception_values:
                print 'Caught %d:%s socket error, aborting' % (value, message)
                raise
            print 'Caught a socket error, trying to recover'
            self.bucket.connection.make_http_connection()
            fp.seek(0)
            self.send_file(fp, headers)
            return
        except Exception, e:
            print 'Caught an unexpected exception'
            self.bucket.connection.make_http_connection()
            raise e
        if response.status != 200:
            raise S3ResponseError(response.status, response.reason, body)
        self.etag = response.getheader('etag')
        if self.etag != '"%s"'  % self.md5:
            raise S3DataError('Injected data did not return correct MD5')

    def _compute_md5(self, fp):
        m = md5.new()
        s = fp.read(self.BufferSize)
        while s:
            m.update(s)
            s = fp.read(self.BufferSize)
        self.md5 = m.hexdigest()
        self.base64md5 = base64.encodestring(m.digest())
        if self.base64md5[-1] == '\n':
            self.base64md5 = self.base64md5[0:-1]
        self.size = fp.tell()
        fp.seek(0)

    def set_contents_from_file(self, fp, headers=None, replace=True,
                               cb=None, num_cb=10):
        """
        Store an object in S3 using the name of the Key object as the
        key in S3 and the contents of the file pointed to by 'fp' as the
        contents.
        
        Parameters:
        
        fp - a File-like object.
        headers - (optional) additional HTTP headers that will be
                  sent with the PUT request.
        replace - (optional) If this parameter is False, the method
                  will first check to see if an object exists in the
                  bucket with the same key.  If it does, it won't
                  overwrite it.  The default value is True which will
                  overwrite the object.
        cb - (optional) a callback function that will be called to report
             progress on the upload.  The callback should accept two integer
             parameters, the first representing the number of bytes that have
             been successfully transmitted to S3 and the second representing
             the total number of bytes that need to be transmitted.
        """
        if hasattr(fp, 'name'):
            self.path = fp.name
        if self.bucket != None:
            self._compute_md5(fp)
            if self.name == None:
                self.name = self.md5
            if not replace:
                k = self.bucket.lookup(self.name)
                if k:
                    return
            self.send_file(fp, headers, cb, num_cb)

    def set_contents_from_filename(self, filename, headers=None,
                                   replace=True, cb=None, num_cb=10):
        """
        Store an object in S3 using the name of the Key object as the
        key in S3 and the contents of the file named by 'filename'.
        See set_contents_from_file method for details about the
        parameters.
        """
        fp = open(filename, 'rb')
        self.set_contents_from_file(fp, headers, replace, cb, num_cb)
        fp.close()

    def set_contents_from_string(self, s, headers=None,
                                 replace=True, cb=None, num_cb=10):
        """
        Store an object in S3 using the name of the Key object as the
        key in S3 and the string 's' as the contents.
        See set_contents_from_file method for details about the
        parameters.
        """
        fp = StringIO.StringIO(s)
        self.set_contents_from_file(fp, headers, replace, cb, num_cb)
        fp.close()

    def get_file(self, fp, headers=None, cb=None, num_cb=10):
        path = '/%s/%s' % (self.bucket.name, self.name)
        path = urllib.quote(path)
        resp = self.bucket.connection.make_request('GET', path, headers)
        if resp.status < 199 or resp.status > 299:
            raise S3ResponseError(resp.status, resp.reason)
        response_headers = resp.msg
        self.metadata = boto.utils.get_aws_metadata(response_headers)
        for key in response_headers.keys():
            if key.lower() == 'content-length':
                self.size = int(response_headers[key])
            elif key.lower() == 'etag':
                self.etag = response_headers[key]
            elif key.lower() == 'content-type':
                self.content_type = response_headers[key]
            elif key.lower() == 'last-modified':
                self.last_modified = response_headers[key]
        if cb:
            if num_cb > 2:
                cb_count = self.size / self.BufferSize / (num_cb-2)
            else:
                cb_count = 0
            i = total_bytes = 0
            cb(total_bytes, self.size)
        save_debug = self.bucket.connection.debug
        if self.bucket.connection.debug == 1:
            self.bucket.connection.set_debug(0)
        l = resp.read(self.BufferSize)
        while len(l) > 0:
            fp.write(l)
            if cb:
                total_bytes += len(l)
                i += 1
                if i == cb_count:
                    cb(total_bytes, self.size)
                    i = 0
            l = resp.read(self.BufferSize)
        if cb:
            cb(total_bytes, self.size)
        resp.read()
        self.bucket.connection.set_debug(save_debug)

    def get_contents_to_file(self, fp, headers=None, cb=None, num_cb=10):
        """
        Retrieve an object from S3 using the name of the Key object as the
        key in S3.  Write the contents of the object to the file pointed
        to by 'fp'.
        
        Parameters:
        
        fp - a File-like object.
        headers - (optional) additional HTTP headers that will be
                  sent with the GET request.
        cb - (optional) a callback function that will be called to report
             progress on the download.  The callback should accept two integer
             parameters, the first representing the number of bytes that have
             been successfully transmitted from S3 and the second representing
             the total number of bytes that need to be transmitted.
        """
        if self.bucket != None:
            self.get_file(fp, headers, cb, num_cb)

    def get_contents_to_filename(self, filename, headers=None,
                                 cb=None, num_cb=10):
        """
        Retrieve an object from S3 using the name of the Key object as the
        key in S3.  Store contents of the object to a file named by 'filename'.
        See get_contents_to_file method for details about the
        parameters.
        """
        fp = open(filename, 'wb')
        self.get_contents_to_file(fp, headers, cb, num_cb)
        fp.close()
        # if last_modified date was sent from s3, try to set file's timestamp
        if self.last_modified != None:
            try:
                modified_tuple = rfc822.parsedate_tz(self.last_modified)
                modified_stamp = int(rfc822.mktime_tz(modified_tuple))
                os.utime(fp.name, (modified_stamp, modified_stamp))
            except Exception, e: pass

    def get_contents_as_string(self, headers=None, cb=None, num_cb=10):
        """
        Retrieve an object from S3 using the name of the Key object as the
        key in S3.  Return the contents of the object as a string.
        See get_contents_to_file method for details about the
        parameters.
        """
        fp = StringIO.StringIO()
        self.get_contents_to_file(fp, headers, cb, num_cb)
        return fp.getvalue()

    # convenience methods for setting/getting ACL
    def set_acl(self, acl_str):
        if self.bucket != None:
            self.bucket.set_acl(acl_str, self.name)

    def get_acl(self):
        if self.bucket != None:
            return self.bucket.get_acl(self.name)

    def add_email_grant(self, permission, email_address):
        """
        Convenience method that provides a quick way to add an email grant to a key.
        This method retrieves the current ACL, creates a new grant based on the parameters
        passed in, adds that grant to the ACL and then PUT's the new ACL back to S3.
        Inputs:
            permission - The permission being granted.  Should be one of:
                         READ|WRITE|READ_ACP|WRITE_ACP|FULL_CONTROL
                         See http://docs.amazonwebservices.com/AmazonS3/2006-03-01/UsingAuthAccess.html
                         for more details on permissions.
            email_address - The email address associated with the AWS account your are granting
                            the permission to.
        Returns:
            Nothing
        """
        policy = self.get_acl()
        policy.acl.add_email_grant(permission, email_address)
        self.set_acl(policy)

    def add_user_grant(self, permission, user_id):
        """
        Convenience method that provides a quick way to add a canonical user grant to a key.
        This method retrieves the current ACL, creates a new grant based on the parameters
        passed in, adds that grant to the ACL and then PUT's the new ACL back to S3.
        Inputs:
            permission - The permission being granted.  Should be one of:
                         READ|WRITE|READ_ACP|WRITE_ACP|FULL_CONTROL
                         See http://docs.amazonwebservices.com/AmazonS3/2006-03-01/UsingAuthAccess.html
                         for more details on permissions.
            user_id - The canonical user id associated with the AWS account your are granting
                      the permission to.
        Returns:
            Nothing
        """
        policy = self.get_acl()
        policy.acl.add_user_grant(permission, user_id)
        self.set_acl(policy)
