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

from boto.connection import SQSConnection, S3Connection
from boto.s3.key import Key
from boto.sqs.message import MHMessage
from boto.exception import SQSError, S3ResponseError
import boto.utils
import StringIO
import time
import os
import sys, traceback
import md5

class Service:

    RetryCount = 5
    ProcessingTime = 60

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
        else:
        self.create_working_dir(working_dir)
        self.create_connections()

    def get_userdata(self):
        self.meta_data = boto.utils.get_instance_metadata()
        s = boto.utils.get_instance_userdata()
        if s:
            l = s.split('|')
            for nvpair in l:
                t = nvpair.split('=')
                setattr(self, t[0].strip(), t[1].strip())

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
            self.working_dir = os.path.expanduser('~/%s' % working_dir)
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

    # read a new message from our queue
    def read_message(self):
        try:
            message = self.input_queue.read(self.ProcessingTime)
            if message:
                print message.get_body()
                key = 'Service-Read'
                message[key] = time.strftime("%a, %d %b %Y %H:%M:%S GMT",
                                             time.gmtime())
        except SQSError, e:
            print 'caught SQSError[%s]: %s' % (e.status, e.reason)
            message = None
        return message

    # retrieve the source file from S3
    def get_file(self, bucket_name, key, file_name):
        successful = False
        while not successful:
            try:
                print 'getting file %s.%s' % (bucket_name, key)
                bucket = self.get_bucket(bucket_name)
                k = Key(bucket)
                k.key = key
                k.get_contents_to_filename(file_name)
                successful = True
            except S3ResponseError, e:
                print 'caught S3Error[%s]: %s' % (e.status, e.reason)

    # process source file, return list of output files
    def process_file(self, in_file_name, msg):
        return []

    # store result file in S3
    def put_file(self, bucket_name, file_name, key):
        print 'put_file(%s, %s, %s)' % (bucket_name, file_name, key)
        successful = False
        while not successful:
            try:
                bucket = self.get_bucket(bucket_name)
                k = Key(bucket)
                k.key = key
                k.set_contents_from_filename(file_name)
                print 'putting file %s as %s.%s' % (file_name, bucket_name, k.key)
                successful = True
            except S3ResponseError, e:
                print 'caught S3Error[%s]: %s' % (e.status, e.reason)
        return k.key

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
                

    # to clean up any files, etc. after each iteration
    def cleanup(self):
        pass

    def shutdown(self):
        if self.do_shutdown and self.meta_data.has_key('instance-id'):
            c = boto.connect_ec2()
            c.terminate_instances([self.meta_data['instance-id']])

    def run(self, notify=False):
        self.notify('Service Starting')
        num_tries = 0
        while num_tries < self.RetryCount:
            try:
                input_message = self.read_message()
                if input_message:
                    num_tries = 0
                    output_message = MHMessage(None, input_message.get_body())
                    in_key = input_message['Key']
                    self.get_file(input_message['Bucket'], in_key,
                                  os.path.join(self.working_dir,'in_file'))
                    results = self.process_file(os.path.join(self.working_dir,
                                                             'in_file'),
                                                output_message)
                    print 'results=', results
                    output_keys = []
                    for file, type in results:
                        key = self.compute_key(file)
                        output_keys.append('%s;type=%s' % (key, type))
                        self.put_file(input_message['Bucket'], file, key)
                    output_message['OutputKey'] = ','.join(output_keys)
                    self.write_message(output_message)
                    self.delete_message(input_message)
                    self.cleanup()
                else:
                    num_tries += 1
                    time.sleep(30)
            except Exception, e:
                num_tries += 1
                if notify:
                    fp = StringIO.StringIO()
                    traceback.print_exc(None, fp)
                    s = fp.getvalue()
                    self.notify('Service failed\n%s' % s)
                self.create_connections()
        self.notify('Service Shutting Down')
        self.shutdown()

