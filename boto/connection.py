# Copyright (c) 2006 Mitch Garnaat http://garnaat.org/
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
import re
import sha
import sys
import time
import urllib
import os
import xml.sax
from boto.exception import SQSError, S3ResponseError, S3CreateError
from boto import handler
from boto.queue import Queue
from boto.bucket import Bucket
from boto.user import User

PORTS_BY_SECURITY = { True: 443, False: 80 }
METADATA_PREFIX = 'x-amz-meta-'
AMAZON_HEADER_PREFIX = 'x-amz-'

# generates the aws canonical string for the given parameters
def canonical_string(method, path, headers, expires=None):
    interesting_headers = {}
    for key in headers:
        lk = key.lower()
        if lk in ['content-md5', 'content-type', 'date'] or lk.startswith(AMAZON_HEADER_PREFIX):
            interesting_headers[lk] = headers[key].strip()

    # these keys get empty strings if they don't exist
    if not interesting_headers.has_key('content-type'):
        interesting_headers['content-type'] = ''
    if not interesting_headers.has_key('content-md5'):
        interesting_headers['content-md5'] = ''

    # just in case someone used this.  it's not necessary in this lib.
    if interesting_headers.has_key('x-amz-date'):
        interesting_headers['date'] = ''

    # if you're using expires for query string auth, then it trumps date
    # (and x-amz-date)
    if expires:
        interesting_headers['date'] = str(expires)

    sorted_header_keys = interesting_headers.keys()
    sorted_header_keys.sort()

    buf = "%s\n" % method
    for key in sorted_header_keys:
        if key.startswith(AMAZON_HEADER_PREFIX):
            buf += "%s:%s\n" % (key, interesting_headers[key])
        else:
            buf += "%s\n" % interesting_headers[key]

    # don't include anything after the first ? in the resource...
    buf += "%s" % path.split('?')[0]

    # ...unless there is an acl or torrent parameter
    if re.search("[&?]acl($|=|&)", path):
        buf += "?acl"
    elif re.search("[&?]torrent($|=|&)", path):
        buf += "?torrent"

    return buf

# computes the base64'ed hmac-sha hash of the canonical string and the secret
# access key, optionally urlencoding the result
def encode(aws_secret_access_key, str, urlencode=False):
    b64_hmac = base64.encodestring(hmac.new(aws_secret_access_key, str, sha).digest()).strip()
    if urlencode:
        return urllib.quote_plus(b64_hmac)
    else:
        return b64_hmac

def merge_meta(headers, metadata):
    final_headers = headers.copy()
    for k in metadata.keys():
        final_headers[METADATA_PREFIX + k] = metadata[k]

    return final_headers

class AWSAuthConnection:
    def __init__(self, server, aws_access_key_id=None,
                 aws_secret_access_key=None,
                 is_secure=True, port=None, debug=False):
        self.is_secure = is_secure
        self.server = server
        self.debug = debug
        if not port:
            port = PORTS_BY_SECURITY[is_secure]
        self.port = port

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

        self.make_http_connection()
        self._last_rs = None

    def make_http_connection(self):
        if self.debug:
            print 'establishing HTTP connection'
        if (self.is_secure):
            self.connection = httplib.HTTPSConnection("%s:%d" % (self.server,
                                                                 self.port))
        else:
            self.connection = httplib.HTTPConnection("%s:%d" % (self.server,
                                                                self.port))
        self.set_debug(self.debug)

    def set_debug(self, debug=0):
        self.debug = debug
        self.connection.set_debuglevel(debug)

    def make_request(self, method, path, headers=None, data='', metadata=None):
        if headers == None:
            headers = {}
        if metadata == None:
            metadata = {}
        final_headers = merge_meta(headers, metadata);
        # add auth header
        self.add_aws_auth_header(final_headers, method, path)

        self.connection.request(method, path, data, final_headers)
        try:
            return self.connection.getresponse()
        except httplib.HTTPException, e:
            self.make_http_connection()
            self.connection.request(method, path, data, final_headers)
            return self.connection.getresponse()

    def add_aws_auth_header(self, headers, method, path):
        if not headers.has_key('Date'):
            headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT",
                                            time.gmtime())

        c_string = canonical_string(method, path, headers)
        if self.debug:
            print '\n\n%s\n\n' % c_string
        headers['Authorization'] = \
            "AWS %s:%s" % (self.aws_access_key_id, encode(self.aws_secret_access_key, c_string))
        
class SQSConnection(AWSAuthConnection):
    
    DefaultHost = 'queue.amazonaws.com'
    DefaultVersion = '2006-04-01'
    DefaultContentType = 'text/plain'
    
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=False, port=None, debug=0):
        AWSAuthConnection.__init__(self, self.DefaultHost,
                                   aws_access_key_id, aws_secret_access_key,
                                   is_secure, port, debug)

    def make_request(self, method, path, headers=None, data=''):
        # add auth header
        if headers == None:
            headers = {}

        if not headers.has_key('AWS-Version'):
            headers['AWS-Version'] = self.DefaultVersion

        if not headers.has_key('Content-Type'):
            headers['Content-Type'] = self.DefaultContentType

        return AWSAuthConnection.make_request(self, method, path,
                                              headers, data)

    def get_all_queues(self, prefix=''):
        if prefix:
            path = '/?QueueNamePrefix=%s' % prefix
        else:
            path = '/'
        response = self.make_request('GET', path)
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        h = handler.XmlHandler(self, {'QueueUrl': Queue})
        xml.sax.parseString(body, h)
        return h.rs

    def create_queue(self, queue_name, visibility_timeout=None):
        path = '/?QueueName=%s' % queue_name
        if visibility_timeout:
            path = path + '&DefaultVisibilityTimeout=%d' % visibility_timeout
        response = self.make_request('POST', path)
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        h = handler.XmlHandler(self, {'QueueUrl' : Queue})
        xml.sax.parseString(body, h)
        self._last_rs = h.rs
        return h.rs[0]

    def delete_queue(self, queue):
        response = self.make_request('DELETE', queue.id)
        body = response.read()
        if response.status >= 300:
            raise SQSError(response.status, response.reason, body)
        h = handler.XmlHandler(self, {})
        xml.sax.parseString(body, h)
        return h.rs

class S3Connection(AWSAuthConnection):

    DefaultHost = 's3.amazonaws.com'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=False, port=None, debug=0):
        AWSAuthConnection.__init__(self, self.DefaultHost,
                                   aws_access_key_id, aws_secret_access_key,
                                   is_secure, port, debug)
    
    def get_all_buckets(self):
        path = '/'
        response = self.make_request('GET', urllib.quote(path))
        body = response.read()
        if response.status > 300:
            raise S3ResponseError(response.status, response.reason)
        # h = handler.XmlHandler(self, {'Owner': User,
        #                               'Bucket': Bucket})
        # ignoring Owner for now
        h = handler.XmlHandler(self, {'Bucket': Bucket})
        xml.sax.parseString(body, h)
        return h.rs

    def create_bucket(self, bucket_name, headers={}):
        path = '/%s' % bucket_name
        response = self.make_request('PUT', urllib.quote(path), headers)
        body = response.read()
        if response.status == 409:
             raise S3CreateError(response.status, response.reason)
        if response.status == 200:
            b = Bucket(self, bucket_name, debug=self.debug)
            return b
        else:
            raise S3ResponseError(response.status, response.reason)

    def delete_bucket(self, bucket):
        path = '/%s' % bucket.name
        response = self.make_request('DELETE', urllib.quote(path))
        body = response.read()
        if response.status != 204:
            raise S3ResponseError(response.status, response.reason)

