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
import os, sys
import boto
from boto.utils import find_class
from boto import config

class Startup:

    def get_eggs(self):
        egg_bucket = config.get_value('Boto', 'egg_bucket', None)
        if egg_bucket:
            s3 = boto.connect_s3()
            bucket = s3.get_bucket(egg_bucket)
            eggs = config.get_value('Boto', 'eggs', '')
            for egg in eggs.split(','):
                if egg:
                    egg_key = bucket.get_key(egg.strip())
                    print 'Fetching %s.%s' % (bucket.name, egg_key.name)
                    egg_path = os.path.join(config.get_value('General', 'working_dir'), egg_key.name)
                    egg_key.get_contents_to_filename(egg_path)
            
    def get_script(self):
        script_name = config.get_value('Boto', 'script_name')
        if script_name:
            c = boto.connect_s3()
            script_name = script_name + '.py'
            script_bucket = config.get_value('Boto', 'script_bucket')
            if not script_bucket:
                script_bucket = self.config.get_value('Boto', 'bucket_name')
            bucket = c.get_bucket(script_bucket)
            script = bucket.get_key(script_name)
            print 'Fetching %s.%s' % (bucket.name, script.name)
            script_path = os.path.join(config.get_value('General', 'working_dir'), script_name)
            script.get_contents_to_filename(script_path)
            self.module_name = config.get_value('Boto', 'script_name')
            sys.path.append(config.get_value('General', 'working_dir'))
        else:
            self.module_name = config.get_value('Boto', 'module_name')

    def run_script(self):
        try:
            debug = config.getint('Boto', 'debug')
        except:
            debug = 0
        # debug level greater than 1 means don't even startup the script
        if debug > 1:
            return
        if self.module_name:
            cls = find_class(self.module_name, config.get_value('Boto', 'class_name'))
            s = cls()
            s.run()

    def main(self):
        self.get_script()
        self.run_script()

if __name__ == "__main__":
    su = Startup()
    su.main()
