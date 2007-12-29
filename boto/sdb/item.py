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

class Item(dict):
    
    def __init__(self, connection=None, name=None, domain_name=None, domain=None):
        dict.__init__(self)
        self.connection = connection
        self.name = name
        self.domain_name = domain_name
        self.domain = domain
        self.box_usage = 0
        self.request_id = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'ItemName':
            self.name = value
        elif name == 'Name':
            self.last_key = value
        elif name == 'Value':
            if self.has_key(self.last_key):
                if not isinstance(self[self.last_key], list):
                    self[self.last_key] = [self[self.last_key]]
                self[self.last_key].append(value)
            else:
                self[self.last_key] = value
        elif name == 'BoxUsage':
            if value:
                self.box_usage = float(value)
        elif name == 'RequestId':
            self.request_id = value
        else:
            setattr(self, name, value)

