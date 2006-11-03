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

"""
Represents an SQS Message
"""

class Message:
    
    def __init__(self, queue=None, body='', xml_attrs=None):
        self.queue = queue
        self.set_body(body)
        self.id = None

    # This allows the XMLHandler to set the attributes as they are named
    # in the XML response but have the capitalized names converted to
    # more conventional looking python variables names automatically
    def __setattr__(self, key, value):
        if key == 'MessageBody':
            self.set_body(value)
            self.__dict__['body'] = value
        elif key == 'MessageId':
            self.__dict__['id'] = value
        else:
            self.__dict__[key] = value

    def set_body(self, body):
        self.body = body

    def __len__(self):
        return len(self.body)

    def get_body(self):
        return self.body


