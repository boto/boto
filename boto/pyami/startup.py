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
import os, sys, traceback
import boto
from boto.utils import find_class
from boto import config
from boto.pyami.scriptbase import ScriptBase

class Startup(ScriptBase):

    def run_installer_commands(self):
        commands = config.get_value('Pyami', 'installer_commands')
        if commands:
            for command in commands.split(','):
                self.run('apt-get -y %s' % command)

    def load_packages(self):
        package_str = config.get_value('Pyami', 'packages')
        if package_str:
            packages = package_str.split(',')
            for package in packages:
                self.run('easy_install %s' % package, exit_on_error=False)

    def get_script(self):
        script_name = config.get_value('Pyami', 'script_name')
        if script_name:
            c = boto.connect_s3()
            script_name = script_name + '.py'
            script_bucket = config.get_value('Pyami', 'script_bucket')
            if not script_bucket:
                script_bucket = config.get_value('Pyami', 'bucket_name')
            bucket = c.get_bucket(script_bucket)
            script = bucket.get_key(script_name)
            print 'Fetching %s.%s' % (bucket.name, script.name)
            script_path = os.path.join(config.get_value('General', 'working_dir'), script_name)
            script.get_contents_to_filename(script_path)
            module_name = config.get_value('Pyami', 'script_name')
            sys.path.append(config.get_value('General', 'working_dir'))
            debug = config.getint('Boto', 'debug')
            # debug level greater than 1 means don't even startup the script
            if debug > 1:
                return
            if module_name:
                cls = find_class(module_name, config.get_value('Pyami', 'class_name'))
                s = cls(config)
                s.run()

    def run_scripts(self):
        scripts = config.get_value('Pyami', 'scripts')
        if scripts:
            for script in scripts.split(','):
                try:
                    self.log('Running Script: %s' % script)
                    module_name, class_name = script.split(':')
                    cls = find_class(module_name, class_name)
                    s = cls(self.log_fp)
                    s.run()
                except Exception, e:
                    self.log('Problem Running Script: %s' % script)
                    traceback.print_exc(None, self.log_fp)

    def main(self):
        self.run_installer_commands()
        self.load_packages()
        self.run_scripts()
        self.get_script()
        self.notify('Startup Completed for %s' % config.get_instance('instance-id'))

if __name__ == "__main__":
    su = Startup()
    su.main()
