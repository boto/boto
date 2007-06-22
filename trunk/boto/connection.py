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

"""
Handles basic connections to AWS
"""

import base64
import hmac
import httplib
import socket
import re
import sha
import sys
import time
import urllib
import os
import xml.sax
from boto.exception import AWSConnectionError
import boto.utils

PORTS_BY_SECURITY = { True: 443, False: 80 }

class AWSAuthConnection:
    def __init__(self, server, aws_access_key_id=None,
                 aws_secret_access_key=None, is_secure=True, port=None,
                 proxy=None, proxy_port=None, debug=False,
                 https_connection_factory=None):
        self.is_secure = is_secure
        self.http_exceptions = (httplib.HTTPException, socket.error)
        if https_connection_factory is not None:
            self.https_connection_factory = https_connection_factory[0]
            self.http_exceptions += https_connection_factory[1]
        else:
            self.https_connection_factory = None
        if (is_secure):
            self.protocol = 'https'
        else:
            self.protocol = 'http'
        self.server = server
        self.debug = debug
        if not port:
            port = PORTS_BY_SECURITY[is_secure]
        self.port = port
        self.server_name = '%s:%d' % (server, port)
        
        if aws_access_key_id:
            self.aws_access_key_id = aws_access_key_id
        else:
            if os.environ.has_key('AWS_ACCESS_KEY_ID'):
                self.aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']
        
        if aws_secret_access_key:
            self.aws_secret_access_key = aws_secret_access_key
        else:
            if os.environ.has_key('AWS_SECRET_ACCESS_KEY'):
                self.aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
        
        self.proxy = proxy
        #This lowercase environment var is the same as used in urllib
        if os.environ.has_key('http_proxy'): 
            self.proxy = os.environ['http_proxy'].split(':')
            self.proxy = proxy_port_pair[0]
            
        self.use_proxy = (self.proxy != None)
        if (self.use_proxy and self.is_secure):
            raise AWSConnectionError("Unable to provide secure connection through proxy")
        
        if proxy_port:
            self.proxy_port = proxy_port
        else:
            if os.environ.has_key('http_proxy'):
                self.proxy_port = os.environ['http_proxy'].split(':')[1]
                if len(proxy_port_pair) != 2:
                    print "http_proxy env var does not specify port, using default"
                    self.proxy_port = self.port
                else:
                    self.proxy_port = os.environ['http_proxy'].split(':')[1]
            else:
                self.proxy_port = None
        
        self.make_http_connection()
        self._last_rs = None

    def make_http_connection(self):
        if (self.use_proxy):
            cnxn_point = self.proxy
            cnxn_port = int(self.proxy_port)
        else:
            cnxn_point = self.server
            cnxn_port = self.port
        if self.debug:
            print 'establishing HTTP connection'
        if (self.is_secure):
            if self.https_connection_factory:
                self.connection = self.https_connection_factory("%s:%d" % (cnxn_point, cnxn_port))
            else:
                self.connection = httplib.HTTPSConnection("%s:%d" % (cnxn_point,
                                                                     cnxn_port))
        else:
            self.connection = httplib.HTTPConnection("%s:%d" % (cnxn_point,
                                                                cnxn_port))
        self.set_debug(self.debug)

    def set_debug(self, debug=0):
        self.debug = debug
        self.connection.set_debuglevel(debug)

    def prefix_proxy_to_path(self, path):
        path = self.protocol + '://' + self.server + path
        return path
        
    def make_request(self, method, path, headers=None, data='', metadata=None):
        if headers == None:
            headers = {}
        if metadata == None:
            metadata = {}
        if not headers.has_key('Content-Length'):
            headers['Content-Length'] = len(data)
        final_headers = boto.utils.merge_meta(headers, metadata);
        # add auth header
        self.add_aws_auth_header(final_headers, method, path)
        if self.use_proxy:
            path = self.prefix_proxy_to_path(path)
        try:
            self.connection.request(method, path, data, final_headers)
            return self.connection.getresponse()
        except self.http_exceptions, e:
            if self.debug:
                print 'encountered %s exception, trying to recover' % \
                    e.__class__.__name__
            self.make_http_connection()
            self.connection.request(method, path, data, final_headers)
            return self.connection.getresponse()

    def add_aws_auth_header(self, headers, method, path):
        if not headers.has_key('Date'):
            headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT",
                                            time.gmtime())
        
        c_string = boto.utils.canonical_string(method, path, headers)
        if self.debug:
            print '\n\n%s\n\n' % c_string
        headers['Authorization'] = \
            "AWS %s:%s" % (self.aws_access_key_id,
                           boto.utils.encode(self.aws_secret_access_key,
                                             c_string))

class AWSQueryConnection(AWSAuthConnection):

    APIVersion = ''
    SignatureVersion = '1'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 host=None, debug=0, https_connection_factory=None):
        AWSAuthConnection.__init__(self, host,
                                   aws_access_key_id, aws_secret_access_key,
                                   is_secure, port, proxy, proxy_port, debug,
                                   https_connection_factory)

    def make_request(self, action, params=None, path=None, verb='GET'):
        if path == None:
            path = '/'
        if params == None:
            params = {}
        h = hmac.new(key=self.aws_secret_access_key, digestmod=sha)
        params['Action'] = action
        params['Version'] = self.APIVersion
        params['AWSAccessKeyId'] = self.aws_access_key_id
        params['SignatureVersion'] = self.SignatureVersion
        params['Timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        keys = params.keys()
        keys.sort(cmp = lambda x, y: cmp(x.lower(), y.lower()))
        qs = ''
        for key in keys:
            h.update(key)
            h.update(str(params[key]))
            qs += key + '=' + urllib.quote(str(params[key])) + '&'
        signature = base64.b64encode(h.digest())
        qs = path + '?' + qs + 'Signature=' + urllib.quote(signature)
        
        if self.use_proxy:
            qs = self.prefix_proxy_to_path(qs)
        
        try:
            self.connection.request(verb, qs)
            return self.connection.getresponse()
        except self.http_exceptions, e:
            if self.debug:
                print 'encountered %s exception, trying to recover' % \
                    e.__class__.__name__
            self.make_http_connection()
            self.connection.request('GET', qs)
            return self.connection.getresponse()

    def build_list_params(self, params, items, label):
        for i in range(1, len(items)+1):
            params['%s.%d' % (label, i)] = items[i-1]


