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

"""
Represents an EC2 Elastic IP Snapshot
"""
from boto.ec2.ec2object import EC2Object

class Snapshot(EC2Object):
    
    def __init__(self, connection=None):
        EC2Object.__init__(self, connection)
        self.id = None
        self.volume_id = None
        self.status = None
        self.progress = None
        self.start_time = None
        self.owner_id = None
        self.volume_size = None
        self.description = None

    def __repr__(self):
        return 'Snapshot:%s' % self.id

    def endElement(self, name, value, connection):
        if name == 'snapshotId':
            self.id = value
        elif name == 'volumeId':
            self.volume_id = value
        elif name == 'status':
            self.status = value
        elif name == 'startTime':
            self.start_time = value
        elif name == 'ownerId':
            self.owner_id = value
        elif name == 'volumeSize':
            self.volume_size = int(value)
        elif name == 'description':
            self.description = value
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

    def get_permissions(self):
        attrs = self.connection.get_snapshot_attribute(self.id,
                                                       attribute='createVolumePermission')
        return attrs.attrs

    def share(self, user_ids=None, groups=None):
        return self.connection.modify_snapshot_attribute(self.id,
                                                         'createVolumePermission',
                                                         'add',
                                                         user_ids,
                                                         groups)

    def unshare(self, user_ids=None, groups=None):
        return self.connection.modify_snapshot_attribute(self.id,
                                                         'createVolumePermission',
                                                         'remove',
                                                         user_ids,
                                                         groups)

    def reset_permissions(self):
        return self.connection.reset_snapshot_attribute(self.id, 'createVolumePermission')

class SnapshotAttribute:

    def __init__(self, parent=None):
        self.snapshot_id = None
        self.attrs = {}

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'createVolumePermission':
            self.name = 'create_volume_permission'
        elif name == 'group':
            if self.attrs.has_key('groups'):
                self.attrs['groups'].append(value)
            else:
                self.attrs['groups'] = [value]
        elif name == 'userId':
            if self.attrs.has_key('user_ids'):
                self.attrs['user_ids'].append(value)
            else:
                self.attrs['user_ids'] = [value]
        elif name == 'snapshotId':
            self.snapshot_id = value
        else:
            setattr(self, name, value)


            
