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
import sys, os, imp
import boto
from boto.utils import get_instance_metadata, get_instance_userdata

class Bootstrap:

    def __init__(self):
        self.inst_data = get_instance_metadata()
        self.user_data = get_instance_userdata(sep='|')

    def write_metadata(self):
        fp = open(os.path.expanduser('~pyami/metadata.ini'), 'w')
        fp.write('[Metadata]\n')
        for key in self.inst_data:
            fp.write('%s: %s\n' % (key, self.inst_data[key]))
        fp.write('[Userdata]\n')
        for key in self.user_data:
            fp.write('%s: %s\n' % (key, self.user_data[key]))
        fp.close()

    def write_env_setup(self):
        fp = open('/etc/profile.d/aws.sh', 'w')
        fp.write('# AWS Environment Setup Script\n')
        fp.write('export AWS_ACCESS_KEY_ID=%s\n' % self.user_data['aws_access_key_id'])
        fp.write('export AWS_SECRET_ACCESS_KEY=%s\n' % self.user_data['aws_secret_access_key'])
        fp.close()

    def create_working_dir(self):
        self.working_dir = self.user_data.get('working_dir', '/mnt/pyami')
        print 'Working directory: %s' % self.working_dir
        if not os.path.exists(self.working_dir):
            os.mkdir(self.working_dir)
        sys.path.append(self.working_dir)

    def run(self):
        self.write_metadata()
        self.write_env_setup()
        self.create_working_dir()

if __name__ == "__main__":
    bs = Bootstrap()
    bs.run()
