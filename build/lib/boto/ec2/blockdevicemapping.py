# Copyright (c) 2009 Mitch Garnaat http://garnaat.org/
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
#

class BlockDeviceType(object):

    def __init__(self, connection=None):
        self.connection = connection
        self.ephemeral_name = None
        self.no_device = False
        self.volume_id = None
        self.snapshot_id = None
        self.status = None
        self.attach_time = None
        self.delete_on_termination = False
        self.size = None

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name =='volumeId':
            self.volume_id = value
        elif name == 'virtualName':
            self.ephemeral_name = value
        elif name =='NoDevice':
            self.no_device = (value == 'true')
        elif name =='snapshotId':
            self.snapshot_id = value
        elif name == 'volumeSize':
            self.size = int(value)
        elif name == 'status':
            self.status = value
        elif name == 'attachTime':
            self.attach_time = value
        elif name == 'deleteOnTermination':
            if value == 'true':
                self.delete_on_termination = True
            else:
                self.delete_on_termination = False
        else:
            setattr(self, name, value)

# for backwards compatibility
EBSBlockDeviceType = BlockDeviceType

class BlockDeviceMapping(dict):

    def __init__(self, connection=None):
        dict.__init__(self)
        self.connection = connection
        self.current_name = None
        self.current_value = None

    def startElement(self, name, attrs, connection):
        if name == 'ebs':
            self.current_value = BlockDeviceType(self)
            return self.current_value

    def endElement(self, name, value, connection):
        if name == 'device' or name == 'deviceName':
            self.current_name = value
        elif name == 'item':
            self[self.current_name] = self.current_value

    def build_list_params(self, params, prefix=''):
        i = 1
        for dev_name in self:
            pre = '%sBlockDeviceMapping.%d' % (prefix, i)
            params['%s.DeviceName' % pre] = dev_name
            block_dev = self[dev_name]
            if block_dev.ephemeral_name:
                params['%s.VirtualName' % pre] = block_dev.ephemeral_name
            else:
                if block_dev.no_device:
                    params['%s.Ebs.NoDevice' % pre] = 'true'
                if block_dev.snapshot_id:
                    params['%s.Ebs.SnapshotId' % pre] = block_dev.snapshot_id
                if block_dev.size:
                    params['%s.Ebs.VolumeSize' % pre] = block_dev.size
                if block_dev.delete_on_termination:
                    params['%s.Ebs.DeleteOnTermination' % pre] = 'true'
                else:
                    params['%s.Ebs.DeleteOnTermination' % pre] = 'false'
            i += 1
