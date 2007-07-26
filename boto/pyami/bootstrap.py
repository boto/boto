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

def find_class(params):
    modules = params['module_name'].split('.')
    path = None
    for module_name in modules:
        fp, pathname, description = imp.find_module(module_name, path)
        module = imp.load_module(module_name, fp, pathname, description)
        if hasattr(module, '__path__'):
            path = module.__path__
    return getattr(module, params['class_name'])
  
class AmiInitializer:

    def __init__(self):
        self.inst_data = get_instance_metadata()
        self.user_data = get_instance_userdata(sep='|')

    def dump_data(self):
        print 'Instance Metadata'
        for key in self.inst_data:
            print '%s: %s' % (key, self.inst_data[key])
        print 'Instance Userdata'
        for key in self.user_data:
            print '%s: %s' % (key, self.user_data[key])

    def create_working_dir(self):
        self.working_dir = self.user_data.get('working_dir',
                                              os.path.expanduser('~/pyami'))
        print 'Working directory: %s' % self.working_dir
        if not os.path.exists(self.working_dir):
            os.mkdir(self.working_dir)
        sys.path.append(self.working_dir)

    def get_script(self):
        c = boto.connect_s3(self.user_data['aws_access_key_id'],
                            self.user_data['aws_secret_access_key'])
        bucket = c.get_bucket(self.user_data['bucket_name'])
        module_name = self.user_data['module_name'] + '.py'
        script = bucket.get_key(module_name)
        print 'Fetching %s.%s' % (bucket.name, script.name)
        script_path = os.path.join(self.working_dir, module_name)
        script.get_contents_to_filename(script_path)

    def run_script(self):
        cls = find_class(self.user_data)
        s = cls(self.inst_data, self.user_data)
        s.run()

    def run(self):
        self.dump_data()
        self.create_working_dir()
        self.get_script()
        self.run_script()

ai = AmiInitializer()
ai.run()
