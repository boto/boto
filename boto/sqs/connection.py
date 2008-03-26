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

from boto.connection import AWSQueryConnection
import xml.sax
from boto.sqs.queue import Queue
from boto.sqs.message import Message
from boto.sqs.attributes import Attributes
from boto import handler
from boto.resultset import ResultSet
from boto.exception import SQSError

PERM_ReceiveMessage = 'ReceiveMessage'
PERM_SendMessage = 'SendMessage'
PERM_FullControl = 'FullControl'

AllPermissions = [PERM_ReceiveMessage, PERM_SendMessage, PERM_FullControl]
                 
class SQSConnection(AWSQueryConnection):

    """
    A subclass of the original SQSQueryConnection targeting the 2008-01-01 SQS API.
    """
    
    DefaultHost = 'queue.amazonaws.com'
    APIVersion = '2008-01-01'
    SignatureVersion = '1'
    DefaultContentType = 'text/plain'
    
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=False, port=None, proxy=None, proxy_port=None,
                 host=DefaultHost, debug=0, https_connection_factory=None):
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
                                    host, debug, https_connection_factory)

    def create_queue(self, queue_name, visibility_timeout=None):
        params = {'QueueName': queue_name}
        if visibility_timeout:
            params['DefaultVisibilityTimeout'] = '%d' % (visibility_timeout,)
        response = self.make_request('CreateQueue', params, '/')
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        q = Queue(self)
        h = handler.XmlHandler(q, self)
        xml.sax.parseString(body, h)
        return q

    def delete_queue(self, queue, force_deletion=False):
        """
        Delete an SQS Queue.
        Inputs:
            queue - a Queue object representing the SQS queue to be deleted.
            force_deletion - (Optional) Normally, SQS will not delete a
                             queue that contains messages.  However, if
                             the force_deletion argument is True, the
                             queue will be deleted regardless of whether
                             there are messages in the queue or not.
                             USE WITH CAUTION.  This will delete all
                             messages in the queue as well.
        Returns:
            An empty ResultSet object.  Not sure why, actually.  It
            should probably return a Boolean indicating success or
            failure.
        """
        response = self.make_request('DeleteQueue', None, queue.id)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise SQSError(response.status, response.reason, body)

    def get_queue_attributes(self, queue_url, attribute='All'):
        params = {'AttributeName' : attribute}
        response = self.make_request('GetQueueAttributes', params, queue_url)
        body = response.read()
        if response.status == 200:
            attrs = Attributes()
            h = handler.XmlHandler(attrs, self)
            xml.sax.parseString(body, h)
            return attrs
        else:
            raise SQSError(response.status, response.reason, body)

    def set_queue_attribute(self, queue_url, attribute, value):
        params = {'Attribute.Name' : attribute, 'Attribute.Value' : value}
        response = self.make_request('SetQueueAttributes', params, queue_url)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise SQSError(response.status, response.reason, body)

    def change_message_visibility(self, queue_url, message_id, vtimeout):
        params = {'MessageId' : message_id,
                  'VisibilityTimeout' : vtimeout}
        response = self.make_request('ChangeMessageVisibility', params,
                                     queue_url)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise SQSError(response.status, response.reason, body)

    def receive_message(self, queue_url, number_messages=1,
                        visibility_timeout=None, message_class=Message):
        params = {'MaxNumberOfMessages' : number_messages}
        if visibility_timeout:
            params['VisibilityTimeout'] = visibility_timeout
        response = self.make_request('ReceiveMessage', params, queue_url)
        body = response.read()
        if response.status == 200:
            rs = ResultSet([('Message', message_class)])
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise SQSError(response.status, response.reason, body)

    def delete_message(self, queue_url, message_id, receipt_handle):
        params = {'ReceiptHandle' : receipt_handle}
        response = self.make_request('DeleteMessage', params, queue_url)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise SQSError(response.status, response.reason, body)

    def send_message(self, queue_url, message_content):
        params = {'MessageBody' : message_content}
        response = self.make_request('SendMessage', params, queue_url)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise SQSError(response.status, response.reason, body)

    def get_all_queues(self, prefix=''):
        params = {}
        if prefix:
            params['QueueNamePrefix'] = prefix
        response = self.make_request('ListQueues', params)
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        rs = ResultSet([('QueueUrl', Queue)])
        h = handler.XmlHandler(rs, self)
        xml.sax.parseString(body, h)
        return rs
        
    def get_queue(self, queue_name):
        rs = self.get_all_queues(queue_name)
        if len(rs) == 1:
            return rs[0]
        return None

