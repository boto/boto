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
import StringIO
import ConfigParser

MetadataConfigPath = '/home/pyami/metadata.ini'

class Config(ConfigParser.RawConfigParser):

    def __init__(self, path=MetadataConfigPath, fp=None):
        ConfigParser.RawConfigParser.__init__(self)
        if path:
            self.read(path)
        if fp:
            self.readfp(fp)

    def get_instance(self, name, default=None):
        try:
            val = self.get('Instance', name)
        except:
            val = default
        return val

    def get_user(self, name, default=None):
        try:
            val = self.get('User', name)
        except:
            val = default
        return val

    def getint_user(self, name, default=0):
        try:
            val = self.getint('User', name)
        except:
            val = default
        return val

    def get_value(self, section, name, default=None):
        try:
            val = self.get(section, name)
        except:
            val = default
        return val
    
    def dump(self):
        s = StringIO.StringIO()
        self.write(s)
        print s.getvalue()

    def dump_safe(self, fp=None):
        if not fp:
            fp = StringIO.StringIO()
        for section in self.sections():
            fp.write('[%s]\n' % section)
            for option in self.options(section):
                if option == 'aws_secret_access_key':
                    fp.write('%s: xxxxxxxxxxxxxxxxxx\n' % option)
                else:
                    fp.write('%s: %s\n' % (option, self.get(section, option)))
    
