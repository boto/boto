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
import os
import boto
import time
from boto.utils import get_instance_metadata, get_instance_userdata
from boto.pyami.config import Config, BotoConfigPath
from boto.pyami.scriptbase import ScriptBase

class Bootstrap(ScriptBase):
    """
    The Bootstrap class is instantiated and run as part of the PyAMI
    instance initialization process.  The methods in this class will
    be run from the rc.local script of the instance and will be run
    as the root user.

    The main purpose of this class is to make sure the boto distribution
    on the instance is the one required.
    """

    def __init__(self):
        self.working_dir = '/mnt/pyami'
        self.write_metadata()

    def create_working_dir(self):
        boto.log.info('Working directory: %s' % self.working_dir)
        if not os.path.exists(self.working_dir):
            os.mkdir(self.working_dir)

    def write_metadata(self):
        fp = open(os.path.expanduser(BotoConfigPath), 'w')
        fp.write('[Instance]\n')
        inst_data = get_instance_metadata()
        for key in inst_data:
            fp.write('%s = %s\n' % (key, inst_data[key]))
        user_data = get_instance_userdata()
        fp.write('\n%s\n' % user_data)
        fp.write('[Pyami]\n')
        fp.write('working_dir = %s\n' % self.working_dir)
        fp.close()
        # This file has the AWS credentials, should we lock it down?
        # os.chmod(BotoConfigPath, stat.S_IREAD | stat.S_IWRITE)
        # now that we have written the file, read it into a pyami Config object
        boto.config = Config()
        boto.init_logging()

    def load_boto(self):
        update = boto.config.get('Boto', 'boto_update', 'svn:HEAD')
        if update.startswith('svn'):
            if update.find(':') >= 0:
                method, version = update.split(':')
                version = '-r%s' % version
            else:
                version = '-rHEAD'
            location = boto.config.get('Boto', 'boto_location', '/usr/local/boto')
            self.run('svn update %s %s' % (version, location))
        elif update.startswith('git'):
            location = boto.config.get('Boto', 'boto_location', '/usr/share/python-support/python-boto/boto')
            num_remaining_attempts = 10
            while num_remaining_attempts > 0:
                num_remaining_attempts -= 1
                try:
                    self.run('git pull', cwd=location)
                    num_remaining_attempts = 0
                except Exception, e:
                    boto.log.info('git pull attempt failed with the following exception. Trying again in a bit. %s', e)
                    time.sleep(2)
            if update.find(':') >= 0:
                method, version = update.split(':')

                #--
                #-- Determine whether we have a local branch matching "version"
                #-- If not, create it based on the remote branch
                #--
                swd = os.getcwd()
                os.chdir(location)
                branch_info = os.popen('git branch')
                branch_info = branch_info.read()
                branches = branch_info.split("\n")
                have_branch = False
                for branch in branches:
                    branch = branch.replace('*','')
                    branch = branch.strip()
                    if branch:
                        if branch == version:
                            have_branch = True
                            break
                if not have_branch:
                    os.system('git branch --track %s origin/%s' % (version, version))
                os.chdir(swd)
            else:
                version = 'master'
            self.run('git checkout %s' % version, cwd=location)
        else:
            # first remove the symlink needed when running from subversion
            self.run('rm /usr/local/lib/python2.5/site-packages/boto')
            self.run('easy_install %s' % update)


    def main(self):
        self.create_working_dir()
        self.load_boto()
        self.notify('Bootstrap Phase 1 Completed for %s' % boto.config.get_instance('instance-id'))

if __name__ == "__main__":
    # because bootstrap starts before any logging configuration can be loaded from
    # the boto config files, we will manually enable logging to /var/log/boto.log
    boto.set_file_logger('bootstrap', '/var/log/boto.log')
    bs = Bootstrap()
    bs.main()
