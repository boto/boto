11# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
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
import mimetypes

# Timezone formats
ISO8601 = '%Y-%m-%dT%H:%M:%SZ'
RFC1123 = '%a, %d %b %Y %X GMT'

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
                 on_completion='shutdown', notify_email=None,
                 read_userdata=True, working_dir=None, log_queue_name=None,
                 mimetype_files=None, preserve_file_name=False):
        self.meta_data = {}
        self.queue_cache = {}
        self.bucket_cache = {}
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.input_queue_name = input_queue_name
        self.output_queue_name = output_queue_name
        self.log_queue_name = log_queue_name
        self.notify_email = notify_email
        self.on_completion = on_completion
        self.preserve_file_name = preserve_file_name
        # now override any values with instance user data passed on startup
        if read_userdata:
            self.get_userdata()
        self.create_connections()
        self.create_working_dir(working_dir)
        if mimetype_files:
            mimetypes.init(mimetype_files)

    def get_userdata(self):
        self.meta_data = boto.utils.get_instance_metadata()
        d = boto.utils.get_instance_userdata(sep='|')
        if d:
            for key in d.keys():
                setattr(self, key, d[key])

    def create_connections(self):
        self.sqs_conn = SQSConnection(self.aws_access_key_id,
                                      self.aws_secret_access_key)
        if self.input_queue_name:
            self.input_queue = self.get_queue(self.input_queue_name)
        self.s3_conn = S3Connection(self.aws_access_key_id,
                                    self.aws_secret_access_key)

    def create_working_dir(self, working_dir):
        self.log(method='create_working_dir', working_dir=working_dir)
        if working_dir:
            self.working_dir = working_dir
        else:
            self.working_dir = os.path.expanduser('~/work')
        if not os.path.exists(self.working_dir):
            os.mkdir(self.working_dir)
        os.chdir(self.working_dir)

    def log(self, **params):
        if self.log_queue_name == None:
            return
        lq = self.get_queue(self.log_queue_name)
        m = lq.new_message()
        m['Timestamp'] = time.strftime(ISO8601, time.gmtime())
        for key in params:
            m[key] = params[key]
        lq.write(m)
        
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
            bucket = self.s3_conn.get_bucket(bucket_name)
            self.bucket_cache[bucket_name] = bucket
            return bucket

    def create_msg(self, key, params=None, bucket_name=None):
        m = self.input_queue.new_message()
        if params:
            m.update(params)
        if key.path:
            t = os.path.split(key.path)
            m['OriginalLocation'] = t[0]
            m['OriginalFileName'] = t[1]
            mime_type = mimetypes.guess_type(t[1])[0]
            if mime_type == None:
                mime_type = 'application/octet-stream'
            m['Content-Type'] = mime_type
            s = os.stat(key.path)
            t = time.gmtime(s[7])
            m['FileAccessedDate'] = time.strftime(ISO8601, t)
            t = time.gmtime(s[8])
            m['FileModifiedDate'] = time.strftime(ISO8601, t)
            t = time.gmtime(s[9])
            m['FileCreateDate'] = time.strftime(ISO8601, t)
        else:
            m['OriginalFileName'] = key.name
            m['OriginalLocation'] = key.bucket.name
            m['ContentType'] = key.content_type
        m['Date'] = time.strftime(RFC1123, time.gmtime())
        m['Host'] = gethostname()
        if bucket_name:
            m['Bucket'] = bucket_name
        else:
            m['Bucket'] = key.bucket.name
        m['InputKey'] = key.name
        m['Size'] = key.size
        return m

    def submit_file(self, path, bucket_name, metadata=None, cb=None, num_cb=0):
        if not metadata:
            metadata = {}
        bucket = self.get_bucket(bucket_name)
        if self.preserve_file_name:
            key_name = os.path.split(path)[1]
        else:
            key_name = None
        k = bucket.new_key(key_name)
        k.update_metadata(metadata)
        successful = False
        num_tries = 0
        while not successful and num_tries < self.RetryCount:
            try:
                num_tries += 1
                print 'submitting file: %s' % path
                k.set_contents_from_filename(path, replace=False,
                                             cb=cb, num_cb=num_cb)
                m = self.create_msg(k, metadata)
                self.input_queue.write(m)
                successful = True
            except S3ResponseError, e:
                print 'caught S3Error'
                print e
                time.sleep(self.RetryDelay)
            except SQSError, e:
                print 'caught SQSError'
                print e
                time.sleep(self.RetryDelay)

    def get_result(self, path, delete_msg=True, get_file=True):
        q = self.get_queue(self.output_queue_name)
        m = q.read()
        if m:
            if get_file:
                outputs = m['OutputKey'].split(',')
                for output in outputs:
                    key_name, type = output.split(';')
                    bucket = self.get_bucket(m['Bucket'])
                    key = bucket.lookup(key_name)
                    print 'retrieving file: %s' % key_name
                    key.get_contents_to_filename(os.path.join(path, key_name))
            if delete_msg:
                q.delete_message(m)
        return m

    def read_message(self):
        self.log(method='read_message')
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
                print 'caught SQSError'
                print e
                time.sleep(self.RetryDelay)
        return message

    # retrieve the source file from S3
    def get_file(self, bucket_name, key_name, file_name):
        self.log(method='get_file', bucket_name=bucket_name,
                 key=key_name, file_name=file_name)
        successful = False
        num_tries = 0
        while not successful and num_tries < self.RetryCount:
            try:
                num_tries += 1
                print 'getting file %s.%s' % (bucket_name, key_name)
                bucket = self.get_bucket(bucket_name)
                key = Key(bucket)
                key.name = key_name
                key.get_contents_to_filename(file_name)
                successful = True
            except S3ResponseError, e:
                print 'caught S3Error[%s]'
                print e
                time.sleep(self.RetryDelay)

    # process source file, return list of output files
    def process_file(self, in_file_name, msg):
        return []

    # store result file in S3
    def put_file(self, bucket_name, file_path):
        self.log(method='put_file', bucket_name=bucket_name,
                 file_path=file_path)
        successful = False
        num_tries = 0
        while not successful and num_tries < self.RetryCount:
            try:
                num_tries += 1
                bucket = self.get_bucket(bucket_name)
                if self.preserve_file_name:
                    key_name = os.path.split(file_path)[1]
                else:
                    key_name = None
                key = bucket.new_key(key_name)
                key.set_contents_from_filename(file_path)
                print 'putting file %s as %s.%s' % (file_path, bucket_name,
                                                    key.name)
                successful = True
            except S3ResponseError, e:
                print 'caught S3Error'
                print e
                time.sleep(self.RetryDelay)
        return key

    def _write_message(self, queue, message):
        successful = False
        num_tries = 0
        while not successful and num_tries < self.RetryCount:
            try:
                num_tries += 1
                queue.write(message)
                successful = True
            except SQSError, e:
                print 'caught SQSError'
                print e
                time.sleep(self.RetryDelay)

    # write message to each output queue
    def write_message(self, message):
        if self.output_queue_name:
            self.log(method='write_message')
            message['Service-Write'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT",
                                                     time.gmtime())
            message['Server'] = self.__class__.__name__
            if os.environ.has_key('HOSTNAME'):
                message['Host'] = os.environ['HOSTNAME']
            else:
                message['Host'] = 'unknown'
            queue = self.get_queue(self.output_queue_name)
            print 'writing message to %s' % queue.id
            self._write_message(queue, message)

    # delete message from input queue
    def delete_message(self, message):
        self.log(method='delete_message')
        print 'deleting message from %s' % self.input_queue.id
        successful = False
        num_tries = 0
        while not successful and num_tries < self.RetryCount:
            try:
                num_tries += 1
                self.input_queue.delete_message(message)
                successful = True
            except SQSError, e:
                print 'caught SQSError'
                print e
                time.sleep(self.RetryDelay)
                

    # to clean up any files, etc. after each iteration
    def cleanup(self):
        pass

    def shutdown(self):
        if self.on_completion == 'shutdown':
            if self.meta_data.has_key('instance-id'):
                time.sleep(60)
                c = EC2Connection(self.aws_access_key_id,
                                  self.aws_secret_access_key)
                c.terminate_instances([self.meta_data['instance-id']])

    def run(self, notify=False):
        self.notify('Service Starting')
        successful_reads = 0
        empty_reads = 0
        while empty_reads < self.MainLoopRetryCount:
            try:
                input_message = self.read_message()
                if input_message:
                    empty_reads = 0
                    successful_reads += 1
                    output_message = MHMessage(None, input_message.get_body())
                    in_key = input_message['InputKey']
                    in_file_name = input_message.get('OriginalFileName',
                                                     'in_file')
                    self.get_file(input_message['Bucket'], in_key,
                                  os.path.join(self.working_dir,in_file_name))
                    results = self.process_file(os.path.join(self.working_dir,
                                                             in_file_name),
                                                output_message)
                    if results != None:
                        output_keys = []
                        for file, type in results:
                            if input_message.has_key('OutputBucket'):
                                output_bucket = input_message['OutputBucket']
                            else:
                                output_bucket = input_message['Bucket']
                            key = self.put_file(output_bucket, file)
                            output_keys.append('%s;type=%s' % (key.name, type))
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

