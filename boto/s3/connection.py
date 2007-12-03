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
import time, re
import boto.utils
from boto.connection import AWSAuthConnection
from boto import handler
from boto.s3.bucket import Bucket
from boto.resultset import ResultSet
from boto.exception import S3ResponseError, S3CreateError

BucketConfigurationBody = """<CreateBucketConfiguration><LocationConstraint>%s</LocationConstraint></CreateBucketConfiguration>"""

DNSRegex = re.compile('^[a-z0-9]+[a-z0-9\\.-]*[a-z0-9\.]+')

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

    def make_request(self, method, path, headers=None, data='', metadata=None):
        if headers == None:
            headers = {}
        if metadata == None:
            metadata = {}
        if not headers.has_key('Content-Length'):
            headers['Content-Length'] = len(data)
        final_headers = boto.utils.merge_meta(headers, metadata);
        # ugh
        # we need to do some ugly stuff here to try to handle the "new style" requests
        # if the bucketname can be passed in the Host header, we should do it that way
        # otherwise, do it the old-fashioned (and much more elegant) way
        # is the path like this: /bucketname
        path_to_sign = path
        if path[1:].find('/') < 0:
            bucketname = path[1:]
            remainder = '/'
        else: # or like this /bucketname/key
            bucketname = path[1:path[1:].find('/')+1]
            remainder = path[path[1:].find('/')+1:]
        if len(bucketname) >= 3 and len(bucketname) <= 63:
            m = DNSRegex.search(bucketname)
            if m != None and m.end() == len(bucketname):
                if bucketname.find('-.') < 0:
                    final_headers['Host'] = '%s.%s' % (bucketname, self.server)
                    path = remainder
                    path_to_sign += '/'
        # add auth header
        self.add_aws_auth_header(final_headers, method, path_to_sign)
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

    def is_dns_name(self, bucket_name):
        if len(bucket_name) < 3 or len(bucket_name) > 63:
            return False
        m = DNSRegex.search(bucket_name)
        if m == None:
            return False
        if m.end() != len(bucket_name):
            return False
        if bucket_name.find('-.') != -1:
            return False
        return True
    
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

    def create_bucket(self, bucket_name, headers=None, location=''):
        path = '/%s' % bucket_name
        if location:
            body = BucketConfigurationBody % location
        else:
            body = ''
        print 'len(body)=%d' % len(body)
        response = self.make_request('PUT', urllib.quote(path), headers, body)
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

