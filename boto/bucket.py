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

class Bucket:

    def __init__(self, connection=None, name=None, prefix=None,
                 page_size=100, debug=None):
        self.name = name
        self.connection = connection
        self.page_size = page_size
        self.debug = debug

    def __setattr__(self, key, value):
        if key == 'Name':
            self.__dict__['name'] = value
        elif key == 'CreationDate':
            self.__dict__['creation_date'] = value
        else:
            self.__dict__[key] = value

    def get_all_contents(self, marker=None, headers=None):
        path = '/%s' % self.name
        if marker:
            path = path + '?marker=%s' % marker
        response = self.connection.make_request('GET', path, headers)
        body = response.read()
        if response.status == 200:
            h = handler.XmlHandler(self, {'Owner': Owner, 'Contents': Key})
            xml.sax.parseString(body, h)
            return h.rs
        else:
            raise S3ResponseError(response.status, response.reason)

    def delete_contents(self, contents):
        path = '/%s/%s' % (self.name, contents.key)
        response = self.connection.make_request('DELETE', path)
        body = response.read()
        if response.status != 204:
            raise S3ResponseError(response.status, response.reason)
        
#     def __repr__(self):
#         return 'Bucket(%s)' % self.name

