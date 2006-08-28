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
from boto.owner import Owner
from boto.key import Key
from boto.exception import S3ResponseError
import xml.sax
import urllib

class Bucket:

    def __init__(self, connection=None, name=None, debug=None):
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

    # params can be one of: prefix, marker, max-keys, delimiter
    # as defined in S3 Developer's Guide, however since max-keys is not
    # a legal variable in Python you have to pass maxkeys and this
    # method will munge it (Ugh!)
    def get_all_keys(self, headers=None, **params):
        path = '/%s' % self.name
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
            h = handler.XmlHandler(self, {'Owner': Owner, 'Contents': Key})
            xml.sax.parseString(body, h)
            return h.rs
        else:
            raise S3ResponseError(response.status, response.reason)

    def delete_key(self, key):
        path = '/%s/%s' % (self.name, key.key)
        response = self.connection.make_request('DELETE', path)
        body = response.read()
        if response.status != 204:
            raise S3ResponseError(response.status, response.reason)
        

