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
Represents an SQS Message
"""

import base64
import StringIO

class RawMessage:
    """
    Base class for SQS messages.  RawMessage does not encode the message
    in any way.  Whatever you store in the body of the message is what
    will be written to SQS and whatever is returned from SQS is stored
    directly into the body of the message.
    """
    
    def __init__(self, queue=None, body=''):
        self.queue = queue
        self._raw_body = ''
        self._decoded_body = None
        self.set_body(body)
        self.id = None
        self.receipt_handle = None

    def __len__(self):
        return len(self._raw_body)

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        # Support both the 2007 and 2008 SQS APIs.
        if name == 'MessageBody' or name == 'Body':
            self._raw_body = value
            self._decoded_body = self._decode(self._raw_body)
        elif name == 'MessageId':
            self.id = value
        elif name == 'ReceiptHandle':
            self.receipt_handle = value
        else:
            setattr(self, name, value)

    def _encode(self, body):
        """Transform body object into serialized byte array format."""
        return body

    def _decode(self, body):
        """Transform seralized byte array into any object."""
        return body
 
    def set_body(self, body):
        """Override the current body for this object, using decoded format."""
        self._decoded_body = body
        self._raw_body = self._encode(body)

    def get_body(self):
        return self._decoded_body
    
    def get_body_encoded(self):
        """
        This method is really a semi-private method used by the Queue.write
        method when writing the contents of the message to SQS.  The
        RawMessage class does not encode the message in any way so this
        just calls get_body().  You probably shouldn't need to call this
        method in the normal course of events.
        """
        return self._raw_body
    
    def change_visibility(self, vtimeout):
        """
        Convenience function to allow you to directly change the
        invisibility timeout for an individual message that has been
        read from an SQS queue.  This won't affect the default visibility
        timeout of the queue.
        """
        return self.queue.connection.change_message_visibility(self.queue.id,
                                                               self.id,
                                                               vtimeout)
class Message(RawMessage):
    """
    The default Message class used for SQS queues.  This class automatically
    encodes/decodes the message body using Base64 encoding to avoid any
    illegal characters in the message body.  See:

    http://developer.amazonwebservices.com/connect/thread.jspa?messageID=49680%EC%88%90

    for details on why this is a good idea.  The encode/decode is meant to
    be transparent to the end-user.
    """
    
    def encode(self, value):
        return base64.b64encode(value)

    def decode(self, value):
        return base64.b64decode(value)

class MHMessage(Message):
    """
    The MHMessage class provides a message that provides RFC821-like
    headers like this:

    HeaderName: HeaderValue

    The encoding/decoding of this is handled automatically and after
    the message body has been read, the message instance can be treated
    like a mapping object, i.e. m['HeaderName'] would return 'HeaderValue'.
    """

    def __init__(self, queue=None, body={}, xml_attrs=None):
        Message.__init__(self, queue, body)

    def decode(self, body):
        msg = {}
        fp = StringIO.StringIO(body)
        line = fp.readline()
        while line:
            delim = line.find(':')
            key = line[0:delim]
            value = line[delim+1:].strip()
            msg[key.strip()] = value.strip()
            line = fp.readline()
        return msg

    def encode(self):
        s = ''
        for key,value in self._dict.items():
            s = s + '%s: %s\n' % (key, value)
        return s

    def __len__(self):
        return len(self._decoded_body)

    def __getitem__(self, key):
        if self._decoded_body.has_key(key):
            return self._decoded_body[key]
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        self._decoded_body[key] = value
        self.set_body(self._decoded_body)

    def keys(self):
        return self._decoded_body.keys()

    def values(self):
        return self._decoded_body.values()

    def items(self):
        return self._decoded_body.items()

    def has_key(self, key):
        return self._decoded_body.has_key(key)

    def update(self, d):
        self._decoded_body.update(d)
        self.set_body(self._decoded_body)

    def get(self, key, default=None):
        return self._decoded_body.get(key, default)
