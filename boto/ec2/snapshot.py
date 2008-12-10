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
Represents an EC2 Elastic IP Snapshot
"""
from boto.ec2.ec2object import EC2Object

class Snapshot(EC2Object):
    
    def __init__(self, connection=None):
        EC2Object.__init__(self, connection)
        self.id = None
        self.progress = None
        self.start_time = None
        self.volume_id = None

    def __repr__(self):
        return 'Snapshot:%s' % self.id

    def endElement(self, name, value, connection):
        if name == 'snapshotId':
            self.id = value
        elif name == 'volumeId':
            self.volume_id = value
        elif name == 'startTime':
            self.start_time = value
        else:
            setattr(self, name, value)

    def _update(self, updated):
        self.progress = updated.progress

    def update(self):
        rs = self.connection.get_all_snapshots([self.id])
        if len(rs) > 0:
            self._update(rs[0])
        return self.progress
    
    def delete(self):
        return self.connection.delete_snapshot(self.id)



