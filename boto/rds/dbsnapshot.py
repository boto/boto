# Copyright (c) 2006-2009 Mitch Garnaat http://garnaat.org/
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

class DBSnapshot(object):
    """
    Represents a RDS DB Snapshot
    """
    
    def __init__(self, connection=None, id=None):
        self.connection = connection
        self.id = id
        self.engine = None
        self.snapshot_create_time = None
        self.instance_create_time = None
        self.port = None
        self.status = None
        self.availability_zone = None
        self.master_username = None
        self.allocated_storage = None
        self.instance_id = None
        self.availability_zone = None

    def __repr__(self):
        return 'DBSnapshot:%s' % self.id

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'Engine':
            self.engine = value
        elif name == 'InstanceCreateTime':
            self.instance_create_time = value
        elif name == 'SnapshotCreateTime':
            self.snapshot_create_time = value
        elif name == 'DBInstanceIdentifier':
            self.instance_id = value
        elif name == 'DBSnapshotIdentifier':
            self.id = value
        elif name == 'Port':
            self.port = int(value)
        elif name == 'Status':
            self.status = value
        elif name == 'AvailabilityZone':
            self.availability_zone = value
        elif name == 'MasterUsername':
            self.master_username = value
        elif name == 'AllocatedStorage':
            self.allocated_storage = int(value)
        elif name == 'SnapshotTime':
            self.time = value
        else:
            setattr(self, name, value)

            

