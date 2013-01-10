# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.
# All Rights Reserved
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
import requests.packages.urllib3
import hmac
import base64
from hashlib import sha256
import sys
import datetime

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote


class SigV2Auth(object):
    """
    Sign an Query Signature V2 request.
    """
    def __init__(self, credentials, api_version=''):
        self.credentials = credentials
        self.api_version = api_version
        self.hmac = hmac.new(self.credentials.secret_key.encode('utf-8'),
                             digestmod=sha256)

    def calc_signature(self, args):
        scheme, host, port = requests.packages.urllib3.get_host(args['url'])
        string_to_sign = '%s\n%s\n%s\n' % (args['method'], host, '/')
        hmac = self.hmac.copy()
        args['params']['SignatureMethod'] = 'HmacSHA256'
        if self.credentials.token:
            args['params']['SecurityToken'] = self.credentials.token
        sorted_params = sorted(args['params'])
        pairs = []
        for key in sorted_params:
            value = args['params'][key]
            pairs.append(quote(key, safe='') + '=' +
                         quote(value, safe='-_~'))
        qs = '&'.join(pairs)
        string_to_sign += qs
        print('string_to_sign')
        print(string_to_sign)
        hmac.update(string_to_sign.encode('utf-8'))
        b64 = base64.b64encode(hmac.digest()).strip().decode('utf-8')
        return (qs, b64)

    def add_auth(self, args):
        args['params']['Action'] = 'DescribeInstances'
        args['params']['AWSAccessKeyId'] = self.credentials.access_key
        args['params']['SignatureVersion'] = '2'
        args['params']['Timestamp'] = datetime.datetime.utcnow().isoformat()
        args['params']['Version'] = self.api_version
        qs, signature = self.calc_signature(args)
        args['params']['Signature'] = signature
        if args['method'] == 'POST':
            args['data'] = args['params']
            args['params'] = {}
