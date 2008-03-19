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
from boto.services.message import ServiceMessage
import time, os

class Submitter:

    def __init__(self, bucket_name, queue_name, message_cls=ServiceMessage):
        self.s3 = boto.connect_s3()
        self.sqs = boto.connect_sqs()
        self.bucket = self.s3.get_bucket(bucket_name)
        self.queue = self.sqs.get_queue(queue_name)
        self.queue.set_message_class(message_cls)

    def submit_file(self, path, metadata=None, cb=None, num_cb=0):
        if not metadata:
            metadata = {}
        names = boto.config.get('Service', 'filenames', 'preserve')
        if names == 'preserve':
            key_name = os.path.split(path)[1]
        elif names == 'preserve_full':
            key_name = path
        else:
            key_name = None
        k = self.bucket.new_key(key_name)
        k.update_metadata(metadata)
        k.set_contents_from_filename(path, replace=False, cb=cb, num_cb=num_cb)
        m = ServiceMessage()
        m.for_key(k, metadata)
        self.queue.write(m)

    def submit_path(self, path, tags=None, ignore_dirs=[], cb=None, num_cb=0, status=False):
        total = 0
        metadata = {}
        if tags:
            metadata['Tags'] = tags
        l = []
        for t in time.gmtime():
            l.append(str(t))
        metadata['Batch'] = '_'.join(l)
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for ignore in ignore_dirs:
                    if ignore in dirs:
                        dirs.remove(ignore)
                for file in files:
                    fullpath = os.path.join(root, file)
                    if status:
                        print 'Submitting %s' % fullpath
                    self.submit_file(fullpath, metadata, cb, num_cb)
                    total += 1
        elif os.path.isfile(path):
            self.submit_file(path, metadata, cb, num_cb)
            total += 1
        else:
            print 'problem with %s' % path
        return total
