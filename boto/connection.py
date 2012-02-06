# Copyright (c) 2006-2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010 Google
# Copyright (c) 2008 rPath, Inc.
# Copyright (c) 2009 The Echo Nest Corporation
# Copyright (c) 2010, Eucalyptus Systems, Inc.
# Copyright (c) 2011, Nexenta Systems Inc.
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

from __future__ import with_statement
import errno
import httplib
import os
import Queue
import random
import re
import socket
import sys
import time
import urlparse
import xml.sax

import requests

import auth
import auth_handler
import boto
import boto.utils
import boto.handler
import boto.cacerts

from boto import config, UserAgent
from boto.exception import AWSConnectionError, BotoClientError, BotoServerError
from boto.provider import Provider
from boto.resultset import ResultSet

HAVE_HTTPS_CONNECTION = False
try:
    import ssl
    from boto import https_connection
    # Google App Engine runs on Python 2.5 so doesn't have ssl.SSLError.
    if hasattr(ssl, 'SSLError'):
        HAVE_HTTPS_CONNECTION = True
except ImportError:
    pass

# This is an ugly hack to bring over the sillyness that is HTTPResponse.reason.
# TODO: Try to get this from somewhere else? Can we pluck straight from
# httplib? Didn't have time to source dive.
HTTP_REASON_CODES = {
    "100": "Continue",
    "101": "Switching Protocols",
    "200": "OK",
    "201": "Created",
    "202": "Accepted",
    "203": "Non-Authoritative Information",
    "204": "No Content",
    "205": "Reset Content",
    "206": "Partial Content",
    "300": "Multiple Choices",
    "301": "Moved Permanently",
    "302": "Found",
    "303": "See Other",
    "304": "Not Modified",
    "305": "Use Proxy",
    "307": "Temporary Redirect",
    "400": "Bad Request",
    "401": "Unauthorized",
    "402": "Payment Required",
    "403": "Forbidden",
    "404": "Not Found",
    "405": "Method Not Allowed",
    "406": "Not Acceptable",
    "407": "Proxy Authentication Required",
    "408": "Request Time-out",
    "409": "Conflict",
    "410": "Gone",
    "411": "Length Required",
    "412": "Precondition Failed",
    "413": "Request Entity Too Large",
    "414": "Request-URI Too Large",
    "415": "Unsupported Media Type",
    "416": "Requested range not satisfiable",
    "417": "Expectation Failed",
    "500": "Internal Server Error",
    "501": "Not Implemented",
    "502": "Bad Gateway",
    "503": "Service Unavailable",
    "504": "Gateway Time-out",
    "505": "HTTP Version not supported",
}

ON_APP_ENGINE = all(key in os.environ for key in (
    'USER_IS_ADMIN', 'CURRENT_VERSION_ID', 'APPLICATION_ID'))

PORTS_BY_SECURITY = { True: 443, False: 80 }

DEFAULT_CA_CERTS_FILE = os.path.join(
        os.path.dirname(os.path.abspath(boto.cacerts.__file__ )), "cacerts.txt")

class HTTPRequest(object):
    """
    A data encapsulation class used for passing values to our HTTP client.
    This is currently the 'requests' library.
    """

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
        :param path: URL path that is being accessed.

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
        self.auth_path = auth_path or path
        self.params = params
        self.body = body

        # chunked Transfer-Encoding should act only on PUT request.
        if headers and 'Transfer-Encoding' in headers and \
           headers['Transfer-Encoding'] == 'chunked' and \
           self.method != 'PUT':
            self.headers = headers.copy()
            del self.headers['Transfer-Encoding']
        else:
            self.headers = headers

    def __str__(self):
        return (('method:(%s) protocol:(%s) host(%s) port(%s) path(%s) '
                 'params(%s) headers(%s) body(%s)') % (
            self.method, self.protocol, self.host, self.port, self.path,
            self.params, self.headers, self.body))

    def authorize(self, connection, **kwargs):
        connection._auth_handler.add_auth(self, **kwargs)

        self.headers['User-Agent'] = UserAgent
        # I'm not sure if this is still needed, now that add_auth is
        # setting the content-length for POST requests.
        if not self.headers.has_key('Content-Length'):
            if not self.headers.has_key('Transfer-Encoding') or \
                    self.headers['Transfer-Encoding'] != 'chunked':
                self.headers['Content-Length'] = str(len(self.body))

class AWSAuthConnection(object):
    def __init__(self, host, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, path='/',
                 provider='aws', security_token=None,
                 suppress_consec_slashes=True):
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

        :type suppress_consec_slashes: bool
        :param suppress_consec_slashes: If provided, controls whether
            consecutive slashes will be suppressed in key paths.
        """
        self.suppress_consec_slashes = suppress_consec_slashes
        self.num_retries = 6
        # Override passed-in is_secure setting if value was defined in config.
        if config.has_option('Boto', 'is_secure'):
            is_secure = config.getboolean('Boto', 'is_secure')
        self.is_secure = is_secure
        # Whether or not to validate server certificates.  At some point in the
        # future, the default should be flipped to true.
        self.https_validate_certificates = config.getbool(
                'Boto', 'https_validate_certificates', False)
        if self.https_validate_certificates and not HAVE_HTTPS_CONNECTION:
            raise BotoClientError(
                    "SSL server certificate validation is enabled in boto "
                    "configuration, but Python dependencies required to "
                    "support this feature are not available. Certificate "
                    "validation is only supported when running under Python "
                    "2.6 or later.")
        self.ca_certificates_file = config.get_value(
                'Boto', 'ca_certificates_file', DEFAULT_CA_CERTS_FILE)
        # define exceptions from httplib that we want to catch and retry
        # TODO: Update for requests.
        self.http_exceptions = (
            httplib.HTTPException,
            socket.error,
            socket.gaierror
        )
        # define subclasses of the above that are not retryable.
        self.http_unretryable_exceptions = []
        if HAVE_HTTPS_CONNECTION:
            self.http_unretryable_exceptions.append(
                requests.exceptions.SSLError)

        # define values in socket exceptions we don't want to catch
        self.socket_exception_values = (errno.EINTR,)
        if https_connection_factory is not None:
            self.https_connection_factory = https_connection_factory[0]
            self.http_exceptions += https_connection_factory[1]
        else:
            self.https_connection_factory = None
        if is_secure:
            self.protocol = 'https'
        else:
            self.protocol = 'http'
        self.host = host
        self.path = path
        if isinstance(debug, (int, long)):
            self.debug = debug
        else:
            self.debug = config.getint('Boto', 'debug', 0)
        if port:
            self.port = port
        else:
            self.port = PORTS_BY_SECURITY[is_secure]

        if config.has_option('Boto', 'http_socket_timeout'):
            self.timeout = config.getint('Boto', 'http_socket_timeout')
        else:
            self.timeout = None

        self.provider = Provider(provider,
                                 aws_access_key_id,
                                 aws_secret_access_key,
                                 security_token)

        # allow config file to override default host
        if self.provider.host:
            self.host = self.provider.host

        self._connection = (self.server_name(), self.is_secure)
        self._last_rs = None
        self._auth_handler = auth.get_auth_handler(
              host, config, self.provider, self._required_auth_capability())

    def __repr__(self):
        return '%s:%s' % (self.__class__.__name__, self.host)

    def _required_auth_capability(self):
        return []

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
        # The default behavior is to suppress consecutive slashes for reasons
        # discussed at
        # https://groups.google.com/forum/#!topic/boto-dev/-ft0XPUy0y8
        # You can override that behavior with the suppress_consec_slashes param.
        if not self.suppress_consec_slashes:
            return self.path + re.sub('^/*', "", path)
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
            if ((ON_APP_ENGINE and sys.version[:3] == '2.5') or
                    sys.version[:3] in ('2.6', '2.7')) and port == 443:
                signature_host = self.host
            else:
                signature_host = '%s:%d' % (self.host, port)
        return signature_host

    def _mexe(self, request, sender=None, override_num_retries=None,
              retry_handler=None):
        """
        mexe - Multi-execute inside a loop, retrying multiple times to handle
               transient Internet errors by simply trying again.
               Also handles redirects.

        This code was inspired by the S3Utils classes posted to the boto-users
        Google group by Larry Bates.  Thanks!

        """
        boto.log.debug('')
        boto.log.debug('>>>>>> Request Details >>>>>>')
        boto.log.debug('Method: %s' % request.method)
        boto.log.debug('Path: %s' % request.path)
        boto.log.debug('Host: %s' % request.host)

        response = None
        body = None
        e = None
        if override_num_retries is None:
            num_retries = config.getint('Boto', 'num_retries', self.num_retries)
        else:
            num_retries = override_num_retries
        i = 0

        while i <= num_retries:
            # Use binary exponential backoff to de-synchronize client requests
            next_sleep = random.random() * (2 ** i)
            try:
                # we now re-sign each request before it is retried
                boto.log.debug('Token: %s' % self.provider.security_token)
                request.authorize(connection=self)

                url = '%s://%s%s' % (
                    request.protocol,
                    request.host,
                    request.path
                )

                # This is really, really explicit, but meh.
                if request.method == 'GET':
                    request_method = requests.get
                elif request.method == 'POST':
                    request_method = requests.post
                elif request.method == 'HEAD':
                    request_method = requests.head
                elif request.method == 'PUT':
                    request_method = requests.put
                elif request.method == 'DELETE':
                    request_method = requests.delete
                else:
                    raise BotoClientError(
                        "Unrecognized HTTP method: %s" % request.method
                    )

                response = request_method(
                    url,
                    data=request.body,
                    headers=request.headers,
                    verify=self.https_validate_certificates,
                    timeout=self.timeout,
                    #config={'verbose': sys.stderr},
                )
                boto.log.debug('Headers: %s' % response.request.headers)
                boto.log.debug('Data: %s' % request.body)

                status_reason = HTTP_REASON_CODES.get(response.status_code, 'Unknown')
                setattr(response, 'reason', status_reason)

                boto.log.debug('')
                boto.log.debug('<<<<<< Response Details <<<<<<')
                boto.log.debug('Status: %s' % response.status_code)
                boto.log.debug('Headers: %s' % response.headers)
                boto.log.debug('Content: %s' % response.content)
                boto.log.debug('<' * 30)
                boto.log.debug('')

                location = response.headers['location']

                if callable(retry_handler):
                    status = retry_handler(response, i, next_sleep)
                    if status:
                        msg, i, next_sleep = status
                        if msg:
                            boto.log.debug(msg)
                        time.sleep(next_sleep)
                        continue
                if response.status_code == 500 or response.status_code == 503:
                    msg = 'Received %d response.  ' % response.status_code
                    msg += 'Retrying in %3.1f seconds' % next_sleep
                    boto.log.debug(msg)
                    body = response.text
                elif response.status_code < 300 or \
                     response.status_code >= 400 or \
                     not location:
                    # Success.
                    return response
                else:
                    # Not sure what happened, appears to be a redir. Grab
                    # the components out of the 'location' header value.
                    scheme, request.host, request.path, \
                        params, query, fragment = urlparse.urlparse(location)
                    if query:
                        request.path += '?' + query
                    msg = 'Redirecting: %s' % scheme + '://'
                    msg += request.host + request.path
                    boto.log.debug(msg)
                    # Fall through to another re-try with the modified values.
                    continue
            except self.http_exceptions, e:
                for unretryable in self.http_unretryable_exceptions:
                    if isinstance(e, unretryable):
                        boto.log.debug(
                            'encountered unretryable %s exception, re-raising' %
                            e.__class__.__name__)
                        raise e
                boto.log.debug('encountered %s exception, reconnecting' % \
                                  e.__class__.__name__)
            time.sleep(next_sleep)
            i += 1
        # If we made it here, it's because we have exhausted our retries
        # and stil haven't succeeded.  So, if we have a response object,
        # use it to raise an exception.
        # Otherwise, raise the exception that must have already h#appened.
        if response:
            raise BotoServerError(response.status_code, status.reason, body)
        elif e:
            raise e
        else:
            msg = 'Please report this exception as a Boto Issue!'
            raise BotoClientError(msg)

    def build_base_http_request(self, method, path, auth_path,
                                params=None, headers=None, data='', host=None):
        path = self.get_path(path)
        if auth_path is not None:
            auth_path = self.get_path(auth_path)
        if params is None:
            params = {}
        else:
            params = params.copy()
        if headers is None:
            headers = {}
        else:
            headers = headers.copy()
        host = host or self.host

        return HTTPRequest(method, self.protocol, host, self.port,
                           path, auth_path, params, headers, data)

    def make_request(self, method, path, headers=None, data='', host=None,
                     auth_path=None, sender=None, override_num_retries=None):
        """Makes a request to the server, with stock multiple-retry logic."""
        http_request = self.build_base_http_request(method, path, auth_path,
                                                    {}, headers, data, host)
        return self._mexe(http_request, sender, override_num_retries)

    def close(self):
        """(Optional) Close any open HTTP connections.  This is non-destructive,
        and making a new request will open a connection again."""

        boto.log.debug('closing all HTTP connections')
        self._connection = None  # compat field

class AWSQueryConnection(AWSAuthConnection):

    APIVersion = ''
    ResponseError = BotoServerError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, host=None, debug=0,
                 https_connection_factory=None, path='/', security_token=None):
        AWSAuthConnection.__init__(self, host, aws_access_key_id,
                                   aws_secret_access_key,
                                   is_secure, port, proxy,
                                   proxy_port, proxy_user, proxy_pass,
                                   debug, https_connection_factory, path,
                                   security_token=security_token)

    def _required_auth_capability(self):
        return []

    def get_utf8_value(self, value):
        return boto.utils.get_utf8_value(value)

    def make_request(self, action, params=None, path='/', verb='GET'):
        http_request = self.build_base_http_request(verb, path, None,
                                                    params, {}, '',
                                                    self.server_name())
        if action:
            http_request.params['Action'] = action
        if self.APIVersion:
            http_request.params['Version'] = self.APIVersion
        return self._mexe(http_request)

    def build_list_params(self, params, items, label):
        if isinstance(items, str):
            items = [items]
        for i in range(1, len(items) + 1):
            params['%s.%d' % (label, i)] = items[i - 1]

    # generics

    def get_list(self, action, params, markers, path='/',
                 parent=None, verb='GET'):
        if not parent:
            parent = self
        response = self.make_request(action, params, path, verb)
        body = response.content
        boto.log.debug(body)
        if not body:
            boto.log.error('Null body %s' % body)
            raise self.ResponseError(response.status_code, response.reason, body)
        elif response.status_code == 200:
            rs = ResultSet(markers)
            h = boto.handler.XmlHandler(rs, parent)
            xml.sax.parseString(body, h)
            return rs
        else:
            boto.log.error('%s %s' % (response.status_code, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status_code, response.reason, body)

    def get_object(self, action, params, cls, path='/',
                   parent=None, verb='GET'):
        if not parent:
            parent = self
        response = self.make_request(action, params, path, verb)
        body = response.content
        boto.log.debug(body)
        if not body:
            boto.log.error('Null body %s' % body)
            raise self.ResponseError(response.status_code, response.reason, body)
        elif response.status_code == 200:
            obj = cls(parent)
            h = boto.handler.XmlHandler(obj, parent)
            xml.sax.parseString(body, h)
            return obj
        else:
            boto.log.error('%s %s' % (response.status_code, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status_code, response.reason, body)

    def get_status(self, action, params, path='/', parent=None, verb='GET'):
        if not parent:
            parent = self
        response = self.make_request(action, params, path, verb)
        body = response.content
        boto.log.debug(body)
        if not body:
            boto.log.error('Null body %s' % body)
            raise self.ResponseError(response.status_code, response.reason, body)
        elif response.status_code == 200:
            rs = ResultSet()
            h = boto.handler.XmlHandler(rs, parent)
            xml.sax.parseString(body, h)
            return rs.status
        else:
            boto.log.error('%s %s' % (response.status_code, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status_code, response.reason, body)
