# Copyright (c) 2006 Mitch Garnaat http://garnaat.org/
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
import mimetypes
import md5
import StringIO
import base64
import boto
from boto.exception import S3ResponseError

class Key:

    def __init__(self, bucket=None, xml_attrs=None):
        self.bucket = bucket
        self.content_type = 'application/octet-stream'
        self.filename = None
        self.etag = None
        self.key = None
        self.last_modified = None
        self.owner = None
        self.storage_class = None

    # This allows the XMLHandler to set the attributes as they are named
    # in the XML response but have the capitalized names converted to
    # more conventional looking python variables names automatically
    def __setattr__(self, key, value):
        if key == 'Key':
            self.__dict__['key'] = value
        elif key == 'ETag':
            self.__dict__['etag'] = value
        elif key == 'LastModified':
            self.__dict__['last_modified'] = value
        elif key == 'Size':
            self.__dict__['size'] = value
        elif key == 'StorageClass':
            self.__dict__['storage_class'] = value
        elif key == 'Contents':
            pass
        else:
            self.__dict__[key] = value

    def send_file(self, fp):
        http_conn = self.bucket.connection.connection
        headers = {'Content-MD5':self.base64md5}
        if self.content_type:
            headers['Content-Type'] = self.content_type
        headers['Content-Length'] = self.size
        final_headers = boto.connection.merge_meta(headers, {});
        path = '/%s/%s' % (self.bucket.name, urllib.quote_plus(self.key))
        self.bucket.connection.add_aws_auth_header(final_headers, 'PUT', path)
        http_conn.putrequest('PUT', path)
        for key in final_headers:
            http_conn.putheader(key,final_headers[key])
        http_conn.endheaders()
        l = fp.read(4096)
        while len(l) > 0:
            http_conn.send(l)
            l = fp.read(4096)
        response = http_conn.getresponse()
        body = response.read()
        if response.status != 200:
            raise S3ResponseError(response.status, response.reason)
        self.etag = response.getheader('etag')
        if self.etag != self.md5:
            raise S3DataError('Injected data did not return correct MD5')

    def _compute_md5(self, fp):
        m = md5.new()
        s = fp.read(4096)
        while s:
            m.update(s)
            s = fp.read(4096)
        self.md5 = '"%s"' % m.hexdigest()
        self.base64md5 = base64.b64encode(m.digest())
        self.size = fp.tell()
        fp.seek(0)

    def set_contents_from_file(self, fp):
        if self.bucket != None:
            self._compute_md5(fp)
            if hasattr(fp, 'name'):
                self.content_type = mimetypes.guess_type(fp.name)[0]
            self.send_file(fp)

    def set_contents_from_filename(self, filename):
        fp = open(filename, 'rb')
        self.set_contents_from_file(fp)
        fp.close()

    def set_contents_from_string(self, s):
        fp = StringIO.StringIO(s)
        self.set_contents_from_file(fp)
        fp.close()

    def get_file(self, fp, headers={}):
        http_conn = self.bucket.connection.connection
        final_headers = boto.connection.merge_meta(headers, {})
        path = '/%s/%s' % (self.bucket.name, urllib.quote_plus(self.key))
        self.bucket.connection.add_aws_auth_header(final_headers, 'GET', path)
        http_conn.putrequest('GET', path)
        for key in final_headers:
            http_conn.putheader(key,final_headers[key])
        http_conn.endheaders()
        resp = http_conn.getresponse()
        response_headers = resp.msg
        for key in response_headers.keys():
            if key.lower() == 'content-length':
                self.size = response_headers[key]
            elif key.lower() == 'etag':
                self.etag = response_headers[key]
        l = resp.read(4096)
        while len(l) > 0:
            fp.write(l)
            l = resp.read(4096)
        resp.read()

    def get_contents_to_file(self, file):
        if self.bucket != None:
            self.get_file(file)

    def get_contents_to_filename(self, filename):
        fp = open(filename, 'wb')
        self.get_contents_to_file(fp)
        fp.close()

    def get_contents_as_string(self):
        fp = StringIO.StringIO()
        self.get_contents_to_file(fp)
        return fp.getvalue()

    # convenience methods for setting/getting ACL
    def set_acl(self, acl_str):
        if self.bucket != None:
            self.bucket.set_acl(acl_str, self.key)

    def get_acl(self):
        if self.bucket != None:
            return self.bucket.get_acl(self.key)
