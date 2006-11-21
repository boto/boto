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

from boto import handler
from boto.acl import Policy, ACL, Grant, CannedACLStrings
from boto.user import User
from boto.key import Key
from boto.exception import S3ResponseError
import xml.sax
import urllib

class Bucket:

    def __init__(self, connection=None, name=None, debug=None, xml_attrs=None):
        self.name = name
        self.connection = connection
        self.debug = debug

    # This allows the XMLHandler to set the attributes as they are named
    # in the XML response but have the capitalized names converted to
    # more conventional looking python variables names automatically
    def __setattr__(self, key, value):
        if key == 'Name':
            self.__dict__['name'] = value
        elif key == 'CreationDate':
            self.__dict__['creation_date'] = value
        else:
            self.__dict__[key] = value

    def lookup(self, key):
        path = '/%s/%s' % (self.name, key)
        response = self.connection.make_request('HEAD', urllib.quote(path))
        if response.status == 200:
            body = response.read()
            k = Key()
            k.bucket = self
            k.get_all_metadata(response.msg)
            k.etag = response.getheader('etag')
            k.content_type = response.getheader('content-type')
            k.last_modified = response.getheader('last-modified')
            k.key = key
            return k
        else:
            # -- gross hack --
            # httplib gets confused with chunked responses to HEAD requests
            # so I have to fake it out
            response.chunked = 0
            body = response.read()
            return None

    # params can be one of: prefix, marker, max-keys, delimiter
    # as defined in S3 Developer's Guide, however since max-keys is not
    # a legal variable in Python you have to pass maxkeys and this
    # method will munge it (Ugh!)
    def get_all_keys(self, headers=None, **params):
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
        if response.status == 200:
            h = handler.XmlHandler(self, {'Owner': User, 'Contents': Key})
            xml.sax.parseString(body, h)
            return h.rs
        else:
            raise S3ResponseError(response.status, response.reason)

    def delete_key(self, key_name):
        # for backward compatibility, previous version expected a Key object
        if isinstance(key_name, Key):
            key_name = key_name.key
        path = '/%s/%s' % (self.name, key_name)
        response = self.connection.make_request('DELETE',
                                                urllib.quote(path))
        body = response.read()
        if response.status != 204:
            raise S3ResponseError(response.status, response.reason)

    def set_acl(self, acl_str, key_name=None):
        # just in case user passes a Key object rather than key name
        if isinstance(key_name, Key):
            key_name = key_name.key
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
            raise S3ResponseError(response.status, response.reason)

    def get_acl(self, key_name=None):
        # just in case user passes a Key object rather than key name
        if isinstance(key_name, Key):
            key_name = key_name.key
        if key_name:
            path = '/%s/%s' % (self.name, key_name)
        else:
            path = '/%s' % self.name
        path = urllib.quote(path) + '?acl'
        response = self.connection.make_request('GET', path)
        body = response.read()
        if response.status == 200:
            h = handler.XmlHandler(self, {'AccessControlPolicy' : Policy,
                                          'AccessControlList' : ACL,
                                          'Grant': Grant,
                                          'Grantee': User,
                                          'Owner' : User})
            xml.sax.parseString(body, h)
            return h.rs[0]
        else:
            raise S3ResponseError(response.status, response.reason)

        

