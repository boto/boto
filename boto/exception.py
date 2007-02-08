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

#
# Exception classes - Subclassing allows you to check for specific errors
#

class SQSError(Exception):
    
    def __init__(self, status, reason, body):
        self.status = status
        self.reason = reason
        self.body = body

    def __repr__(self):
        return 'SQSError: %s %s\n%s' % (self.status, self.reason, self.body)

    def __str__(self):
        return 'SQSError: %s %s\n%s' % (self.status, self.reason, self.body)

class S3Error(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __repr__(self):
        return 'S3Error: %s' % self.reason

    def __str__(self):
        return 'S3Error: %s' % self.reason

class S3ResponseError(S3Error):
    def __init__(self, status, reason):
        S3Error.__init__(self, reason)
        self.status = status
        self.reason = reason

    def __repr__(self):
        return 'S3Error[%d]: %s' % (self.status, self.reason)

    def __str__(self):
        return 'S3Error[%d]: %s' % (self.status, self.reason)

class S3TypeError(S3Error):
    pass

class S3EmptyError(S3Error):
    pass

class S3DataError(S3Error):
    pass

class S3CreateError(S3ResponseError):
    pass

class EC2ResponseError(SQSError):
    pass

class AWSAuthConnectionError(Exception):

    def __init__(self, reason):
        self.reason = reason

    def __repr__(self):
        return 'AWSAuthConnnectionError: %s' % self.reason

    def __str__(self):
        return 'AWSAuthConnnectionError: %s' % self.reason
