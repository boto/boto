# Copyright 2010 Google Inc.
# Copyright (c) 2011 Mitch Garnaat http://garnaat.org/
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
import copy
import datetime
from email.utils import formatdate
import hmac
import os
import sys
import time
import urllib
import urlparse
import posixpath

from boto.auth_handler import AuthHandler
from boto.exception import BotoClientError

try:
    from hashlib import sha1 as sha
    from hashlib import sha256 as sha256
except ImportError:
    import sha
    sha256 = None


class HmacKeys(object):
    """Key based Auth handler helper."""

    def __init__(self, host, config, provider):
        if provider.access_key is None or provider.secret_key is None:
            raise boto.auth_handler.NotReadyToAuthenticate()
        self.host = host
        self.update_provider(provider)

    def update_provider(self, provider):
        self._provider = provider
        self._hmac = hmac.new(self._provider.secret_key, digestmod=sha)
        if sha256:
            self._hmac_256 = hmac.new(self._provider.secret_key,
                                      digestmod=sha256)
        else:
            self._hmac_256 = None

    def algorithm(self):
        if self._hmac_256:
            return 'HmacSHA256'
        else:
            return 'HmacSHA1'

    def _get_hmac(self):
        if self._hmac_256:
            digestmod = sha256
        else:
            digestmod = sha
        return hmac.new(self._provider.secret_key,
                        digestmod=digestmod)

    def sign_string(self, string_to_sign):
        new_hmac = self._get_hmac()
        new_hmac.update(string_to_sign)
        return base64.encodestring(new_hmac.digest()).strip()

    def __getstate__(self):
        pickled_dict = copy.copy(self.__dict__)
        del pickled_dict['_hmac']
        del pickled_dict['_hmac_256']
        return pickled_dict

    def __setstate__(self, dct):
        self.__dict__ = dct
        self.update_provider(self._provider)


class AnonAuthHandler(AuthHandler, HmacKeys):
    """
    Implements Anonymous requests.
    """

    capability = ['anon']

    def __init__(self, host, config, provider):
        super(AnonAuthHandler, self).__init__(host, config, provider)

    def add_auth(self, http_request, **kwargs):
        pass


class HmacAuthV1Handler(AuthHandler, HmacKeys):
    """    Implements the HMAC request signing used by S3 and GS."""

    capability = ['hmac-v1', 's3']

    def __init__(self, host, config, provider):
        AuthHandler.__init__(self, host, config, provider)
        HmacKeys.__init__(self, host, config, provider)
        self._hmac_256 = None

    def update_provider(self, provider):
        super(HmacAuthV1Handler, self).update_provider(provider)
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
        auth = ("%s %s:%s" % (auth_hdr, self._provider.access_key, b64_hmac))
        boto.log.debug('Signature:\n%s' % auth)
        headers['Authorization'] = auth


class HmacAuthV2Handler(AuthHandler, HmacKeys):
    """
    Implements the simplified HMAC authorization used by CloudFront.
    """
    capability = ['hmac-v2', 'cloudfront']

    def __init__(self, host, config, provider):
        AuthHandler.__init__(self, host, config, provider)
        HmacKeys.__init__(self, host, config, provider)
        self._hmac_256 = None

    def update_provider(self, provider):
        super(HmacAuthV2Handler, self).update_provider(provider)
        self._hmac_256 = None

    def add_auth(self, http_request, **kwargs):
        headers = http_request.headers
        if 'Date' not in headers:
            headers['Date'] = formatdate(usegmt=True)
        if self._provider.security_token:
            key = self._provider.security_token_header
            headers[key] = self._provider.security_token

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

        if self._provider.security_token:
            key = self._provider.security_token_header
            headers[key] = self._provider.security_token

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
        l = sorted(['%s:%s' % (n.lower().strip(),
                    headers_to_sign[n].strip()) for n in headers_to_sign])
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
                                    http_request.auth_path,
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
        hash_value = sha256(string_to_sign).digest()
        b64_hmac = self.sign_string(hash_value)
        s = "AWS3 AWSAccessKeyId=%s," % self._provider.access_key
        s += "Algorithm=%s," % self.algorithm()
        s += "SignedHeaders=%s," % ';'.join(headers_to_sign)
        s += "Signature=%s" % b64_hmac
        req.headers['X-Amzn-Authorization'] = s


class HmacAuthV4Handler(AuthHandler, HmacKeys):
    """
    Implements the new Version 4 HMAC authorization.
    """

    capability = ['hmac-v4']

    def __init__(self, host, config, provider,
                 service_name=None, region_name=None):
        AuthHandler.__init__(self, host, config, provider)
        HmacKeys.__init__(self, host, config, provider)
        # You can set the service_name and region_name to override the
        # values which would otherwise come from the endpoint, e.g.
        # <service>.<region>.amazonaws.com.
        self.service_name = service_name
        self.region_name = region_name

    def _sign(self, key, msg, hex=False):
        if hex:
            sig = hmac.new(key, msg.encode('utf-8'), sha256).hexdigest()
        else:
            sig = hmac.new(key, msg.encode('utf-8'), sha256).digest()
        return sig

    def headers_to_sign(self, http_request):
        """
        Select the headers from the request that need to be included
        in the StringToSign.
        """
        host_header_value = self.host_header(self.host, http_request)
        headers_to_sign = {}
        headers_to_sign = {'Host': host_header_value}
        for name, value in http_request.headers.items():
            lname = name.lower()
            if lname.startswith('x-amz'):
                headers_to_sign[name] = value
        return headers_to_sign

    def host_header(self, host, http_request):
        port = http_request.port
        secure = http_request.protocol == 'https'
        if ((port == 80 and not secure) or (port == 443 and secure)):
            return host
        return '%s:%s' % (host, port)

    def query_string(self, http_request):
        parameter_names = sorted(http_request.params.keys())
        pairs = []
        for pname in parameter_names:
            pval = boto.utils.get_utf8_value(http_request.params[pname])
            pairs.append(urllib.quote(pname, safe='') + '=' +
                         urllib.quote(pval, safe='-_~'))
        return '&'.join(pairs)

    def canonical_query_string(self, http_request):
        # POST requests pass parameters in through the
        # http_request.body field.
        if http_request.method == 'POST':
            return ""
        l = []
        for param in sorted(http_request.params):
            value = boto.utils.get_utf8_value(http_request.params[param])
            l.append('%s=%s' % (urllib.quote(param, safe='-_.~'),
                                urllib.quote(value, safe='-_.~')))
        return '&'.join(l)

    def canonical_headers(self, headers_to_sign):
        """
        Return the headers that need to be included in the StringToSign
        in their canonical form by converting all header keys to lower
        case, sorting them in alphabetical order and then joining
        them into a string, separated by newlines.
        """
        canonical = []

        for header in headers_to_sign:
            c_name = header.lower().strip()
            raw_value = headers_to_sign[header]
            if '"' in raw_value:
                c_value = raw_value.strip()
            else:
                c_value = ' '.join(raw_value.strip().split())
            canonical.append('%s:%s' % (c_name, c_value))
        return '\n'.join(sorted(canonical))

    def signed_headers(self, headers_to_sign):
        l = ['%s' % n.lower().strip() for n in headers_to_sign]
        l = sorted(l)
        return ';'.join(l)

    def canonical_uri(self, http_request):
        path = http_request.auth_path
        # Normalize the path
        # in windows normpath('/') will be '\\' so we chane it back to '/'
        normalized = posixpath.normpath(path).replace('\\','/')
        # Then urlencode whatever's left.
        encoded = urllib.quote(normalized)
        if len(path) > 1 and path.endswith('/'):
            encoded += '/'
        return encoded

    def payload(self, http_request):
        body = http_request.body
        # If the body is a file like object, we can use
        # boto.utils.compute_hash, which will avoid reading
        # the entire body into memory.
        if hasattr(body, 'seek') and hasattr(body, 'read'):
            return boto.utils.compute_hash(body, hash_algorithm=sha256)[0]
        return sha256(http_request.body).hexdigest()

    def canonical_request(self, http_request):
        cr = [http_request.method.upper()]
        cr.append(self.canonical_uri(http_request))
        cr.append(self.canonical_query_string(http_request))
        headers_to_sign = self.headers_to_sign(http_request)
        cr.append(self.canonical_headers(headers_to_sign) + '\n')
        cr.append(self.signed_headers(headers_to_sign))
        cr.append(self.payload(http_request))
        return '\n'.join(cr)

    def scope(self, http_request):
        scope = [self._provider.access_key]
        scope.append(http_request.timestamp)
        scope.append(http_request.region_name)
        scope.append(http_request.service_name)
        scope.append('aws4_request')
        return '/'.join(scope)

    def split_host_parts(self, host):
        return host.split('.')

    def determine_region_name(self, host):
        parts = self.split_host_parts(host)
        if self.region_name is not None:
            region_name = self.region_name
        elif len(parts) > 1:
            if parts[1] == 'us-gov':
                region_name = 'us-gov-west-1'
            else:
                if len(parts) == 3:
                    region_name = 'us-east-1'
                else:
                    region_name = parts[1]
        else:
            region_name = parts[0]

        return region_name

    def determine_service_name(self, host):
        parts = self.split_host_parts(host)
        if self.service_name is not None:
            service_name = self.service_name
        else:
            service_name = parts[0]
        return service_name

    def credential_scope(self, http_request):
        scope = []
        http_request.timestamp = http_request.headers['X-Amz-Date'][0:8]
        scope.append(http_request.timestamp)
        # The service_name and region_name either come from:
        # * The service_name/region_name attrs or (if these values are None)
        # * parsed from the endpoint <service>.<region>.amazonaws.com.
        region_name = self.determine_region_name(http_request.host)
        service_name = self.determine_service_name(http_request.host)
        http_request.service_name = service_name
        http_request.region_name = region_name

        scope.append(http_request.region_name)
        scope.append(http_request.service_name)
        scope.append('aws4_request')
        return '/'.join(scope)

    def string_to_sign(self, http_request, canonical_request):
        """
        Return the canonical StringToSign as well as a dict
        containing the original version of all headers that
        were included in the StringToSign.
        """
        sts = ['AWS4-HMAC-SHA256']
        sts.append(http_request.headers['X-Amz-Date'])
        sts.append(self.credential_scope(http_request))
        sts.append(sha256(canonical_request).hexdigest())
        return '\n'.join(sts)

    def signature(self, http_request, string_to_sign):
        key = self._provider.secret_key
        k_date = self._sign(('AWS4' + key).encode('utf-8'),
                              http_request.timestamp)
        k_region = self._sign(k_date, http_request.region_name)
        k_service = self._sign(k_region, http_request.service_name)
        k_signing = self._sign(k_service, 'aws4_request')
        return self._sign(k_signing, string_to_sign, hex=True)

    def add_auth(self, req, **kwargs):
        """
        Add AWS4 authentication to a request.

        :type req: :class`boto.connection.HTTPRequest`
        :param req: The HTTPRequest object.
        """
        # This could be a retry.  Make sure the previous
        # authorization header is removed first.
        if 'X-Amzn-Authorization' in req.headers:
            del req.headers['X-Amzn-Authorization']
        now = datetime.datetime.utcnow()
        req.headers['X-Amz-Date'] = now.strftime('%Y%m%dT%H%M%SZ')
        if self._provider.security_token:
            req.headers['X-Amz-Security-Token'] = self._provider.security_token
        qs = self.query_string(req)
        if qs and req.method == 'POST':
            # Stash request parameters into post body
            # before we generate the signature.
            req.body = qs
            req.headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
            req.headers['Content-Length'] = str(len(req.body))
        else:
            # Safe to modify req.path here since
            # the signature will use req.auth_path.
            req.path = req.path.split('?')[0]

            if qs:
                # Don't insert the '?' unless there's actually a query string
                req.path = req.path + '?' + qs
        canonical_request = self.canonical_request(req)
        boto.log.debug('CanonicalRequest:\n%s' % canonical_request)
        string_to_sign = self.string_to_sign(req, canonical_request)
        boto.log.debug('StringToSign:\n%s' % string_to_sign)
        signature = self.signature(req, string_to_sign)
        boto.log.debug('Signature:\n%s' % signature)
        headers_to_sign = self.headers_to_sign(req)
        l = ['AWS4-HMAC-SHA256 Credential=%s' % self.scope(req)]
        l.append('SignedHeaders=%s' % self.signed_headers(headers_to_sign))
        l.append('Signature=%s' % signature)
        req.headers['Authorization'] = ','.join(l)


class S3HmacAuthV4Handler(HmacAuthV4Handler, AuthHandler):
    """
    Implements a variant of Version 4 HMAC authorization specific to S3.
    """
    capability = ['hmac-v4-s3']

    def __init__(self, *args, **kwargs):
        super(S3HmacAuthV4Handler, self).__init__(*args, **kwargs)

        if self.region_name:
            self.region_name = self.clean_region_name(self.region_name)

    def clean_region_name(self, region_name):
        if region_name.startswith('s3-'):
            return region_name[3:]

        return region_name

    def canonical_uri(self, http_request):
        # S3 does **NOT** do path normalization that SigV4 typically does.
        # Urlencode the path, **NOT** ``auth_path`` (because vhosting).
        path = urlparse.urlparse(http_request.path)
        # Because some quoting may have already been applied, let's back it out.
        unquoted = urllib.unquote(path.path)
        # Requote, this time addressing all characters.
        encoded = urllib.quote(unquoted)
        return encoded

    def host_header(self, host, http_request):
        port = http_request.port
        secure = http_request.protocol == 'https'
        if ((port == 80 and not secure) or (port == 443 and secure)):
            return http_request.host
        return '%s:%s' % (http_request.host, port)

    def headers_to_sign(self, http_request):
        """
        Select the headers from the request that need to be included
        in the StringToSign.
        """
        host_header_value = self.host_header(self.host, http_request)
        headers_to_sign = {}
        headers_to_sign = {'Host': host_header_value}
        for name, value in http_request.headers.items():
            lname = name.lower()
            # Hooray for the only difference! The main SigV4 signer only does
            # ``Host`` + ``x-amz-*``. But S3 wants pretty much everything
            # signed, except for authorization itself.
            if not lname in ['authorization']:
                headers_to_sign[name] = value
        return headers_to_sign

    def determine_region_name(self, host):
        # S3's different format(s) of representing region/service from the
        # rest of AWS makes this hurt too.
        #
        # Possible domain formats:
        # - s3.amazonaws.com (Classic)
        # - s3-us-west-2.amazonaws.com (Specific region)
        # - bukkit.s3.amazonaws.com (Vhosted Classic)
        # - bukkit.s3-ap-northeast-1.amazonaws.com (Vhosted specific region)
        # - s3.cn-north-1.amazonaws.com.cn - (Bejing region)
        # - bukkit.s3.cn-north-1.amazonaws.com.cn - (Vhosted Bejing region)
        parts = self.split_host_parts(host)

        if self.region_name is not None:
            region_name = self.region_name
        else:
            # Classic URLs - s3-us-west-2.amazonaws.com
            if len(parts) == 3:
                region_name = self.clean_region_name(parts[0])

                # Special-case for Classic.
                if region_name == 's3':
                    region_name = 'us-east-1'
            else:
                # Iterate over the parts in reverse order.
                for offset, part in enumerate(reversed(parts)):
                    part = part.lower()

                    # Look for the first thing starting with 's3'.
                    # Until there's a ``.s3`` TLD, we should be OK. :P
                    if part == 's3':
                        # If it's by itself, the region is the previous part.
                        region_name = parts[-offset]
                        break
                    elif part.startswith('s3-'):
                        region_name = self.clean_region_name(part)
                        break

        return region_name

    def determine_service_name(self, host):
        # Should this signing mechanism ever be used for anything else, this
        # will fail. Consider utilizing the logic from the parent class should
        # you find yourself here.
        return 's3'

    def mangle_path_and_params(self, req):
        """
        Returns a copy of the request object with fixed ``auth_path/params``
        attributes from the original.
        """
        modified_req = copy.copy(req)

        # Unlike the most other services, in S3, ``req.params`` isn't the only
        # source of query string parameters.
        # Because of the ``query_args``, we may already have a query string
        # **ON** the ``path/auth_path``.
        # Rip them apart, so the ``auth_path/params`` can be signed
        # appropriately.
        parsed_path = urlparse.urlparse(modified_req.auth_path)
        modified_req.auth_path = parsed_path.path

        if modified_req.params is None:
            modified_req.params = {}

        raw_qs = parsed_path.query
        existing_qs = urlparse.parse_qs(
            raw_qs,
            keep_blank_values=True
        )

        # ``parse_qs`` will return lists. Don't do that unless there's a real,
        # live list provided.
        for key, value in existing_qs.items():
            if isinstance(value, (list, tuple)):
                if len(value) == 1:
                    existing_qs[key] = value[0]

        modified_req.params.update(existing_qs)
        return modified_req

    def payload(self, http_request):
        if http_request.headers.get('x-amz-content-sha256'):
            return http_request.headers['x-amz-content-sha256']

        return super(S3HmacAuthV4Handler, self).payload(http_request)

    def add_auth(self, req, **kwargs):
        if not 'x-amz-content-sha256' in req.headers:
            if '_sha256' in req.headers:
                req.headers['x-amz-content-sha256'] = req.headers.pop('_sha256')
            else:
                req.headers['x-amz-content-sha256'] = self.payload(req)

        req = self.mangle_path_and_params(req)
        return super(S3HmacAuthV4Handler, self).add_auth(req, **kwargs)


class QueryAuthHandler(AuthHandler):
    """
    Provides pure query construction (no actual signing).

    Mostly useful for STS' ``assume_role_with_web_identity``.

    Does **NOT** escape query string values!
    """

    capability = ['pure-query']

    def _escape_value(self, value):
        # Would normally be ``return urllib.quote(value)``.
        return value

    def _build_query_string(self, params):
        keys = params.keys()
        keys.sort(cmp=lambda x, y: cmp(x.lower(), y.lower()))
        pairs = []
        for key in keys:
            val = boto.utils.get_utf8_value(params[key])
            pairs.append(key + '=' + self._escape_value(val))
        return '&'.join(pairs)

    def add_auth(self, http_request, **kwargs):
        headers = http_request.headers
        params = http_request.params
        qs = self._build_query_string(
            http_request.params
        )
        boto.log.debug('query_string: %s' % qs)
        headers['Content-Type'] = 'application/json; charset=UTF-8'
        http_request.body = ''
        # if this is a retried request, the qs from the previous try will
        # already be there, we need to get rid of that and rebuild it
        http_request.path = http_request.path.split('?')[0]
        http_request.path = http_request.path + '?' + qs


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
            headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
            http_request.body = qs + '&Signature=' + urllib.quote_plus(signature)
            http_request.headers['Content-Length'] = str(len(http_request.body))
        else:
            http_request.body = ''
            # if this is a retried request, the qs from the previous try will
            # already be there, we need to get rid of that and rebuild it
            http_request.path = http_request.path.split('?')[0]
            http_request.path = (http_request.path + '?' + qs +
                                 '&Signature=' + urllib.quote_plus(signature))


class QuerySignatureV0AuthHandler(QuerySignatureHelper, AuthHandler):
    """Provides Signature V0 Signing"""

    SignatureVersion = 0
    capability = ['sign-v0']

    def _calc_signature(self, params, *args):
        boto.log.debug('using _calc_signature_0')
        hmac = self._get_hmac()
        s = params['Action'] + params['Timestamp']
        hmac.update(s)
        keys = params.keys()
        keys.sort(cmp=lambda x, y: cmp(x.lower(), y.lower()))
        pairs = []
        for key in keys:
            val = boto.utils.get_utf8_value(params[key])
            pairs.append(key + '=' + urllib.quote(val))
        qs = '&'.join(pairs)
        return (qs, base64.b64encode(hmac.digest()))


class QuerySignatureV1AuthHandler(QuerySignatureHelper, AuthHandler):
    """
    Provides Query Signature V1 Authentication.
    """

    SignatureVersion = 1
    capability = ['sign-v1', 'mturk']

    def __init__(self, *args, **kw):
        QuerySignatureHelper.__init__(self, *args, **kw)
        AuthHandler.__init__(self, *args, **kw)
        self._hmac_256 = None

    def _calc_signature(self, params, *args):
        boto.log.debug('using _calc_signature_1')
        hmac = self._get_hmac()
        keys = params.keys()
        keys.sort(cmp=lambda x, y: cmp(x.lower(), y.lower()))
        pairs = []
        for key in keys:
            hmac.update(key)
            val = boto.utils.get_utf8_value(params[key])
            hmac.update(val)
            pairs.append(key + '=' + urllib.quote(val))
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
        hmac = self._get_hmac()
        params['SignatureMethod'] = self.algorithm()
        if self._provider.security_token:
            params['SecurityToken'] = self._provider.security_token
        keys = sorted(params.keys())
        pairs = []
        for key in keys:
            val = boto.utils.get_utf8_value(params[key])
            pairs.append(urllib.quote(key, safe='') + '=' +
                         urllib.quote(val, safe='-_~'))
        qs = '&'.join(pairs)
        boto.log.debug('query string: %s' % qs)
        string_to_sign += qs
        boto.log.debug('string_to_sign: %s' % string_to_sign)
        hmac.update(string_to_sign)
        b64 = base64.b64encode(hmac.digest())
        boto.log.debug('len(b64)=%d' % len(b64))
        boto.log.debug('base64 encoded digest: %s' % b64)
        return (qs, b64)


class POSTPathQSV2AuthHandler(QuerySignatureV2AuthHandler, AuthHandler):
    """
    Query Signature V2 Authentication relocating signed query
    into the path and allowing POST requests with Content-Types.
    """

    capability = ['mws']

    def add_auth(self, req, **kwargs):
        req.params['AWSAccessKeyId'] = self._provider.access_key
        req.params['SignatureVersion'] = self.SignatureVersion
        req.params['Timestamp'] = boto.utils.get_ts()
        qs, signature = self._calc_signature(req.params, req.method,
                                             req.auth_path, req.host)
        boto.log.debug('query_string: %s Signature: %s' % (qs, signature))
        if req.method == 'POST':
            req.headers['Content-Length'] = str(len(req.body))
            req.headers['Content-Type'] = req.headers.get('Content-Type',
                                                          'text/plain')
        else:
            req.body = ''
        # if this is a retried req, the qs from the previous try will
        # already be there, we need to get rid of that and rebuild it
        req.path = req.path.split('?')[0]
        req.path = (req.path + '?' + qs +
                             '&Signature=' + urllib.quote_plus(signature))


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
        boto.exception.NoAuthHandlerFound
    """
    ready_handlers = []
    auth_handlers = boto.plugin.get_plugin(AuthHandler, requested_capability)
    total_handlers = len(auth_handlers)
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

    # We select the last ready auth handler that was loaded, to allow users to
    # customize how auth works in environments where there are shared boto
    # config files (e.g., /etc/boto.cfg and ~/.boto): The more general,
    # system-wide shared configs should be loaded first, and the user's
    # customizations loaded last. That way, for example, the system-wide
    # config might include a plugin_directory that includes a service account
    # auth plugin shared by all users of a Google Compute Engine instance
    # (allowing sharing of non-user data between various services), and the
    # user could override this with a .boto config that includes user-specific
    # credentials (for access to user data).
    return ready_handlers[-1]


def detect_potential_sigv4(func):
    def _wrapper(self):
        if os.environ.get('EC2_USE_SIGV4', False):
            return ['hmac-v4']

        if boto.config.get('ec2', 'use-sigv4', False):
            return ['hmac-v4']

        if hasattr(self, 'region'):
            if getattr(self.region, 'endpoint', ''):
                if '.cn-' in self.region.endpoint:
                    return ['hmac-v4']

        return func(self)
    return _wrapper


def detect_potential_s3sigv4(func):
    def _wrapper(self):
        if os.environ.get('S3_USE_SIGV4', False):
            return ['hmac-v4-s3']

        if boto.config.get('s3', 'use-sigv4', False):
            return ['hmac-v4-s3']

        if hasattr(self, 'host'):
            if '.cn-' in self.host:
                return ['hmac-v4-s3']

        return func(self)
    return _wrapper
