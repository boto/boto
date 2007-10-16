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

import xml.sax
import urllib
import time
import boto.utils
from boto.connection import AWSAuthConnection
from boto import handler
from boto.s3.bucket import Bucket
from boto.resultset import ResultSet
from boto.exception import S3ResponseError, S3CreateError

class S3Connection(AWSAuthConnection):

    DefaultHost = 's3.amazonaws.com'
    QueryString = 'Signature=%s&Expires=%d&AWSAccessKeyId=%s'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=False, port=None, proxy=None, proxy_port=None,
                 host=DefaultHost, debug=0, https_connection_factory=None):
        AWSAuthConnection.__init__(self, host,
                                   aws_access_key_id, aws_secret_access_key,
                                   is_secure, port, proxy, proxy_port, debug,
                                   https_connection_factory)

    def __iter__(self):
        return self.get_all_buckets()
    
    def generate_url(self, expires_in, method, path,
                     headers=None, query_auth=True):
        if not headers:
            headers = {}
        expires = int(time.time() + expires_in)
        canonical_str = boto.utils.canonical_string(method, path,
                                                    headers, expires)
        encoded_canonical = boto.utils.encode(self.aws_secret_access_key,
                                              canonical_str, True)
        if '?' in path:
            arg_div = '&'
        elif query_auth:
            arg_div = '?'
        else:
            arg_div = ''
        if query_auth:
            query_part = self.QueryString % (encoded_canonical, expires,
                                             self.aws_access_key_id)
        else:
            query_part = ''
        return self.protocol + '://' + self.server_name + path  + arg_div + query_part
    
    def get_all_buckets(self):
        path = '/'
        response = self.make_request('GET', urllib.quote(path))
        body = response.read()
        if response.status > 300:
            raise S3ResponseError(response.status, response.reason, body)
        rs = ResultSet([('Bucket', Bucket)])
        h = handler.XmlHandler(rs, self)
        xml.sax.parseString(body, h)
        return rs

    def get_bucket(self, bucket_name):
        bucket = Bucket(self, bucket_name)
        rs = bucket.get_all_keys(None, maxkeys=0)
        return bucket

    def lookup(self, bucket_name):
        try:
            bucket = self.get_bucket(bucket_name)
        except:
            bucket = None
        return bucket

    def create_bucket(self, bucket_name, headers={}):
        path = '/%s' % bucket_name
        response = self.make_request('PUT', urllib.quote(path), headers)
        body = response.read()
        if response.status == 409:
             raise S3CreateError(response.status, response.reason, body)
        if response.status == 200:
            b = Bucket(self, bucket_name)
            return b
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def delete_bucket(self, bucket):
        if isinstance(bucket, Bucket):
            bucket_name = bucket.name
        else:
            bucket_name = bucket
        path = '/%s' % bucket_name
        response = self.make_request('DELETE', urllib.quote(path))
        body = response.read()
        if response.status != 204:
            raise S3ResponseError(response.status, response.reason, body)

