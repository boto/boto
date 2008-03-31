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
#
import boto
from boto.pyami.scriptbase import ScriptBase
import os

class CopyBot(ScriptBase):

    def __init__(self, config):
        self.wdir = boto.config.get('Pyami', 'working_dir')
        self.instance_id = boto.config.get('Instance', 'instance-id')
        self.log_file = '%s.log' % self.instance_id
        self.log_path = os.path.join(self.wdir, self.log_file)
        boto.set_file_logger('CopyBot', self.log_path)
        self.s3 = boto.connect_s3()
        self.src = self.s3.get_bucket(boto.config.get('CopyBot', 'src_bucket'))
        self.dst = self.s3.create_bucket(boto.config.get('CopyBot', 'dst_bucket'))

    def main(self):
        boto.log.info('src=%s' % self.src)
        boto.log.info('dst=%s' % self.dst)
        for key in self.src:
            boto.log.info('key=%s' % key.name)
            path = os.path.join(self.wdir, key.name)
            key.get_contents_to_filename(path)
            key.bucket = self.dst
            key.set_contents_from_filename(path)
            os.unlink(path)
        boto.log.info('copy complete, shutting down')
        key = self.dst.new_key(self.log_file)
        key.set_contents_from_filename(self.log_path)
        ec2 = boto.connect_ec2()
        ec2.terminate_instances([self.instance_id])
        
