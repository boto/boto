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

class BotoClientError(Exception):
    
    def __init__(self, reason):
        self.reason = reason

    def __repr__(self):
        return 'S3Error: %s' % self.reason

    def __str__(self):
        return 'S3Error: %s' % self.reason

class SDBPersistanceError(Exception):

    pass

class S3PermissionsError(BotoClientError):

    pass
    
class BotoServerError(Exception):
    
    def __init__(self, status, reason, body=''):
        self.status = status
        self.reason = reason
        self.body = body

    def __repr__(self):
        return '%s: %s %s\n%s' % (self.__class__.__name__,
                                  self.status, self.reason, self.body)

    def __str__(self):
        return '%s: %s %s\n%s' % (self.__class__.__name__,
                                  self.status, self.reason, self.body)

class S3CreateError(BotoServerError):
    pass

class SQSError(BotoServerError):
    pass
    
class S3ResponseError(BotoServerError):
    pass

class EC2ResponseError(BotoServerError):
    pass

class SDBResponseError(BotoServerError):
    pass

class AWSConnectionError(BotoClientError):
    pass

class S3DataError(BotoClientError):
    pass

class FPSResponseError(BotoServerError):
    pass
