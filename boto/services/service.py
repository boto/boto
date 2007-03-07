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

from boto.s3.connection import S3Connection
from boto.sqs.connection import SQSConnection
from boto.ec2.connection import EC2Connection
from boto.s3.key import Key
from boto.sqs.message import MHMessage
from boto.exception import SQSError, S3ResponseError
import boto.utils
import StringIO
import time
import os
import sys, traceback
import md5
from socket import gethostname

class Service:

    # Number of times to retry failed requests to S3 or SQS
    RetryCount = 5

    # Number of seconds to wait between Retries
    RetryDelay = 5

    # Number of times to retry queue read when no messages are available
    MainLoopRetryCount = 5
    
    # Number of seconds to wait before retrying queue read in main loop
    MainLoopDelay = 30

    # Time required to process a transaction
    ProcessingTime = 60

    # Number of successful queue reads before spawning helpers
    SpawnCount = 10

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 input_queue_name=None, output_queue_name=None,
                 do_shutdown=False, notify_email=None, read_userdata=True,
                 working_dir=None):
        self.meta_data = {}
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.input_queue_name = input_queue_name
        self.output_queue_name = output_queue_name
        self.notify_email = notify_email
        self.do_shutdown = do_shutdown
        # now override any values with instance user data passed on startup
        if read_userdata:
            self.get_userdata()
        self.create_working_dir(working_dir)
        self.create_connections()

    def get_userdata(self):
        self.meta_data = boto.utils.get_instance_metadata()
        d = boto.utils.get_instance_userdata(sep='|')
        if d:
            for key in d.keys():
                setattr(self, key, d[key])

    def create_connections(self):
        self.queue_cache = {}
        self.bucket_cache = {}
        self.sqs_conn = SQSConnection(self.aws_access_key_id,
                                      self.aws_secret_access_key)
        if self.input_queue_name:
            self.input_queue = self.get_queue(self.input_queue_name)
        self.s3_conn = S3Connection(self.aws_access_key_id,
                                    self.aws_secret_access_key)

    def create_working_dir(self, working_dir):
        if working_dir:
            self.working_dir = working_dir
        else:
            self.working_dir = os.path.expanduser('~/work')
        if not os.path.exists(self.working_dir):
            os.mkdir(self.working_dir)
        os.chdir(self.working_dir)
        
    def notify(self, msg):
        if self.notify_email:
            import smtplib, socket
            subject = "Message from Server - %s" % self.__class__.__name__
            body = "From: %s\r\n" % self.notify_email
            body = body + "To: %s\r\n" % self.notify_email
            body = body + "Subject: " + subject + '\r\n\r\n'
            body = body + 'Server: %s\n' % self.__class__.__name__
            body = body + 'Host: %s\n' % socket.gethostname()
            body = body + msg
            server = smtplib.SMTP('localhost')
            server.sendmail(self.notify_email, self.notify_email, body)
            server.quit()
        
    def compute_key(self, filename):
        fp = open(filename, 'rb')
        m = md5.new()
        s = fp.read(4096)
        while s:
            m.update(s)
            s = fp.read(4096)
        fp.close()
        return m.hexdigest()

    def split_key(key):
        if key.find(';') < 0:
            t = (key, '')
        else:
            key, type = key.split(';')
            label, mtype = type.split('=')
            t = (key, mtype)
        return t

    def get_queue(self, queue_name):
        if queue_name in self.queue_cache.keys():
            return self.queue_cache[queue_name]
        else:
            queue = self.sqs_conn.create_queue(queue_name)
            queue.set_message_class(MHMessage)
            self.queue_cache[queue_name] = queue
            return queue

    def get_bucket(self, bucket_name):
        if bucket_name in self.bucket_cache.keys():
            return self.bucket_cache[bucket_name]
        else:
            bucket = self.s3_conn.create_bucket(bucket_name)
            self.bucket_cache[bucket_name] = bucket
            return bucket

    def key_exists(self, bucket_name, key):
        bucket = self.get_bucket(bucket_name)
        return bucket.lookup(key)

    def create_msg(self, key, params=None):
        m = self.input_queue.new_message()
        if params:
            m.update(params)
        if key.path:
            t = os.path.split(key.path)
            m['OriginalLocation'] = t[0]
            m['OriginalFileName'] = t[1]
        m['Date'] = time.strftime("%a, %d %b %Y %X GMT",
                                  time.gmtime())
        m['Host'] = gethostname()
        m['Bucket'] = key.bucket.name
        m['InputKey'] = key.key
        m['Size'] = key.size
        return m

    def submit_file(self, path, bucket_name, metadata=None):
        if not metadata:
            metadata = {}
        bucket = self.get_bucket(bucket_name)
        k = bucket.new_key()
        k.update_metadata(metadata)
        successful = False
        num_tries = 0
        while not successful and num_tries < self.RetryCount:
            try:
                num_tries += 1
                print 'submitting file: %s' % path
                k.set_contents_from_filename(path, replace=False)
                m = self.create_msg(k, metadata)
                print m.get_body()
                self.input_queue.write(m)
                successful = True
            except S3ResponseError, e:
                print 'caught S3Error[%s]: %s' % (e.status, e.reason)
                time.sleep(self.RetryDelay)
            except SQSError, e:
                print 'caught SQSError[%s]: %s' % (e.status, e.reason)
                time.sleep(self.RetryDelay)

    def get_result(self, path)
    # read a new message from our queue
    def read_message(self):
        message = None
        successful = False
        num_tries = 0
        while not successful and num_tries < self.RetryCount:
            try:
                num_tries += 1
                message = self.input_queue.read(self.ProcessingTime)
                if message:
                    print message.get_body()
                    key = 'Service-Read'
                    message[key] = time.strftime("%a, %d %b %Y %H:%M:%S GMT",
                                                 time.gmtime())
                successful = True
            except SQSError, e:
                print 'caught SQSError[%s]: %s' % (e.status, e.reason)
                time.sleep(self.RetryDelay)
        return message

    # retrieve the source file from S3
    def get_file(self, bucket_name, key, file_name):
        successful = False
        num_tries = 0
        while not successful and num_tries < self.RetryCount:
            try:
                num_tries += 1
                print 'getting file %s.%s' % (bucket_name, key)
                bucket = self.get_bucket(bucket_name)
                k = Key(bucket)
                k.key = key
                k.get_contents_to_filename(file_name)
                successful = True
            except S3ResponseError, e:
                print 'caught S3Error[%s]: %s' % (e.status, e.reason)
                time.sleep(self.RetryDelay)

    # process source file, return list of output files
    def process_file(self, in_file_name, msg):
        return []

    # store result file in S3
    def put_file(self, bucket_name, file_name):
        successful = False
        num_tries = 0
        while not successful and num_tries < self.RetryCount:
            try:
                num_tries += 1
                bucket = self.get_bucket(bucket_name)
                k = Key(bucket)
                k.set_contents_from_filename(file_name)
                print 'putting file %s as %s.%s' % (file_name, bucket_name, k.key)
                successful = True
            except S3ResponseError, e:
                print 'caught S3Error[%s]: %s' % (e.status, e.reason)
                time.sleep(self.RetryDelay)
        return k

    # write message to each output queue
    def write_message(self, message):
        message['Service-Write'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT",
                                                 time.gmtime())
        message['Server'] = self.__class__.__name__
        if os.environ.has_key('HOSTNAME'):
            message['Host'] = os.environ['HOSTNAME']
        else:
            message['Host'] = 'unknown'
        queue = self.get_queue(self.output_queue_name)
        print 'writing message to %s' % queue.id
        successful = False
        num_tries = 0
        while not successful and num_tries < self.RetryCount:
            try:
                num_tries += 1
                print message.get_body()
                queue.write(message)
                successful = True
            except SQSError, e:
                print 'caught SQSError[%s]: %s' % (e.status, e.reason)
                time.sleep(self.RetryDelay)

    # delete message from input queue
    def delete_message(self, message):
        print 'deleting message from %s' % self.input_queue.id
        successful = False
        num_tries = 0
        while not successful and num_tries < self.RetryCount:
            try:
                num_tries += 1
                self.input_queue.delete_message(message)
                successful = True
            except SQSError, e:
                print 'caught SQSError[%s]: %s' % (e.status, e.reason)
                time.sleep(self.RetryDelay)
                

    # to clean up any files, etc. after each iteration
    def cleanup(self):
        pass

    def shutdown(self):
        if self.do_shutdown and self.meta_data.has_key('instance-id'):
            time.sleep(60)
            c = EC2Connection(self.aws_access_key_id,
                              self.aws_secret_access_key)
            c.terminate_instances([self.meta_data['instance-id']])

    def spawn_children(self):
        self.notify('%s - Spawning Child' % self.meta_data['instance-id'])

    def run(self, notify=False):
        self.notify('Service Starting')
        successful_reads = 0
        empty_reads = 0
        while empty_reads < self.MainLoopRetryCount:
            try:
                if successful_reads >= self.SpawnCount:
                    self.spawn_children()
                    successful_reads = 0
                input_message = self.read_message()
                if input_message:
                    empty_reads = 0
                    successful_reads += 1
                    output_message = MHMessage(None, input_message.get_body())
                    in_key = input_message['InputKey']
                    self.get_file(input_message['Bucket'], in_key,
                                  os.path.join(self.working_dir,'in_file'))
                    results = self.process_file(os.path.join(self.working_dir,
                                                             'in_file'),
                                                output_message)
                    output_keys = []
                    for file, type in results:
                        key = self.put_file(input_message['Bucket'], file)
                        output_keys.append('%s;type=%s' % (key.key, type))
                    output_message['OutputKey'] = ','.join(output_keys)
                    self.write_message(output_message)
                    self.delete_message(input_message)
                    self.cleanup()
                else:
                    empty_reads += 1
                    successful_reads = 0
                    time.sleep(self.MainLoopDelay)
            except Exception, e:
                empty_reads += 1
                successful_reads = 0
                fp = StringIO.StringIO()
                traceback.print_exc(None, fp)
                s = fp.getvalue()
                self.notify('Service failed\n%s' % s)
                self.create_connections()
        self.notify('Service Shutting Down')
        self.shutdown()

