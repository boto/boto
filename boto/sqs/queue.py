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

"""
Represents an SQS Queue
"""

import xml.sax
import urlparse
from boto.exception import SQSError
from boto.handler import XmlHandler
from boto.sqs.message import Message
from boto.resultset import ResultSet

class Queue:
    
    def __init__(self, connection=None, url=None, message_class=Message):
        self.connection = connection
        self.url = url
        self.message_class = message_class

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'QueueUrl':
            self.url = value
            if value:
                self.id = urlparse.urlparse(value)[2]
        elif name == 'VisibilityTimeout':
            self.visibility_timeout = int(value)
        else:
            setattr(self, name, value)

    def set_message_class(self, message_class):
        self.message_class = message_class

    # get the visibility timeout for the queue
    def get_timeout(self):
        path = '%s' % self.id
        response = self.connection.make_request('GET', path)
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        handler = XmlHandler(self, self.connection)
        xml.sax.parseString(body, handler)
        return self.visibility_timeout

    # set the visibility timeout for the queue
    def set_timeout(self, visibility_timeout):
        path = '%s?VisibilityTimeout=%d' % (self.id, visibility_timeout)
        response = self.connection.make_request('PUT', path)
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        handler = XmlHandler(self, self.connection)
        xml.sax.parseString(body, handler)
        self.visibility_timeout = visibility_timeout

    # convenience method that returns a single message or None if queue is empty
    def read(self, visibility_timeout=None):
        rs = self.get_messages(1, visibility_timeout)
        if len(rs) == 1:
            return rs[0]
        else:
            return None

    # add a single message to the queue
    def write(self, message):
        path = '%s/back' % self.id
        message.queue = self
        response = self.connection.make_request('PUT', path, None,
                                                message.get_body_b64())
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        handler = XmlHandler(message, self.connection)
        xml.sax.parseString(body, handler)
        return None

    def new_message(self, body=''):
        return self.message_class(self, body)

    # get a variable number of messages, returns a list of messages
    def get_messages(self, num_messages=1, visibility_timeout=None):
        path = '%s/front?NumberOfMessages=%d' % (self.id, num_messages)
        if visibility_timeout:
            path = '%s&VisibilityTimeout=%d' % (path, visibility_timeout)
        response = self.connection.make_request('GET', path)
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        rs = ResultSet('Message', self.message_class)
        h = XmlHandler(rs, self.connection)
        xml.sax.parseString(body, h)
        return rs

    def delete_message(self, message):
        path = '%s/%s' % (self.id, message.id)
        response = self.connection.make_request('DELETE', path)
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        rs = ResultSet()
        h = XmlHandler(rs, self.connection)
        xml.sax.parseString(body, h)
        return rs

    def clear(self, page_size=100, vtimeout=10):
        """Utility function to remove all messages from a queue"""
        n = 0
        l = self.get_messages(page_size, vtimeout)
        while l:
            for m in l:
                self.delete_message(m)
                n += 1
            l = self.get_messages(page_size, vtimeout)
        return n

    def count(self, page_size=100, vtimeout=10):
        """Utility function to count the number of messages in a queue"""
        n = 0
        l = self.get_messages(page_size, vtimeout)
        while l:
            for m in l:
                n += 1
            l = self.get_messages(page_size, vtimeout)
        return n
    
    def dump(self, file_name, page_size=100, vtimeout=10, sep='\n'):
        """Utility function to dump the messages in a queue to a file"""
        fp = open(file_name, 'wb')
        n = 0
        l = self.get_messages(page_size, vtimeout)
        while l:
            for m in l:
                fp.write(m.get_body())
                if sep:
                    fp.write(sep)
                n += 1
            l = self.get_messages(page_size, vtimeout)
        fp.close()
        return n

    def save_to_s3(self, bucket):
        """
        Read all messages from the queue and persist them to S3.
        Messages are stored in the S3 bucket using a naming scheme of:
            <queue_id>/<message_id>
        """
        n = 0
        m = self.read()
        while m:
            n += 1
            key = bucket.new_key('%s/%s' % (self.id, m.id))
            key.set_contents_from_string(m.get_body())
            self.delete_message(m)
            m = self.read()
        return n

    def load_from_s3(self, bucket):
        """
        Load messages previously saved to S3.
        """
        n = 0
        prefix = '%s/' % self.id
        rs = bucket.list(prefix=prefix)
        for key in rs:
            n += 1
            m = self.new_message(key.get_contents_as_string())
            self.write(m)
        return n

    def load(self, file_name, sep='\n'):
        """Utility function to load messages from a file to a queue"""
        fp = open(file_name, 'rb')
        n = 0
        body = ''
        l = fp.readline()
        while l:
            if l == sep:
                m = Message(self, body)
                self.write(m)
                n += 1
                print 'writing message %d' % n
                body = ''
            else:
                body = body + l
            l = fp.readline()
        fp.close()
        return n
    
    
