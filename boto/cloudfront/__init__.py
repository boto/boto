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

import xml.sax
import base64
import time
import boto.utils
from boto.connection import AWSAuthConnection
from boto import handler
from boto.cloudfront.distribution import Distribution, DistributionConfig, DistributionSummary
from boto.resultset import ResultSet
from boto.cloudfront.exception import CloudFrontServerError

class CloudFrontConnection(AWSAuthConnection):

    DefaultHost = 'cloudfront.amazonaws.com'
    Version = '2008-06-30'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 port=None, proxy=None, proxy_port=None,
                 host=DefaultHost, debug=0):
        AWSAuthConnection.__init__(self, host,
                aws_access_key_id, aws_secret_access_key,
                True, port, proxy, proxy_port, debug=debug)

    def get_all_distributions(self):
        response = self.make_request('GET', '/%s/distribution' % self.Version)
        body = response.read()
        if response.status >= 300:
            raise CloudFrontServerError(response.status, response.reason, body)
        rs = ResultSet([('DistributionSummary', DistributionSummary)])
        h = handler.XmlHandler(rs, self)
        xml.sax.parseString(body, h)
        return rs

    def get_distribution_info(self, distribution_id):
        response = self.make_request('GET', '/%s/distribution/%s' % (self.Version, distribution_id))
        body = response.read()
        if response.status >= 300:
            raise CloudFrontServerError(response.status, response.reason, body)
        d = Distribution(connection=self)
        response_headers = response.msg
        for key in response_headers.keys():
            if key.lower() == 'etag':
                d.etag = response_headers[key]
        h = handler.XmlHandler(d, self)
        xml.sax.parseString(body, h)
        return d

    def get_etag(self, response):
        response_headers = response.msg
        for key in response_headers.keys():
            if key.lower() == 'etag':
                return response_headers[key]
        return None
    
    def get_distribution_config(self, distribution_id):
        response = self.make_request('GET', '/%s/distribution/%s/config' % (self.Version, distribution_id))
        body = response.read()
        if response.status >= 300:
            raise CloudFrontServerError(response.status, response.reason, body)
        d = DistributionConfig(connection=self)
        d.etag = self.get_etag(response)
        h = handler.XmlHandler(d, self)
        xml.sax.parseString(body, h)
        return d
    
    def set_distribution_config(self, distribution_id, etag, config):
        response = self.make_request('PUT', '/%s/distribution/%s/config' % (self.Version, distribution_id),
                                     {'If-Match' : etag, 'Content-Type' : 'text/xml'}, config.to_xml())
        body = response.read()
        return self.get_etag(response)
        if response.status != 200:
            raise CloudFrontServerError(response.status, response.reason, body)
    
    def create_distribution(self, origin, enabled, caller_reference='', cnames=None, comment=''):
        config = DistributionConfig(origin=origin, enabled=enabled,
                                    caller_reference=caller_reference,
                                    cnames=cnames, comment=comment)
        response = self.make_request('POST', '/%s/distribution' % self.Version,
                                     {'Content-Type' : 'text/xml'}, data=config.to_xml())
        body = response.read()
        if response.status == 201:
            d = Distribution(connection=self)
            h = handler.XmlHandler(d, self)
            xml.sax.parseString(body, h)
            return d
        else:
            raise CloudFrontServerError(response.status, response.reason, body)
        
    def delete_distribution(self, distribution_id, etag):
        response = self.make_request('DELETE', '/%s/distribution/%s' % (self.Version, distribution_id),
                                     {'If-Match' : etag})
        body = response.read()
        if response.status != 204:
            raise CloudFrontServerError(response.status, response.reason, body)

    def add_aws_auth_header(self, headers, method, path):
        if not headers.has_key('Date'):
            headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT",
                                            time.gmtime())

        hmac = self.hmac.copy()
        hmac.update(headers['Date'])
        b64_hmac = base64.encodestring(hmac.digest()).strip()
        headers['Authorization'] = "AWS %s:%s" % (self.aws_access_key_id, b64_hmac)
