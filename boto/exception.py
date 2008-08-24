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
Exception classes - Subclassing allows you to check for specific errors
"""

from boto import handler
from boto.resultset import ResultSet

import xml.sax

class BotoClientError(Exception):
    """
    General Boto Client error (error accessing AWS)
    """
    
    def __init__(self, reason):
        self.reason = reason

    def __repr__(self):
        return 'S3Error: %s' % self.reason

    def __str__(self):
        return 'S3Error: %s' % self.reason

class SDBPersistenceError(Exception):

    pass

class S3PermissionsError(BotoClientError):
    """
    Permissions error when accessing a bucket or key on S3.
    """
    pass
    
class BotoServerError(Exception):
    
    def __init__(self, status, reason, body=None):
        self.status = status
        self.reason = reason
        self.body = body or ''
        self.request_id = None

        # Attempt to parse the error response. If body isn't present,
        # then just ignore the error response.
        if self.body:
            try:
                h = handler.XmlHandler(self, self)
                xml.sax.parseString(self.body, h)
            except xml.sax.SAXParseException, pe:
                # Go ahead and clean up anything that may have
                # managed to get into the error data so we
                # don't get partial garbage.
                print "Warning: failed to parse error message from AWS: %s" % pe
                self._cleanupParsedProperties()

    def __repr__(self):
        return '%s: %s %s\n%s' % (self.__class__.__name__,
                                  self.status, self.reason, self.body)

    def __str__(self):
        return '%s: %s %s\n%s' % (self.__class__.__name__,
                                  self.status, self.reason, self.body)

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name in ('RequestId', 'RequestID'):
            self.request_id = value
        return None

    def _cleanupParsedProperties(self):
        self.request_id = None


class ConsoleOutput:

    def __init__(self, parent=None):
        self.parent = parent
        self.instance_id = None
        self.timestamp = None
        self.comment = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'instanceId':
            self.instance_id = value
        elif name == 'output':
            self.output = base64.b64decode(value)
        else:
            setattr(self, name, value)

class S3CreateError(BotoServerError):
    """
    Error creating a bucket or key on S3.
    """
    pass

class S3CopyError(BotoServerError):
    """
    Error copying a key on S3.
    """
    pass

class SQSError(BotoServerError):
    """
    General Error on Simple Queue Service.
    """
    def __init__(self, status, reason, body=None):
        self.detail = None
        self.type = None
        self.code = None
        self.message = None
        BotoServerError.__init__(self, status, reason, body)

    def startElement(self, name, attrs, connection):
        return BotoServerError.startElement(self, name, attrs, connection)

    def endElement(self, name, value, connection):
        if name == 'Detail':
            self.detail = value
        elif name == 'Type':
            self.type = value
        elif name == 'Code':
            self.code = value
        elif name == 'Message':
            self.message = value
        else:
            return BotoServerError.endElement(self, name, value, connection)

    def _cleanupParsedProperties(self):
        BotoServerError._cleanupParsedProperties(self)
        for p in ('detail', 'type', 'code', 'message'):
            setattr(self, p, None)

class S3ResponseError(BotoServerError):
    """
    Error in response from S3.
    """
    def __init__(self, status, reason, body=None):
        self.resource = None
        self.code = None
        self.message = None
        BotoServerError.__init__(self, status, reason, body)

    def startElement(self, name, attrs, connection):
        return BotoServerError.startElement(self, name, attrs, connection)

    def endElement(self, name, value, connection):
        if name == 'Resource':
            self.resource = value
        elif name == 'Code':
            self.code = value
        elif name == 'Message':
            self.message = value
        else:
            return BotoServerError.endElement(self, name, value, connection)

    def _cleanupParsedProperties(self):
        BotoServerError._cleanupParsedProperties(self)
        for p in ('resource', 'code', 'message'):
            setattr(self, p, None)

class EC2ResponseError(BotoServerError):
    """
    Error in response from EC2.
    """

    def __init__(self, status, reason, body=None):
        self.code = None
        self.message = None
        self.errors = None
        self._errorResultSet = []
        BotoServerError.__init__(self, status, reason, body)
        self.errors = [ (e.code, e.message) \
                for e in self._errorResultSet ]
        if len(self.errors):
            self.code, self.message = self.errors[0]

    def startElement(self, name, attrs, connection):
        if name == 'Errors':
            self._errorResultSet = ResultSet([('Error', _EC2Error)])
            return self._errorResultSet
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'RequestID':
            self.request_id = value
        else:
            return None # don't call subclass here

    def _cleanupParsedProperties(self):
        BotoServerError._cleanupParsedProperties(self)
        self._errorResultSet = []
        for p in ('errors', 'code', 'message'):
            setattr(self, p, None)

class _EC2Error:

    def __init__(self, connection=None):
        self.connection = connection
        self.code = None
        self.message = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'Code':
            self.code = value
        elif name == 'Message':
            self.message = value
        else:
            return None

class SDBResponseError(BotoServerError):
    """
    Error in respones from SDB.
    """
    pass

class AWSConnectionError(BotoClientError):
    """
    General error connecting to Amazon Web Services.
    """
    pass

class S3DataError(BotoClientError):
    """
    Error receiving data from S3.
    """ 
    pass

class FPSResponseError(BotoServerError):
    pass
