# Copyright (c) 2012 Andy Davidoff http://www.disruptek.com/
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
from boto.exception import BotoServerError


class ResponseErrorFactory(BotoServerError):

    def __new__(cls, *args, **kw):
        error = BotoServerError(*args, **kw)
        try:
            newclass = globals()[error.error_code]
        except KeyError:
            newclass = ResponseError
        obj = newclass.__new__(newclass, *args, **kw)
        obj.__dict__.update(error.__dict__)
        return obj


class ResponseError(BotoServerError):
    """
    Undefined response error.
    """
    retry = False

    def __repr__(self):
        return '{}({}, {},\n\t{})'.format(self.__class__.__name__,
                                          self.status, self.reason,
                                          self.error_message)

    def __str__(self):
        return 'MWS Response Error: {0.status} {0.__class__.__name__} {1}\n' \
               '{2}\n' \
               '{0.error_message}'.format(self,
                                          self.retry and '(Retriable)' or '',
                                          self.__doc__.strip())


class RetriableResponseError(ResponseError):
    retry = True


class InvalidParameterValue(ResponseError):
    """
    One or more parameter values in the request is invalid.
    """


class InvalidParameter(ResponseError):
    """
    One or more parameters in the request is invalid.
    """


class InvalidAddress(ResponseError):
    """
    Invalid address.
    """
