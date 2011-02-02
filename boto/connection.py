# Copyright (c) 2006-2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010 Google
# Copyright (c) 2008 rPath, Inc.
# Copyright (c) 2009 The Echo Nest Corporation
# Copyright (c) 2010, Eucalyptus Systems, Inc.
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

"""
Handles basic connections to AWS
"""

import base64
import errno
import httplib
import os
import Queue
import re
import socket
import sys
import time
import urllib, urlparse
import xml.sax

import auth
import auth_handler
import boto
import boto.utils

from boto import config, UserAgent, handler
from boto.exception import AWSConnectionError, BotoClientError, BotoServerError
from boto.provider import Provider
from boto.resultset import ResultSet


PORTS_BY_SECURITY = { True: 443, False: 80 }

class ConnectionPool:
    def __init__(self, hosts, connections_per_host):
        self._hosts = boto.utils.LRUCache(hosts)
        self.connections_per_host = connections_per_host

    def __getitem__(self, key):
        if key not in self._hosts:
            self._hosts[key] = Queue.Queue(self.connections_per_host)
        return self._hosts[key]

    def __repr__(self):
        return 'ConnectionPool:%s' % ','.join(self._hosts._dict.keys())

class HTTPRequest(object):

    def __init__(self, method, protocol, host, port, path, auth_path,
                 params, headers, body):
        """Represents an HTTP request.

        :type method: string
        :param method: The HTTP method name, 'GET', 'POST', 'PUT' etc.

        :type protocol: string
        :param protocol: The http protocol used, 'http' or 'https'. 

        :type host: string
        :param host: Host to which the request is addressed. eg. abc.com

        :type port: int
        :param port: port on which the request is being sent. Zero means unset,
                     in which case default port will be chosen.

        :type path: string 
        :param path: URL path that is bein accessed.

        :type auth_path: string 
        :param path: The part of the URL path used when creating the
                     authentication string.

        :type params: dict
        :param params: HTTP url query parameters, with key as name of the param,
                       and value as value of param.

        :type headers: dict
        :param headers: HTTP headers, with key as name of the header and value
                        as value of header.

        :type body: string
        :param body: Body of the HTTP request. If not present, will be None or
                     empty string ('').
        """
        self.method = method
        self.protocol = protocol
        self.host = host 
        self.port = port
        self.path = path
        self.auth_path = auth_path
        self.params = params
        self.headers = headers
        self.body = body

    def __str__(self):
        return (('method:(%s) protocol:(%s) host(%s) port(%s) path(%s) '
                 'params(%s) headers(%s) body(%s)') % (self.method,
                 self.protocol, self.host, self.port, self.path, self.params,
                 self.headers, self.body))

class AWSAuthConnection(object):
    def __init__(self, host, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, path='/', provider='aws'):
        """
        :type host: str
        :param host: The host to make the connection to
       
        :keyword str aws_access_key_id: Your AWS Access Key ID (provided by
            Amazon). If none is specified, the value in your 
            ``AWS_ACCESS_KEY_ID`` environmental variable is used.
        :keyword str aws_secret_access_key: Your AWS Secret Access Key 
            (provided by Amazon). If none is specified, the value in your 
            ``AWS_SECRET_ACCESS_KEY`` environmental variable is used.

        :type is_secure: boolean
        :param is_secure: Whether the connection is over SSL

        :type https_connection_factory: list or tuple
        :param https_connection_factory: A pair of an HTTP connection
                                         factory and the exceptions to catch.
                                         The factory should have a similar
                                         interface to L{httplib.HTTPSConnection}.

        :param str proxy: Address/hostname for a proxy server

        :type proxy_port: int
        :param proxy_port: The port to use when connecting over a proxy

        :type proxy_user: str
        :param proxy_user: The username to connect with on the proxy

        :type proxy_pass: str
        :param proxy_pass: The password to use when connection over a proxy.

        :type port: int
        :param port: The port to use to connect
        """
        self.num_retries = 5
        # Override passed-in is_secure setting if value was defined in config.
        if config.has_option('Boto', 'is_secure'):
            is_secure = config.getboolean('Boto', 'is_secure')
        self.is_secure = is_secure
        self.handle_proxy(proxy, proxy_port, proxy_user, proxy_pass)
        # define exceptions from httplib that we want to catch and retry
        self.http_exceptions = (httplib.HTTPException, socket.error,
                                socket.gaierror)
        # define values in socket exceptions we don't want to catch
        self.socket_exception_values = (errno.EINTR,)
        if https_connection_factory is not None:
            self.https_connection_factory = https_connection_factory[0]
            self.http_exceptions += https_connection_factory[1]
        else:
            self.https_connection_factory = None
        if (is_secure):
            self.protocol = 'https'
        else:
            self.protocol = 'http'
        self.host = host
        self.path = path
        if debug:
            self.debug = debug
        else:
            self.debug = config.getint('Boto', 'debug', debug)
        if port:
            self.port = port
        else:
            self.port = PORTS_BY_SECURITY[is_secure]

        self.provider = Provider(provider,
                                 aws_access_key_id,
                                 aws_secret_access_key)

        # allow config file to override default host
        if self.provider.host:
            self.host = self.provider.host

        # cache up to 20 connections per host, up to 20 hosts
        self._pool = ConnectionPool(20, 20)
        self._connection = (self.server_name(), self.is_secure)
        self._last_rs = None
        self._auth_handler = auth.get_auth_handler(
              host, config, self.provider, self._required_auth_capability()) 

    def __repr__(self):
        return '%s:%s' % (self.__class__.__name__, self.host)

    def _required_auth_capability(self):
        return []

    def _cached_name(self, host, is_secure):
        if host is None:
            host = self.server_name()
        cached_name = is_secure and 'https://' or 'http://'
        cached_name += host
        return cached_name

    def connection(self):
        return self.get_http_connection(*self._connection)
    connection = property(connection)

    def aws_access_key_id(self):
        return self.provider.access_key
    aws_access_key_id = property(aws_access_key_id)
    gs_access_key_id = aws_access_key_id
    access_key = aws_access_key_id

    def aws_secret_access_key(self):
        return self.provider.secret_key
    aws_secret_access_key = property(aws_secret_access_key)
    gs_secret_access_key = aws_secret_access_key
    secret_key = aws_secret_access_key

    def get_path(self, path='/'):
        pos = path.find('?')
        if pos >= 0:
            params = path[pos:]
            path = path[:pos]
        else:
            params = None
        if path[-1] == '/':
            need_trailing = True
        else:
            need_trailing = False
        path_elements = self.path.split('/')
        path_elements.extend(path.split('/'))
        path_elements = [p for p in path_elements if p]
        path = '/' + '/'.join(path_elements)
        if path[-1] != '/' and need_trailing:
            path += '/'
        if params:
            path = path + params
        return path

    def server_name(self, port=None):
        if not port:
            port = self.port
        if port == 80:
            signature_host = self.host
        else:
            # This unfortunate little hack can be attributed to
            # a difference in the 2.6 version of httplib.  In old
            # versions, it would append ":443" to the hostname sent
            # in the Host header and so we needed to make sure we
            # did the same when calculating the V2 signature.  In 2.6
            # (and higher!)
            # it no longer does that.  Hence, this kludge.
            if sys.version[:3] in ('2.6', '2.7') and port == 443:
                signature_host = self.host
            else:
                signature_host = '%s:%d' % (self.host, port)
        return signature_host

    def handle_proxy(self, proxy, proxy_port, proxy_user, proxy_pass):
        self.proxy = proxy
        self.proxy_port = proxy_port
        self.proxy_user = proxy_user
        self.proxy_pass = proxy_pass
        if os.environ.has_key('http_proxy') and not self.proxy:
            pattern = re.compile(
                '(?:http://)?' \
                '(?:(?P<user>\w+):(?P<pass>.*)@)?' \
                '(?P<host>[\w\-\.]+)' \
                '(?::(?P<port>\d+))?'
            )
            match = pattern.match(os.environ['http_proxy'])
            if match:
                self.proxy = match.group('host')
                self.proxy_port = match.group('port')
                self.proxy_user = match.group('user')
                self.proxy_pass = match.group('pass')
        else:
            if not self.proxy:
                self.proxy = config.get_value('Boto', 'proxy', None)
            if not self.proxy_port:
                self.proxy_port = config.get_value('Boto', 'proxy_port', None)
            if not self.proxy_user:
                self.proxy_user = config.get_value('Boto', 'proxy_user', None)
            if not self.proxy_pass:
                self.proxy_pass = config.get_value('Boto', 'proxy_pass', None)

        if not self.proxy_port and self.proxy:
            print "http_proxy environment variable does not specify " \
                "a port, using default"
            self.proxy_port = self.port
        self.use_proxy = (self.proxy != None)

    def get_http_connection(self, host, is_secure):
        queue = self._pool[self._cached_name(host, is_secure)]
        try:
            return queue.get_nowait()
        except Queue.Empty:
            return self.new_http_connection(host, is_secure)

    def new_http_connection(self, host, is_secure):
        if self.use_proxy:
            host = '%s:%d' % (self.proxy, int(self.proxy_port))
        if host is None:
            host = self.server_name()
        if is_secure:
            boto.log.debug('establishing HTTPS connection')
            if self.use_proxy:
                connection = self.proxy_ssl()
            elif self.https_connection_factory:
                connection = self.https_connection_factory(host)
            else:
                connection = httplib.HTTPSConnection(host)
        else:
            boto.log.debug('establishing HTTP connection')
            connection = httplib.HTTPConnection(host)
        if self.debug > 1:
            connection.set_debuglevel(self.debug)
        # self.connection must be maintained for backwards-compatibility
        # however, it must be dynamically pulled from the connection pool
        # set a private variable which will enable that
        if host.split(':')[0] == self.host and is_secure == self.is_secure:
            self._connection = (host, is_secure)
        return connection

    def put_http_connection(self, host, is_secure, connection):
        try:
            self._pool[self._cached_name(host, is_secure)].put_nowait(connection)
        except Queue.Full:
            # gracefully fail in case of pool overflow
            connection.close()

    def proxy_ssl(self):
        host = '%s:%d' % (self.host, self.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.proxy, int(self.proxy_port)))
        except:
            raise
        sock.sendall("CONNECT %s HTTP/1.0\r\n" % host)
        sock.sendall("User-Agent: %s\r\n" % UserAgent)
        if self.proxy_user and self.proxy_pass:
            for k, v in self.get_proxy_auth_header().items():
                sock.sendall("%s: %s\r\n" % (k, v))
        sock.sendall("\r\n")
        resp = httplib.HTTPResponse(sock, strict=True)
        resp.begin()

        if resp.status != 200:
            # Fake a socket error, use a code that make it obvious it hasn't
            # been generated by the socket library
            raise socket.error(-71,
                               "Error talking to HTTP proxy %s:%s: %s (%s)" %
                               (self.proxy, self.proxy_port, resp.status, resp.reason))

        # We can safely close the response, it duped the original socket
        resp.close()

        h = httplib.HTTPConnection(host)

        # Wrap the socket in an SSL socket
        if hasattr(httplib, 'ssl'):
            sslSock = httplib.ssl.SSLSocket(sock)
        else: # Old Python, no ssl module
            sslSock = socket.ssl(sock, None, None)
            sslSock = httplib.FakeSocket(sock, sslSock)
        # This is a bit unclean
        h.sock = sslSock
        return h

    def prefix_proxy_to_path(self, path, host=None):
        path = self.protocol + '://' + (host or self.server_name()) + path
        return path

    def get_proxy_auth_header(self):
        auth = base64.encodestring(self.proxy_user + ':' + self.proxy_pass)
        return {'Proxy-Authorization': 'Basic %s' % auth}

    def _mexe(self, method, path, data, headers, host=None, sender=None,
              override_num_retries=None):
        """
        mexe - Multi-execute inside a loop, retrying multiple times to handle
               transient Internet errors by simply trying again.
               Also handles redirects.

        This code was inspired by the S3Utils classes posted to the boto-users
        Google group by Larry Bates.  Thanks!
        """
        boto.log.debug('Method: %s' % method)
        boto.log.debug('Path: %s' % path)
        boto.log.debug('Data: %s' % data)
        boto.log.debug('Headers: %s' % headers)
        boto.log.debug('Host: %s' % host)
        response = None
        body = None
        e = None
        if override_num_retries is None:
            num_retries = config.getint('Boto', 'num_retries', self.num_retries)
        else:
            num_retries = override_num_retries
        i = 0
        connection = self.get_http_connection(host, self.is_secure)
        while i <= num_retries:
            try:
                if callable(sender):
                    response = sender(connection, method, path, data, headers)
                else:
                    connection.request(method, path, data, headers)
                    response = connection.getresponse()
                location = response.getheader('location')
                # -- gross hack --
                # httplib gets confused with chunked responses to HEAD requests
                # so I have to fake it out
                if method == 'HEAD' and getattr(response, 'chunked', False):
                    response.chunked = 0
                if response.status == 500 or response.status == 503:
                    boto.log.debug('received %d response, retrying in %d seconds' % (response.status, 2 ** i))
                    body = response.read()
                elif response.status == 408:
                    body = response.read()
                    print '-------------------------'
                    print '         4 0 8           '
                    print 'path=%s' % path
                    print body
                    print '-------------------------'
                elif response.status < 300 or response.status >= 400 or \
                        not location:
                    self.put_http_connection(host, self.is_secure, connection)
                    return response
                else:
                    scheme, host, path, params, query, fragment = \
                            urlparse.urlparse(location)
                    if query:
                        path += '?' + query
                    boto.log.debug('Redirecting: %s' % scheme + '://' + host + path)
                    connection = self.get_http_connection(host, scheme == 'https')
                    continue
            except KeyboardInterrupt:
                sys.exit('Keyboard Interrupt')
            except self.http_exceptions, e:
                boto.log.debug('encountered %s exception, reconnecting' % \
                                  e.__class__.__name__)
                connection = self.new_http_connection(host, self.is_secure)
            time.sleep(2 ** i)
            i += 1
        # If we made it here, it's because we have exhausted our retries and stil haven't
        # succeeded.  So, if we have a response object, use it to raise an exception.
        # Otherwise, raise the exception that must have already happened.
        if response:
            raise BotoServerError(response.status, response.reason, body)
        elif e:
            raise e
        else:
            raise BotoClientError('Please report this exception as a Boto Issue!')

    def build_base_http_request(self, method, path, auth_path,
                                params=None, headers=None, data='', host=None):
        path = self.get_path(path)
        if auth_path is not None:
            auth_path = self.get_path(auth_path)
        if params == None:
            params = {}
        else:
            params = params.copy()
        if headers == None:
            headers = {}
        else:
            headers = headers.copy()
        host = host or self.host
        if self.use_proxy:
            path = self.prefix_proxy_to_path(path, host)
            if self.proxy_user and self.proxy_pass and not self.is_secure:
                # If is_secure, we don't have to set the proxy authentication
                # header here, we did that in the CONNECT to the proxy.
                headers.update(self.get_proxy_auth_header())
        return HTTPRequest(method, self.protocol, host, self.port,
                           path, auth_path, params, headers, data)

    def fill_in_auth(self, http_request, **kwargs):
        headers = http_request.headers
        for key in headers:
            val = headers[key]
            if isinstance(val, unicode):
                headers[key] = urllib.quote_plus(val.encode('utf-8'))

        self._auth_handler.add_auth(http_request, **kwargs)

        headers['User-Agent'] = UserAgent
        if not headers.has_key('Content-Length'):
            headers['Content-Length'] = str(len(http_request.body))
        return http_request

    def _send_http_request(self, http_request, sender=None,
                           override_num_retries=None):
        return self._mexe(http_request.method, http_request.path,
                          http_request.body, http_request.headers,
                          http_request.host, sender, override_num_retries)

    def make_request(self, method, path, headers=None, data='', host=None,
                     auth_path=None, sender=None, override_num_retries=None):
        """Makes a request to the server, with stock multiple-retry logic."""
        http_request = self.build_base_http_request(method, path, auth_path,
                                                    {}, headers, data, host)
        http_request = self.fill_in_auth(http_request)
        return self._send_http_request(http_request, sender,
                                       override_num_retries)

    def close(self):
        """(Optional) Close any open HTTP connections.  This is non-destructive,
        and making a new request will open a connection again."""

        boto.log.debug('closing all HTTP connections')
        self.connection = None  # compat field

class AWSQueryConnection(AWSAuthConnection):

    APIVersion = ''
    ResponseError = BotoServerError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, host=None, debug=0,
                 https_connection_factory=None, path='/'):
        AWSAuthConnection.__init__(self, host, aws_access_key_id, aws_secret_access_key,
                                   is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                                   debug, https_connection_factory, path)

    def _required_auth_capability(self):
        return []

    def get_utf8_value(self, value):
        return boto.utils.get_utf8_value(value)

    def make_request(self, action, params=None, path='/', verb='GET'):
        http_request = self.build_base_http_request(verb, path, None,
                                                    params, {}, '',
                                                    self.server_name())
        http_request.params['Action'] = action
        http_request.params['Version'] = self.APIVersion
        http_request = self.fill_in_auth(http_request)
        return self._send_http_request(http_request)

    def build_list_params(self, params, items, label):
        if isinstance(items, str):
            items = [items]
        for i in range(1, len(items) + 1):
            params['%s.%d' % (label, i)] = items[i - 1]

    # generics

    def get_list(self, action, params, markers, path='/', parent=None, verb='GET'):
        if not parent:
            parent = self
        response = self.make_request(action, params, path, verb)
        body = response.read()
        boto.log.debug(body)
        if response.status == 200:
            rs = ResultSet(markers)
            h = handler.XmlHandler(rs, parent)
            xml.sax.parseString(body, h)
            return rs
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)

    def get_object(self, action, params, cls, path='/', parent=None, verb='GET'):
        if not parent:
            parent = self
        response = self.make_request(action, params, path, verb)
        body = response.read()
        boto.log.debug(body)
        if response.status == 200:
            obj = cls(parent)
            h = handler.XmlHandler(obj, parent)
            xml.sax.parseString(body, h)
            return obj
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)

    def get_status(self, action, params, path='/', parent=None, verb='GET'):
        if not parent:
            parent = self
        response = self.make_request(action, params, path, verb)
        body = response.read()
        boto.log.debug(body)
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, parent)
            xml.sax.parseString(body, h)
            return rs.status
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)
