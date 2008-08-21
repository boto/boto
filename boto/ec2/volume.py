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
Represents an EC2 Elastic IP Volume
"""

class Volume:
    
    def __init__(self, connection=None):
        self.connection = connection
        self.id = None
        self.instance_id = None
        self.snapshot_id = None
        self.size = None
        self.create_time = None
        self.attach_time = None

    def __repr__(self):
        return 'Volume:%s' % self.id

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'volumeId':
            self.id = value
        elif name == 'instanceId':
            self.instance_id = value
        elif name == 'snapshotId':
            self.snapshot_id = value
        elif name == 'createTime':
            self.create_time = value
        elif name == 'attachTime':
            self.attach_time = value
        elif name == 'size':
            self.size = int(value)
        else:
            setattr(self, name, value)

    def delete(self):
        return self.connection.delete_volume(self.id)

    def detach(self):
        return self.connection.detach_value(self.id, self.instance_id)



