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

from boto.services.service import Service
from boto.utils import ShellCommand
import StringIO

class CommandLineService(Service):

    def log_data(self, data):
        out_file_name = self.__class__.__name__ + '.log'
        out_file_name = os.path.join(self.working_dir, out_file_name)
        out_fp = open(out_file_name, 'a')
        out_fp.write(data)
        out_fp.close()
        
    def run_command(self, command, msg, debug=0):
        log_fp = StringIO.StringIO()
        log_fp.write(msg.get_body())
        log_fp.write('\n')
        c = ShellCommand(command, log_fp)
        # only log unsuccessful commands unless debug flag is set
        if c.status != 0 or debug > 0:
            self.log_data(c.output)
        return c.status
        
