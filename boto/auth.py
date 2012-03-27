# Copyright 2010 Google Inc.
# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Copyright (c) 2011, Eucalyptus Systems, Inc.
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
Handles authentication required to AWS and GS
"""

import base64
import boto
import boto.auth_handler
import boto.exception
import boto.plugin
import boto.utils
import hmac
import boto.compat as compat
from email.utils import formatdate

from boto.auth_handler import AuthHandler


class HmacKeys(object):
    """Key based Auth handler helper."""

    def __init__(self, host, config, provider):
        if provider.access_key is None or provider.secret_key is None:
            raise boto.auth_handler.NotReadyToAuthenticate()
        self.host = host
        self.update_provider(provider)

    def update_provider(self, provider):
        self._provider = provider
        sk = self._provider.secret_key.encode('utf-8')
        self._hmac = hmac.new(sk, digestmod=compat.sha)
        if compat.sha256:
            self._hmac_256 = hmac.new(sk, digestmod=compat.sha256)
        else:
            self._hmac_256 = None

    def algorithm(self):
        if self._hmac_256:
            return 'HmacSHA256'
        else:
            return 'HmacSHA1'

    def sign_string(self, string_to_sign):
        if self._hmac_256:
            hmac = self._hmac_256.copy()
        else:
            hmac = self._hmac.copy()
        if not isinstance(string_to_sign, compat.binary_type):
            string_to_sign = string_to_sign.encode('utf-8')
        hmac.update(string_to_sign)
        return base64.b64encode(hmac.digest()).strip().decode('utf-8')


class AnonAuthHandler(AuthHandler, HmacKeys):
    """
    Implements Anonymous requests.
    """

    capability = ['anon']

    def __init__(self, host, config, provider):
        AuthHandler.__init__(self, host, config, provider)

    def add_auth(self, http_request, **kwargs):
        pass


class HmacAuthV1Handler(AuthHandler, HmacKeys):
    """
    Implements the HMAC request signing used by S3 and GS.
    """

    capability = ['hmac-v1', 's3']

    def __init__(self, host, config, provider):
        AuthHandler.__init__(self, host, config, provider)
        HmacKeys.__init__(self, host, config, provider)
        self._hmac_256 = None

    def add_auth(self, http_request, **kwargs):
        headers = http_request.headers
        method = http_request.method
        auth_path = http_request.auth_path
        if 'Date' not in headers:
            headers['Date'] = formatdate(usegmt=True)

        if self._provider.security_token:
            key = self._provider.security_token_header
            headers[key] = self._provider.security_token
        string_to_sign = boto.utils.canonical_string(method, auth_path,
                                                     headers, None,
                                                     self._provider)
        boto.log.debug('StringToSign:\n%s' % string_to_sign)
        b64_hmac = self.sign_string(string_to_sign)
        auth_hdr = self._provider.auth_header
        headers['Authorization'] = ("%s %s:%s" %
                                    (auth_hdr,
                                     self._provider.access_key, b64_hmac))


class HmacAuthV2Handler(AuthHandler, HmacKeys):
    """
    Implements the simplified HMAC authorization used by CloudFront.
    """
    capability = ['hmac-v2', 'cloudfront']

    def __init__(self, host, config, provider):
        AuthHandler.__init__(self, host, config, provider)
        HmacKeys.__init__(self, host, config, provider)
        self._hmac_256 = None

    def add_auth(self, http_request, **kwargs):
        headers = http_request.headers
        if 'Date' not in headers:
            headers['Date'] = formatdate(usegmt=True)

        b64_hmac = self.sign_string(headers['Date'])
        auth_hdr = self._provider.auth_header
        headers['Authorization'] = ("%s %s:%s" %
                                    (auth_hdr,
                                     self._provider.access_key, b64_hmac))


class HmacAuthV3Handler(AuthHandler, HmacKeys):
    """Implements the new Version 3 HMAC authorization used by Route53."""

    capability = ['hmac-v3', 'route53', 'ses']

    def __init__(self, host, config, provider):
        AuthHandler.__init__(self, host, config, provider)
        HmacKeys.__init__(self, host, config, provider)

    def add_auth(self, http_request, **kwargs):
        headers = http_request.headers
        if 'Date' not in headers:
            headers['Date'] = formatdate(usegmt=True)

        b64_hmac = self.sign_string(headers['Date'])
        s = "AWS3-HTTPS AWSAccessKeyId=%s," % self._provider.access_key
        s += "Algorithm=%s,Signature=%s" % (self.algorithm(), b64_hmac)
        headers['X-Amzn-Authorization'] = s


class HmacAuthV3HTTPHandler(AuthHandler, HmacKeys):
    """
    Implements the new Version 3 HMAC authorization used by DynamoDB.
    """

    capability = ['hmac-v3-http']

    def __init__(self, host, config, provider):
        AuthHandler.__init__(self, host, config, provider)
        HmacKeys.__init__(self, host, config, provider)

    def headers_to_sign(self, http_request):
        """
        Select the headers from the request that need to be included
        in the StringToSign.
        """
        headers_to_sign = {}
        headers_to_sign = {'Host': self.host}
        for name, value in http_request.headers.items():
            lname = name.lower()
            if lname.startswith('x-amz'):
                headers_to_sign[name] = value
        return headers_to_sign

    def canonical_headers(self, headers_to_sign):
        """
        Return the headers that need to be included in the StringToSign
        in their canonical form by converting all header keys to lower
        case, sorting them in alphabetical order and then joining
        them into a string, separated by newlines.
        """
        l = ['%s:%s' % (n.lower().strip(),
                        headers_to_sign[n].strip()) for n in headers_to_sign]
        l.sort()
        return '\n'.join(l)

    def string_to_sign(self, http_request):
        """
        Return the canonical StringToSign as well as a dict
        containing the original version of all headers that
        were included in the StringToSign.
        """
        headers_to_sign = self.headers_to_sign(http_request)
        canonical_headers = self.canonical_headers(headers_to_sign)
        string_to_sign = '\n'.join([http_request.method,
                                    http_request.path,
                                    '',
                                    canonical_headers,
                                    '',
                                    http_request.body])
        return string_to_sign, headers_to_sign

    def add_auth(self, req, **kwargs):
        """
        Add AWS3 authentication to a request.

        :type req: :class`boto.connection.HTTPRequest`
        :param req: The HTTPRequest object.
        """
        # This could be a retry.  Make sure the previous
        # authorization header is removed first.
        if 'X-Amzn-Authorization' in req.headers:
            del req.headers['X-Amzn-Authorization']
        req.headers['X-Amz-Date'] = formatdate(usegmt=True)
        if self._provider.security_token:
            req.headers['X-Amz-Security-Token'] = self._provider.security_token
        string_to_sign, headers_to_sign = self.string_to_sign(req)
        boto.log.debug('StringToSign:\n%s' % string_to_sign)
        string_to_sign = string_to_sign.encode('utf-8')
        hash_value = compat.sha256(string_to_sign).digest()
        b64_hmac = self.sign_string(hash_value)
        s = "AWS3 AWSAccessKeyId=%s," % self._provider.access_key
        s += "Algorithm=%s," % self.algorithm()
        s += "SignedHeaders=%s," % ';'.join(headers_to_sign)
        s += "Signature=%s" % b64_hmac
        req.headers['X-Amzn-Authorization'] = s


class QuerySignatureHelper(HmacKeys):
    """
    Helper for Query signature based Auth handler.

    Concrete sub class need to implement _calc_sigature method.
    """

    def add_auth(self, http_request, **kwargs):
        headers = http_request.headers
        params = http_request.params
        params['AWSAccessKeyId'] = self._provider.access_key
        params['SignatureVersion'] = self.SignatureVersion
        params['Timestamp'] = boto.utils.get_ts()
        qs, signature = self._calc_signature(
            http_request.params, http_request.method,
            http_request.auth_path, http_request.host)
        boto.log.debug('query_string: %s Signature: %s' % (qs, signature))
        if http_request.method == 'POST':
            ct = 'application/x-www-form-urlencoded; charset=UTF-8'
            headers['Content-Type'] = ct
            http_request.body = qs + '&Signature='
            http_request.body += compat.quote_plus(signature)
            cl = str(len(http_request.body))
            http_request.headers['Content-Length'] = cl
        else:
            http_request.body = ''
            # if this is a retried request, the qs from the previous try will
            # already be there, we need to get rid of that and rebuild it
            http_request.path = http_request.path.split('?')[0]
            http_request.path = (http_request.path + '?' + qs +
                                 '&Signature=' + compat.quote_plus(signature))


class QuerySignatureV0AuthHandler(QuerySignatureHelper, AuthHandler):
    """Provides Signature V0 Signing"""

    SignatureVersion = 0
    capability = ['sign-v0']

    def _calc_signature(self, params, *args):
        boto.log.debug('using _calc_signature_0')
        hmac = self._hmac.copy()
        s = params['Action'] + params['Timestamp']
        s = s.encode('utf-8')
        hmac.update(s)
        keys = sorted(params, key=str.lower)
        pairs = []
        for key in keys:
            val = boto.utils.get_utf8_value(params[key])
            pairs.append(key + '=' + compat.quote(val))
        qs = '&'.join(pairs)
        return (qs, base64.b64encode(hmac.digest()))


class QuerySignatureV1AuthHandler(QuerySignatureHelper, AuthHandler):
    """
    Provides Query Signature V1 Authentication.
    """

    SignatureVersion = 1
    capability = ['sign-v1', 'mturk']

    def _calc_signature(self, params, *args):
        boto.log.debug('using _calc_signature_1')
        hmac = self._hmac.copy()
        keys = sorted(params, key=str.lower)
        pairs = []
        for key in keys:
            key = key.encode('utf-8')
            hmac.update(key)
            val = boto.utils.get_utf8_value(params[key])
            val = val.encode('utf-8')
            hmac.update(val)
            pairs.append(key + '=' + compat.quote(val))
        qs = '&'.join(pairs)
        return (qs, base64.b64encode(hmac.digest()))


class QuerySignatureV2AuthHandler(QuerySignatureHelper, AuthHandler):
    """Provides Query Signature V2 Authentication."""

    SignatureVersion = 2
    capability = ['sign-v2', 'ec2', 'ec2', 'emr', 'fps', 'ecs',
                  'sdb', 'iam', 'rds', 'sns', 'sqs', 'cloudformation']

    def _calc_signature(self, params, verb, path, server_name):
        boto.log.debug('using _calc_signature_2')
        string_to_sign = '%s\n%s\n%s\n' % (verb, server_name.lower(), path)
        if self._hmac_256:
            hmac = self._hmac_256.copy()
            params['SignatureMethod'] = 'HmacSHA256'
        else:
            hmac = self._hmac.copy()
            params['SignatureMethod'] = 'HmacSHA1'
        if self._provider.security_token:
            params['SecurityToken'] = self._provider.security_token
        keys = sorted(params)
        pairs = []
        for key in keys:
            val = boto.utils.get_utf8_value(params[key])
            pairs.append(compat.quote(key, safe='') + '=' +
                         compat.quote(val, safe='-_~'))
        qs = '&'.join(pairs)
        boto.log.debug('query string: %s' % qs)
        string_to_sign += qs
        boto.log.debug('string_to_sign: %s' % string_to_sign)
        string_to_sign = string_to_sign.encode('utf-8')
        hmac.update(string_to_sign)
        b64 = base64.b64encode(hmac.digest())
        boto.log.debug('len(b64)=%d' % len(b64))
        boto.log.debug('base64 encoded digest: %s' % b64)
        return (qs, b64)


def get_auth_handler(host, config, provider, requested_capability=None):
    """Finds an AuthHandler that is ready to authenticate.

    Lists through all the registered AuthHandlers to find one that is willing
    to handle for the requested capabilities, config and provider.

    :type host: string
    :param host: The name of the host

    :type config:
    :param config:

    :type provider:
    :param provider:

    Returns:
        An implementation of AuthHandler.

    Raises:
        boto.exception.NoAuthHandlerFound:
        boto.exception.TooManyAuthHandlerReadyToAuthenticate:
    """
    ready_handlers = []
    auth_handlers = boto.plugin.get_plugin(AuthHandler, requested_capability)
    for handler in auth_handlers:
        try:
            ready_handlers.append(handler(host, config, provider))
        except boto.auth_handler.NotReadyToAuthenticate:
            pass

    if not ready_handlers:
        checked_handlers = auth_handlers
        names = [handler.__name__ for handler in checked_handlers]
        raise boto.exception.NoAuthHandlerFound(
              'No handler was ready to authenticate. %d handlers were checked.'
              ' %s '
              'Check your credentials' % (len(names), str(names)))

    if len(ready_handlers) > 1:
        # NOTE: Even though it would be nice to accept more than one handler
        # by using one of the many ready handlers, we are never sure that each
        # of them are referring to the same storage account. Since we cannot
        # easily guarantee that, it is always safe to fail, rather than operate
        # on the wrong account.
        names = [handler.__class__.__name__ for handler in ready_handlers]
        raise boto.exception.TooManyAuthHandlerReadyToAuthenticate(
               '%d handlers %s ready to authenticate for requested_capability '
               '%s, only 1 expected. This happens if you import multiple '
               'pluging.Plugin implementations that declare support for the '
               'requested_capability.' % (len(names), str(names),
               requested_capability))

    return ready_handlers[0]
