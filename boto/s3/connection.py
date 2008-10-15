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
import urllib, base64
import time
import boto.utils
import types
from boto.connection import AWSAuthConnection
from boto import handler
from boto.s3.bucket import Bucket
from boto.s3.key import Key
from boto.resultset import ResultSet
from boto.exception import S3ResponseError, S3CreateError, BotoClientError

def assert_case_insensitive(f):
    def wrapper(*args, **kwargs):
        if len(args) == 3 and not (args[2].islower() or args[2].isalnum()):
            raise BotoClientError("Bucket names cannot contain upper-case " \
            "characters when using either the sub-domain or virtual " \
        "hosting calling format.")
        return f(*args, **kwargs)
    return wrapper

class _CallingFormat:
    def build_url_base(self, protocol, server, bucket, key=''):
        url_base = '%s://' % protocol
        url_base += self.build_host(server, bucket)
        url_base += self.build_path_base(bucket, key)
        return url_base

    def build_host(self, server, bucket):
        if bucket == '':
            return server
        else:
            return self.get_bucket_server(server, bucket)

    def build_auth_path(self, bucket, key=''):
        path = ''
        if bucket != '':
            path = '/' + bucket
        return path + '/%s' % urllib.quote(key)

    def build_path_base(self, bucket, key=''):
        return '/%s' % urllib.quote(key)

class SubdomainCallingFormat(_CallingFormat):
    @assert_case_insensitive
    def get_bucket_server(self, server, bucket):
        return '%s.%s' % (bucket, server)

class VHostCallingFormat(_CallingFormat):
    @assert_case_insensitive
    def get_bucket_server(self, server, bucket):
        return bucket

class OrdinaryCallingFormat(_CallingFormat):
    def get_bucket_server(self, server, bucket):
        return server

    def build_path_base(self, bucket, key=''):
        path_base = '/'
        if bucket:
            path_base += "%s/" % bucket
        return path_base + urllib.quote(key)

class Location:
    DEFAULT = ''
    EU = 'EU'

class S3Connection(AWSAuthConnection):

    DefaultHost = 's3.amazonaws.com'
    QueryString = 'Signature=%s&Expires=%d&AWSAccessKeyId=%s'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 host=DefaultHost, debug=0, https_connection_factory=None,
                 calling_format=SubdomainCallingFormat()):
        self.calling_format = calling_format
        AWSAuthConnection.__init__(self, host,
                aws_access_key_id, aws_secret_access_key,
                is_secure, port, proxy, proxy_port, debug=debug,
                https_connection_factory=https_connection_factory)

    def __iter__(self):
        return self.get_all_buckets()

    def __contains__(self, bucket_name):
       return not (self.lookup(bucket_name) is None)

    def build_post_policy(self, expiration_time, conditions):
        """
        Taken from the AWS book Python examples and modified for use with boto
        """
        if type(expiration_time) != time.struct_time:
            raise 'Policy document must include a valid expiration Time object'

        # Convert conditions object mappings to condition statements

        return '{"expiration": "%s",\n"conditions": [%s]}' % \
            (time.strftime(boto.utils.ISO8601, expiration_time), ",".join(conditions))


    def build_post_form_args(self, bucket_name, key, expires_in = 6000,
                        acl = None, success_action_redirect = None, max_content_length = None,
                        http_method = "http"):
        """
        Taken from the AWS book Python examples and modified for use with boto
        This only returns the arguments required for the post form, not the actual form
        This does not return the file input field which also needs to be added

        @param bucket_name: Bucket to submit to
        @param key: Key name, optionally add ${filename} to the end to attach the submitted filename
        @param expires_in: Time (in seconds) before this expires, defaults to 6000
        @param acl: ACL rule to use, if any
        @param success_action_redirect: URL to redirect to on success
        @param max_content_length: Maximum size for this file
        @param http_method: HTTP Method to use, "http" or "https"

        @return: {"action": action_url_to_post_to, "fields": [ {"name": field_name, "value":  field_value}, {"name": field_name2, "value": field_value2} ] }
        @rtype: dict
        """
        fields = []
        conditions = []
        expiration = time.gmtime(int(time.time() + expires_in))

        # Generate policy document
        conditions.append('{"bucket": "%s"}' % bucket_name)
        if key.endswith("${filename}"):
            conditions.append('["starts-with", "$key", "%s"]' % key[:-len("${filename}")])
        else:
            conditions.append('{"key": "%s"}' % key)
        if acl:
            conditions.append('{"acl": "%s"}' % acl)
            fields.append({ "name": "acl", "value": acl})
        if success_action_redirect:
            conditions.append('{"success_action_redirect": "%s"}' % success_action_redirect)
            fields.append({ "name": "success_action_redirect", "value": success_action_redirect})
        if max_content_length:
            conditions.append('["content-length-range", 0, %i]' % max_content_length)
            fields.append({"name":'content-length-range', "value": "0,%i" % max_content_length})

        policy = self.build_post_policy(expiration, conditions)

        # Add the base64-encoded policy document as the 'policy' field
        policy_b64 = base64.b64encode(policy)
        fields.append({"name": "policy", "value": policy_b64})

        # Add the AWS access key as the 'AWSAccessKeyId' field
        fields.append({"name": "AWSAccessKeyId", "value": self.aws_access_key_id})

        # Add signature for encoded policy document as the 'AWSAccessKeyId' field
        hmac_copy = self.hmac.copy()
        hmac_copy.update(policy_b64)
        signature = base64.encodestring(hmac_copy.digest()).strip()
        fields.append({"name": "signature", "value": signature})
        fields.append({"name": "key", "value": key})

        # HTTPS protocol will be used if the secure HTTP option is enabled.
        url = '%s://%s.s3.amazonaws.com/' % (http_method, bucket_name)

        return {"action": url, "fields": fields}


    def generate_url(self, expires_in, method, bucket='', key='',
                     headers=None, query_auth=True, force_http=False):
        if not headers:
            headers = {}
        expires = int(time.time() + expires_in)
        auth_path = self.calling_format.build_auth_path(bucket, key)
        canonical_str = boto.utils.canonical_string(method, auth_path,
                                                    headers, expires)
        hmac_copy = self.hmac.copy()
        hmac_copy.update(canonical_str)
        b64_hmac = base64.encodestring(hmac_copy.digest()).strip()
        encoded_canonical = urllib.quote_plus(b64_hmac)
        path = self.calling_format.build_path_base(bucket, key)
        if query_auth:
            query_part = '?' + self.QueryString % (encoded_canonical, expires,
                                             self.aws_access_key_id)
        else:
            query_part = ''
        if force_http:
            protocol = 'http'
            server_name = self.server
        else:
            protocol = self.protocol
            server_name = self.server_name
        return self.calling_format.build_url_base(protocol,
                server_name, bucket, key) + query_part

    def get_all_buckets(self):
        response = self.make_request('GET')
        body = response.read()
        if response.status > 300:
            raise S3ResponseError(response.status, response.reason, body)
        rs = ResultSet([('Bucket', Bucket)])
        h = handler.XmlHandler(rs, self)
        xml.sax.parseString(body, h)
        return rs

    def get_canonical_user_id(self):
        """
        Convenience method that returns the "CanonicalUserID" of the user who's credentials
        are associated with the connection.  The only way to get this value is to do a GET
        request on the service which returns all buckets associated with the account.  As part
        of that response, the canonical userid is returned.  This method simply does all of
        that and then returns just the user id.

        @rtype: string
        @return: A string containing the canonical user id.
        """
        rs = self.get_all_buckets()
        return rs.ID

    def get_bucket(self, bucket_name, validate=True):
        bucket = Bucket(self, bucket_name)
        if validate:
            rs = bucket.get_all_keys(None, maxkeys=0)
        return bucket

    def lookup(self, bucket_name, validate=True):
        try:
            bucket = self.get_bucket(bucket_name, validate)
        except:
            bucket = None
        return bucket

    def create_bucket(self, bucket_name, headers=None, location=Location.DEFAULT, policy=None):
        """
        Creates a new located bucket. By default it's in the USA. You can pass
        Location.EU to create an European bucket.

        @type bucket_name: string
        @param bucket_name: The name of the new bucket
        
        @type headers: dict
        @param headers: Additional headers to pass along with the request to AWS.

        @type location: L{Location<boto.s3.connection.Location>}
        @param location: The location of the new bucket
        
        @type policy: L{CannedACLString<boto.s3.acl.CannedACLStrings>}
        @param policy: A canned ACL policy that will be applied to the new key in S3.
             
        """
        if policy:
            if headers:
                headers['x-amz-acl'] = policy
            else:
                headers = {'x-amz-acl' : policy}
        if location == Location.DEFAULT:
            data = ''
        else:
            data = '<CreateBucketConstraint><LocationConstraint>' + \
                    location + '</LocationConstraint></CreateBucketConstraint>'
        response = self.make_request('PUT', bucket_name, headers=headers,
                data=data)
        body = response.read()
        if response.status == 409:
            raise S3CreateError(response.status, response.reason, body)
        if response.status == 200:
            return Bucket(self, bucket_name)
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def delete_bucket(self, bucket):
        response = self.make_request('DELETE', bucket)
        body = response.read()
        if response.status != 204:
            raise S3ResponseError(response.status, response.reason, body)

    def make_request(self, method, bucket='', key='', headers=None, data='',
            query_args=None, sender=None):
        if isinstance(bucket, Bucket):
            bucket = bucket.name
        if isinstance(key, Key):
            key = key.name
        path = self.calling_format.build_path_base(bucket, key)
        auth_path = self.calling_format.build_auth_path(bucket, key)
        host = self.calling_format.build_host(self.server, bucket)
        if query_args:
            path += '?' + query_args
            auth_path += '?' + query_args
        return AWSAuthConnection.make_request(self, method, path, headers,
                data, host, auth_path, sender)

#    def checked_request(self, method, bucket='', key='', headers=None, data='',
#            query_args=None, sender=None, good_status=200):
#        response = self.make_request(method, bucket, key, headers, data,
#                query_args, sender)
#        return check_s3_response(response, good_status)
