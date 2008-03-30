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
from boto.pyami.scriptbase import ScriptBase
from boto.s3.key import Key
from boto.exception import S3ResponseError
from boto.utils import get_ts
import StringIO
import time
import os
import sys, traceback
import md5
import mimetypes

class Service(ScriptBase):

    # Number of times to retry queue read when no messages are available
    MainLoopRetryCount = 5
    
    # Number of seconds to wait before retrying queue read in main loop
    MainLoopDelay = 30

    # Time required to process a transaction
    ProcessingTime = 60

    def __init__(self):
        ScriptBase.__init__(self)
        self.name = self.__class__.__name__
        self.working_dir = boto.config.get('Pyami', 'working_dir')
        self._aws_cache = {}
        self.create_connections()
#        if mimetype_files:
#            mimetypes.init(mimetype_files)

    def create_connections(self):
        queue_name = boto.config.get(self.name, 'input_queue', None)
        if queue_name:
            self.input_queue = self.get_queue(queue_name)
        else:
            self.input_queue = None
        queue_name = boto.config.get(self.name, 'output_queue', None)
        if queue_name:
            self.output_queue = self.get_queue(queue_name)
        else:
            self.output_queue = None
        domain_name = boto.config.get(self.name, 'output_domain', None)
        if domain_name:
            self.output_domain = self.get_domain(domain_name)
        else:
            self.output_domain = None

    def split_key(key):
        if key.find(';') < 0:
            t = (key, '')
        else:
            key, type = key.split(';')
            label, mtype = type.split('=')
            t = (key, mtype)
        return t

    def get_queue(self, queue_name):
        return self.get_aws_object('sqs', queue_name)

    def get_domain(self, domain_name):
        return self.get_aws_object('sdb', domain_name)

    def get_bucket(self, bucket_name):
        return self.get_aws_object('s3', bucket_name)

    def get_aws_conn(self, service):
        conn = self._aws_cache.get(service, None)
        if not conn:
            meth = getattr(boto, 'connect_'+service)
            conn = meth()
            self._aws_cache[service] = conn
        return conn

    def get_aws_object(self, service, name):
        conn = self.get_aws_conn(service)
        obj = self._aws_cache.get(service+name, None)
        if not obj:
            if service == 's3':
                obj = conn.lookup(name)
                if not obj:
                    obj = conn.create_bucket(name)
                self._aws_cache[service+name] = obj
            elif service == 'sqs':
                obj = conn.get_queue(name)
                if not obj:
                    obj = conn.create_queue(name)
                self._aws_cache[service+name] = obj
                obj.set_message_class(ServiceMessage)
            elif service == 'sdb':
                obj = conn.lookup(name)
                if not obj:
                    obj = conn.create_domain(name)
                self._aws_cache[service+name] = obj
        return obj

    def get_result(self, path, delete_msg=True, get_file=True):
        q = self.get_queue(self.output_queue_name)
        m = q.read()
        if m:
            if get_file:
                outputs = m['OutputKey'].split(',')
                for output in outputs:
                    key_name, type = output.split(';')
                    if type:
                        mimetype = type.split('=')[1]
                    bucket = self.get_bucket(m['Bucket'])
                    key = bucket.lookup(key_name)
                    file_name = os.path.join(path, key_name)
                    print 'retrieving file: %s to %s' % (key_name, file_name)
                    key.get_contents_to_filename(file_name)
            if delete_msg:
                q.delete_message(m)
        return m

    def read_message(self):
        boto.log.info('read_message')
        message = self.input_queue.read(self.ProcessingTime)
        if message:
            boto.log.info(message.get_body())
            key = 'Service-Read'
            message[key] = get_ts()
        return message

    # retrieve the source file from S3
    def get_file(self, message):
        bucket_name = message['Bucket']
        key_name = message['InputKey']
        file_name = os.path.join(self.working_dir, message.get('OriginalFileName', 'in_file'))
        boto.log.info('get_file: %s/%s to %s' % (bucket_name, key_name, file_name))
        bucket = self.get_bucket(bucket_name)
        key = Key(bucket)
        key.name = key_name
        key.get_contents_to_filename(os.path.join(self.working_dir, file_name))
        return file_name

    # process source file, return list of output files
    def process_file(self, in_file_name, msg):
        return []

    # store result file in S3
    def put_file(self, bucket_name, file_path, key_name=None):
        boto.log.info('putting file %s as %s.%s' % (file_path, bucket_name, key_name))
        bucket = self.get_bucket(bucket_name)
        key = bucket.new_key(key_name)
        key.set_contents_from_filename(file_path)
        return key

    def save_results(self, results, input_message, output_message):
        output_keys = []
        for file, type in results:
            if input_message.has_key('OutputBucket'):
                output_bucket = input_message['OutputBucket']
            else:
                output_bucket = input_message['Bucket']
            key_name = os.path.split(file)[1]
            key = self.put_file(output_bucket, file, key_name)
            output_keys.append('%s;type=%s' % (key.name, type))
        output_message['OutputKey'] = ','.join(output_keys)
            
    # write message to each output queue
    def write_message(self, message):
        message['Service-Write'] = get_ts()
        message['Server'] = self.name
        if os.environ.has_key('HOSTNAME'):
            message['Host'] = os.environ['HOSTNAME']
        else:
            message['Host'] = 'unknown'
        message['Instance-ID'] = self.instance_id
        if self.output_queue:
            boto.log.info('Writing message to SQS queue: %s' % self.output_queue.id)
            self.output_queue.write(message)
        if self.output_domain:
            boto.log.info('Writing message to SDB domain: %s' % self.output_domain.name)
            item_name = '/'.join([message['Service-Write'], message['Bucket'], message['InputKey']])
            self.output_domain.put_attributes(item_name, message)

    # delete message from input queue
    def delete_message(self, message):
        boto.log.info('deleting message from %s' % self.input_queue.id)
        self.input_queue.delete_message(message)

    # to clean up any files, etc. after each iteration
    def cleanup(self):
        pass

    def shutdown(self):
        on_completion = boto.config.get(self.name, 'on_completion', 'stay_alive')
        if on_completion == 'shutdown':
            if self.instance_id:
                time.sleep(60)
                c = boto.connect_ec2()
                c.terminate_instances([self.instance_id])

    def main(self, notify=False):
        self.notify('Service: %s Starting' % self.name)
        empty_reads = 0
        while empty_reads < self.MainLoopRetryCount:
            try:
                input_message = self.read_message()
                if input_message:
                    empty_reads = 0
                    output_message = ServiceMessage(None, input_message.get_body())
                    input_file = self.get_file(input_message)
                    results = self.process_file(input_file, output_message)
                    self.save_results(results, input_message, output_message)
                    self.write_message(output_message)
                    self.delete_message(input_message)
                    self.cleanup()
                else:
                    empty_reads += 1
                    time.sleep(self.MainLoopDelay)
            except Exception, e:
                boto.log.exception('Service Failed')
                empty_reads += 1
                self.create_connections()
        self.notify('Service: %s Shutting Down' % self.name)
        self.shutdown()

