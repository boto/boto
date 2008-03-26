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

import boto
from boto.services.service import Service
from boto.services.message import ServiceMessage
import os, time, mimetypes

class SonOfMMM(Service):

    def __init__(self):
        Service.__init__(self)
        if boto.config.has_option('SonOfMMM', 'ffmpeg_args'):
            self.command = 'ffmpeg ' + boto.config.get('SonOfMMM', 'ffmpeg_args')
        else:
            self.command = 'ffmpeg -y -i %s %s'
        self.output_mimetype = boto.config.get('SonOfMMM', 'output_mimetype')
        if boto.config.has_option('SonOfMMM', 'output_ext'):
            self.output_ext = boto.config.get('SonOfMMM', 'output_ext')
        else:
            self.output_ext = mimetypes.guess_extension(self.output_mimetype)
        self.output_bucket_name = boto.config.get('SonOfMMM', 'output_bucket', None)
        self.input_bucket_name = boto.config.get('SonOfMMM', 'input_bucket', None)
        if self.input_bucket_name:
            self.queue_files()

    ProcessingTime = 300

    def queue_files(self):
        boto.log.info('Queueing files from %s' % self.input_bucket_name)
        bucket = self.get_bucket(self.input_bucket_name)
        for key in bucket:
            boto.log.info('Queueing %s' % key.name)
            m = ServiceMessage()
            m.for_key(key, {'OutputBucket' : self.output_bucket_name})
            self.input_queue.write(m)

    def process_file(self, in_file_name, msg):
        base, ext = os.path.splitext(in_file_name)
        out_file_name = os.path.join(self.working_dir,
                                     base+self.output_ext)
        command = self.command % (in_file_name, out_file_name)
        boto.log.info('running:\n%s' % command)
        status = self.run(command)
        if status == 0:
            return [(out_file_name, self.output_mimetype)]
        else:
            return []
        
