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
import sys, os, pwd, tarfile
import boto
from boto.utils import get_instance_metadata, get_instance_userdata
from boto.pyami.config import Config
from boto.pyami.scriptbase import ScriptBase

MetadataConfigPath = '/etc/metadata.ini'

class LoadBoto(ScriptBase):
    """
    The LoadBoto class is instantiated and run as part of the PyAMI
    instance initialization process.  The methods in this class will
    be run from the rc.local script of the instance and will be run
    as the root user.

    The main purpose of this class is to download and install any required
    software packages prior to running the Pyami bootstrap command.
    """

    def __init__(self):
        self.working_dir = '/mnt/pyami'
        self.write_metadata()
        ScriptBase.__init__(self, self.config)

    def write_metadata(self):
        fp = open(os.path.expanduser(MetadataConfigPath), 'w')
        fp.write('[Instance]\n')
        inst_data = get_instance_metadata()
        for key in inst_data:
            fp.write('%s: %s\n' % (key, inst_data[key]))
        user_data = get_instance_userdata()
        fp.write('\n%s\n' % user_data)
        fp.write('working_dir: %s\n' % self.working_dir)
        fp.close()
        # now that we have written the file, read it into a pyami Config object
        self.config = Config(path=MetadataConfigPath)

    def write_env_setup(self):
        fp = open('/etc/profile.d/aws.sh', 'w')
        fp.write('\n# AWS Environment Setup Script\n')
        access_key = self.config.get_value('Credentials', 'aws_access_key_id', None)
        if access_key:
            fp.write('export AWS_ACCESS_KEY_ID=%s\n' % access_key)
        secret_key = self.config.get_value('Credentials', 'aws_secret_access_key', None)
        if secret_key:
            fp.write('export AWS_SECRET_ACCESS_KEY=%s\n' % secret_key)
        fp.close()

    def create_working_dir(self):
        print 'Working directory: %s' % self.working_dir
        if not os.path.exists(self.working_dir):
            os.mkdir(self.working_dir)

    def load_boto(self):
        update = self.config.get_value('Boto', 'boto_update', 'svn:HEAD')
        if update.startswith('svn'):
            if update.find(':') >= 0:
                method, version = update.split(':')
                version = '-r%s' % version
            else:
                version = '-rHEAD'
            location = self.config.get_value('Boto', 'boto_location', '/usr/local/boto')
            self.run('svn update %s %s' % (version, location))
        elif update.startswith('s3'):
            p = update.find(':')
            if p >= 0:
                try:
                    bucket_name, key_name = update[p+1:].split('/')
                    s3 = boto.connect_s3(self.config.get_value('Credentials', 'aws_access_key_id'),
                                         self.config.get_value('Credentials', 'aws_secret_access_key'))
                    bucket = s3.get_bucket(bucket_name)
                    key = bucket.get_key(key_name)
                    self.log_fp.write('\nFetching %s.%s\n' % (bucket_name, key_name))
                    path = os.path.join(self.working_dir, key.name)
                    key.get_contents_to_filename(path)
                    # first remove the symlink needed when running from subversion
                    self.run('rm /usr/local/lib/python2.5/site-packages/boto')
                    # now untar the downloaded file
                    tf = tarfile.open(path, 'r:gz')
                    tf.list(verbose=True)
                    dir_name = tf.getnames()[0]
                    tf.extractall(self.working_dir)
                    # now run the installer
                    setup_path = os.path.join(self.working_dir, dir_name)
                    old_dir = os.getcwd()
                    os.chdir(setup_path)
                    self.run('python setup.py install')
                    os.chdir(old_dir)
                except:
                    self.log_fp.write('\nProblem fetching from S3\n')

    def main(self):
        self.write_metadata()
        self.write_env_setup()
        self.create_working_dir()
        self.load_boto()
        self.notify('LoadBoto Completed for %s' % self.config.get_instance('instance-id'))

if __name__ == "__main__":
    lp = LoadBoto()
    lp.main()
