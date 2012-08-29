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
import os
import sys
from boto import config
from boto.utils import find_class
from boto.pyami.scriptbase import ScriptBase
from distutils.sysconfig import get_python_lib

class Startup(ScriptBase):

    def __init__(self):
        self.working_dir = '/mnt/pyami'
        self.python_lib = get_python_lib()
        ScriptBase.__init__(self)

    def run_scripts(self):
        scripts = config.get('Pyami', 'scripts')
        if scripts:
            for script in scripts.split(','):
                script = script.strip(" ")
                try:
                    pos = script.rfind('.')
                    if pos > 0:
                        mod_name = script[0:pos]
                        cls_name = script[pos+1:]
                        cls = find_class(mod_name, cls_name)
                        boto.log.info('Running Script: %s' % script)
                        s = cls()
                        s.main()
                    else:
                        boto.log.warning('Trouble parsing script: %s' % script)
                except Exception, e:
                    boto.log.exception('Problem Running Script: %s. Startup process halting.' % script)
                    raise e

    def fetch_s3_file(self, s3_file):
        try:
            from boto.utils import fetch_file
            f = fetch_file(s3_file)
            path = os.path.join(self.working_dir, s3_file.split("/")[-1])
            open(path, "w").write(f.read())
        except:
            boto.log.exception('Problem Retrieving file: %s' % s3_file)
            path = None
        return path

    def load_packages(self):
        package_str = boto.config.get('Pyami', 'packages')
        package_name = ""
        if package_str:
            packages = package_str.split(',')
            for package in packages:
                package = package.strip()
                if package.startswith('s3:'):
                    package = self.fetch_s3_file(package)
                    package_name = package.split("/")[-1]
                if package:
                    # if the "package" is really a .py file, it doesn't have to
                    # be installed, just being in the working dir is enough
                    if not package.endswith('.py'):
                        self.run('easy_install -Z %s' % package, exit_on_error=False)
                        sys.path.append("%s/%s" % (self.python_lib, package_name))
    def main(self):
        self.load_packages()
        self.run_scripts()
        self.notify('Startup Completed for %s' % config.get('Instance', 'instance-id'))

if __name__ == "__main__":
    if not config.has_section('loggers'):
        boto.set_file_logger('startup', '/var/log/boto.log')
    sys.path.append(config.get('Pyami', 'working_dir'))
    su = Startup()
    su.main()
