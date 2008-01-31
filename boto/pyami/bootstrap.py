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
import sys, os, pwd
import boto
from boto.utils import get_instance_metadata, get_instance_userdata
from boto.pyami.config import Config, BotoConfigPath

class Bootstrap:
    """
    The Bootstrap class is instantiated and run as part of the PyAMI
    instance initialization process.  The methods in this class will
    be run from the rc.local script of the instance and will be run
    as the root user.

    This version is a new variation that is meant to work with ubuntu
    and also to simplify some of the Pyami startup stuff.
    """

    def __init__(self):
        self.config = None
        self.working_dir = '/mnt/pyami'

    def write_metadata(self):
        fp = open(os.path.expanduser(BotoConfigPath), 'w')
        fp.write('[Instance]\n')
        inst_data = get_instance_metadata()
        for key in inst_data:
            fp.write('%s = %s\n' % (key, inst_data[key]))
        fp.write('[User]\n')
        user_data = get_instance_userdata(sep='|')
        for key in user_data:
            fp.write('%s = %s\n' % (key, user_data[key]))
        fp.write('[General]\n')
        fp.write('working_dir = %s\n' % self.working_dir)
        fp.close()
        # now that we have written the file, read it into a pyami Config object
        self.config = Config(BotoConfigPath)

    def write_env_setup(self):
        fp = open('/etc/profile.d/aws.sh', 'w')
        fp.write('\n# AWS Environment Setup Script\n')
        access_key = self.config.get_user('aws_access_key_id', None)
        if access_key:
            fp.write('export AWS_ACCESS_KEY_ID=%s\n' % access_key)
        secret_key = self.config.get_user('aws_secret_access_key', None)
        if secret_key:
            fp.write('export AWS_SECRET_ACCESS_KEY=%s\n' % secret_key)
        fp.close()

    def create_working_dir(self):
        print 'Working directory: %s' % self.working_dir
        if not os.path.exists(self.working_dir):
            os.mkdir(self.working_dir)

    def main(self):
        self.write_metadata()
        self.write_env_setup()
        self.create_working_dir()

if __name__ == "__main__":
    bs = Bootstrap()
    bs.main()
