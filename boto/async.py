# Copyright (c) 2010 Reza Lotun http://reza.lotun.name/
# All rights reserved.
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
# Parts of this code were copied or derived from sample code supplied by AWS.
# The following notice applies to that code.
#
#  This software code is made available "AS IS" without warranties of any
#  kind.  You may copy, display, modify and redistribute the software
#  code either by itself or as incorporated into your code; provided that
#  you do not remove any proprietary notices.  Your use of this software
#  code is at your own risk and you waive any claim against Amazon
#  Digital Services, Inc. or its affiliates with respect to your use of
#  this software code. (c) 2006 Amazon Digital Services, Inc. or its
#  affiliates.

from twisted.python import log, failure
from twisted.internet import defer
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent, ResponseDone, _parse
from twisted.web.http_headers import Headers


class Response(object):
    """ Mimic HTTP response object. """
    def __init__(self, data=None, status=None, reason=None):
        self.data = data
        self.status = status
        self.reason = reason

    def read(self):
        return self.data


class ResponseReceiver(Protocol):
    """ A very simple protocol which accumulates sent data in a buffer and fires
    a deferred with this result when the connection closes.
    """
    def __init__(self, deferred, response_obj):
        self.buffer = []
        self.response_obj = response_obj
        self.finished = deferred

    def dataReceived(self, data):
        self.buffer.append(data)

    def connectionLost(self, reason):
        # package up the data we've received so far
        body_so_far = ''.join(self.buffer)

        r = Response(data=body_so_far, status=self.response_obj.code)

        if reason.check(ResponseDone):
            # response has been cleanly received
            self.finished.callback(r)
        elif reason.check(PotentialDataLoss):
            # got data back, but don't know if it's everything we wanted
            self.finished.callback(r)
        else:
            self.finished.errback(reason)


_reactor = None
class AsyncHTTP(object):

    @classmethod
    def make_request(cls, method, path, data, headers, host, sender):

        # get a reference to the reactor and cache it
        global _reactor
        if not _reactor:
            from twisted.internet import reactor
            _reactor = reactor

        agent = Agent(_reactor)

        # form our headers
        hdrs = Headers()
        for k, v in headers.iteritems():
            if isinstance(v, list):
                for i in v:
                    hdrs.addRawHeader(k, i)
            else:
                hdrs.addRawHeader(k, v)

        kwargs = dict(method=method, uri='%s%s' % (host, path), headers=hdrs)


        d = agent.request(**kwargs)

        def handle_connection(response):
            if 200 <= response.code < 300:
                d = defer.Deferred()
                proto = ResponseReceiver(d, response)
                response.deliverBody(proto)
                return d
            else:
                # XXX: for now we'll just errback
                return defer.fail(response)

        d.addCallback(handle_connection)
        return d

