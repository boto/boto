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

"""
Represents an SQS Message
"""

import base64
import StringIO

class Message:
    
    def __init__(self, queue=None, body=''):
        self.queue = queue
        self.set_body(body)
        self.id = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'MessageBody':
            self.set_body_b64(value)
        elif name == 'MessageId':
            self.id = value
        else:
            setattr(self, name, value)

    def set_body(self, body):
        self.body = body

    def set_body_b64(self, body):
        self.body = base64.b64decode(body)
        self.set_body(self.body)

    def __len__(self):
        return len(self.body)

    def get_body(self):
        return self.body

    def get_body_b64(self):
        return base64.b64encode(self.get_body())

    def change_visibility(self, vtimeout):
        return self.queue.connection.change_message_visibility(self.queue.id,
                                                               self.id,
                                                               vtimeout)

#
# subclass that provides RFC821-like headers
#
class MHMessage(Message):

    def __init__(self, queue=None, body='', xml_attrs=None):
        self.dict = {}
        Message.__init__(self, queue, body)

    def set_body(self, body):
        fp = StringIO.StringIO(body)
        line = fp.readline()
        while line:
            delim = line.find(':')
            key = line[0:delim]
            value = line[delim+1:].strip()
            self.dict[key.strip()] = value.strip()
            line = fp.readline()

    def get_body(self):
        s = ''
        for key,value in self.dict.items():
            s = s + '%s: %s\n' % (key, value)
        return s

    def __len__(self):
        return len(self.get_body())

    def __getitem__(self, key):
        if self.dict.has_key(key):
            return self.dict[key]
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        self.dict[key] = value

    def keys(self):
        return self.dict.keys()

    def values(self):
        return self.dict.values()

    def items(self):
        return self.dict.items()

    def has_key(self, key):
        return self.dict.has_key(key)

    def update(self, d):
        return self.dict.update(d)

    def get(self, key, default=None):
        return self.dict.get(key, default)
        
