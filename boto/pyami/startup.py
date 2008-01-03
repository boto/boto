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
from boto.pyami.config import Config

class Startup:

    def get_script(self):
        script_name = self.config.get_user('script_name')
        if script_name:
            c = boto.connect_s3(self.config.get_user('aws_access_key_id'),
                                self.config.get_user('aws_secret_access_key'))
            script_name = script_name + '.py'
            script_bucket = self.config.get_user('script_bucket')
            if not script_bucket:
                script_bucket = self.config.get_user('bucket_name')
            bucket = c.get_bucket(script_bucket)
            script = bucket.get_key(script_name)
            print 'Fetching %s.%s' % (bucket.name, script.name)
            script_path = os.path.join(self.config.get_user('working_dir'),
                                                          script_name)
            script.get_contents_to_filename(script_path)
            self.module_name = self.config.get_user('script_name')
            sys.path.append(self.config.get_user('working_dir'))
        else:
            self.module_name = self.config.get_user('module_name')

    def run_script(self):
        debug = self.config.getint_user('debug')
        # debug level greater than 1 means don't even startup the script
        if debug > 1:
            return
        if self.module_name:
            cls = find_class(self.module_name,
                             self.config.get_user('class_name'))
            s = cls(self.config)
            s.run()

    def main(self):
        self.config = Config()
        self.get_script()
        self.run_script()

if __name__ == "__main__":
    su = Startup()
    su.main()
