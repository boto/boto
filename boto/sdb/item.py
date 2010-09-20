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
Represents an SDB Item
"""

import base64

class Item(dict):
    
    def __init__(self, domain, name='', active=False):
        dict.__init__(self)
        self.domain = domain
        self.name = name
        self.active = active
        self.request_id = None
        self.encoding = None
        self.in_attribute = False
        self.converter = self.domain.connection.converter

    def startElement(self, name, attrs, connection):
        if name == 'Attribute':
            self.in_attribute = True
        self.encoding = attrs.get('encoding', None)
        return None

    def decode_value(self, value):
        if self.encoding == 'base64':
            self.encoding = None
            return base64.decodestring(value)
        else:
            return value

    def endElement(self, name, value, connection):
        if name == 'ItemName':
            self.name = self.decode_value(value)
        elif name == 'Name':
            if self.in_attribute:
                self.last_key = self.decode_value(value)
            else:
                self.name = self.decode_value(value)
        elif name == 'Value':
            if self.has_key(self.last_key):
                if not isinstance(self[self.last_key], list):
                    self[self.last_key] = [self[self.last_key]]
                value = self.decode_value(value)
                if self.converter:
                    value = self.converter.decode(value)
                self[self.last_key].append(value)
            else:
                value = self.decode_value(value)
                if self.converter:
                    value = self.converter.decode(value)
                self[self.last_key] = value
        elif name == 'BoxUsage':
            try:
                connection.box_usage += float(value)
            except:
                pass
        elif name == 'RequestId':
            self.request_id = value
        elif name == 'Attribute':
            self.in_attribute = False
        else:
            setattr(self, name, value)

    def load(self):
        self.domain.get_attributes(self.name, item=self)

    def save(self, replace=True):
        self.domain.put_attributes(self.name, self, replace)
        # Delete any attributes set to "None"
        if replace:
            del_attrs = []
            for name in self:
                if self[name] == None:
                    del_attrs.append(name)
            if len(del_attrs) > 0:
                self.domain.delete_attributes(self.name, del_attrs)

    def add_value(self, key, value):
        if key in self:
            if not isinstance(self[key], list):
                self[key] = [self[key]]
            self[key].append(value)
        else:
            self[key] = value

    def delete(self):
        self.domain.delete_item(self)

        
        

