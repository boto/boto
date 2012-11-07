# Copyright (c) 2006-2010 Mitch Garnaat http://garnaat.org/
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

import xml.sax
import urllib
import base64
import time

import boto.utils
from boto.connection import AWSAuthConnection
from boto import handler
from boto.s3.bucket import Bucket
from boto.s3.key import Key
from boto.resultset import ResultSet
from boto.exception import BotoClientError, S3ResponseError


def check_lowercase_bucketname(n):
    """
    Bucket names must not contain uppercase characters. We check for
    this by appending a lowercase character and testing with islower().
    Note this also covers cases like numeric bucket names with dashes.

    >>> check_lowercase_bucketname("Aaaa")
    Traceback (most recent call last):
    ...
    BotoClientError: S3Error: Bucket names cannot contain upper-case
    characters when using either the sub-domain or virtual hosting calling
    format.

    >>> check_lowercase_bucketname("1234-5678-9123")
    True
    >>> check_lowercase_bucketname("abcdefg1234")
    True
    """
    if not (n + 'a').islower():
        raise BotoClientError("Bucket names cannot contain upper-case " \
            "characters when using either the sub-domain or virtual " \
            "hosting calling format.")
    return True


def assert_case_insensitive(f):
    def wrapper(*args, **kwargs):
        if len(args) == 3 and check_lowercase_bucketname(args[2]):
            pass
        return f(*args, **kwargs)
    return wrapper


class _CallingFormat(object):

    def get_bucket_server(self, server, bucket):
        return ''

    def build_url_base(self, connection, protocol, server, bucket, key=''):
        url_base = '%s://' % protocol
        url_base += self.build_host(server, bucket)
        url_base += connection.get_path(self.build_path_base(bucket, key))
        return url_base

    def build_host(self, server, bucket):
        if bucket == '':
            return server
        else:
            return self.get_bucket_server(server, bucket)

    def build_auth_path(self, bucket, key=''):
        key = boto.utils.get_utf8_value(key)
        path = ''
        if bucket != '':
            path = '/' + bucket
        return path + '/%s' % urllib.quote(key)

    def build_path_base(self, bucket, key=''):
        key = boto.utils.get_utf8_value(key)
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
        key = boto.utils.get_utf8_value(key)
        path_base = '/'
        if bucket:
            path_base += "%s/" % bucket
        return path_base + urllib.quote(key)


class ProtocolIndependentOrdinaryCallingFormat(OrdinaryCallingFormat):

    def build_url_base(self, connection, protocol, server, bucket, key=''):
        url_base = '//'
        url_base += self.build_host(server, bucket)
        url_base += connection.get_path(self.build_path_base(bucket, key))
        return url_base


class Location:

    DEFAULT = ''  # US Classic Region
    EU = 'EU'
    USWest = 'us-west-1'
    USWest2 = 'us-west-2'
    SAEast = 'sa-east-1'
    APNortheast = 'ap-northeast-1'
    APSoutheast = 'ap-southeast-1'


class S3Connection(AWSAuthConnection):

    DefaultHost = 's3.amazonaws.com'
    QueryString = 'Signature=%s&Expires=%d&AWSAccessKeyId=%s'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None,
                 host=DefaultHost, debug=0, https_connection_factory=None,
                 calling_format=SubdomainCallingFormat(), path='/',
                 provider='aws', bucket_class=Bucket, security_token=None,
                 suppress_consec_slashes=True, anon=False,
                 validate_certs=None):
        self.calling_format = calling_format
        self.bucket_class = bucket_class
        self.anon = anon
        AWSAuthConnection.__init__(self, host,
                aws_access_key_id, aws_secret_access_key,
                is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                debug=debug, https_connection_factory=https_connection_factory,
                path=path, provider=provider, security_token=security_token,
                suppress_consec_slashes=suppress_consec_slashes,
                validate_certs=validate_certs)

    def _required_auth_capability(self):
        if self.anon:
            return ['anon']
        else:
            return ['s3']

    def __iter__(self):
        for bucket in self.get_all_buckets():
            yield bucket

    def __contains__(self, bucket_name):
        return not (self.lookup(bucket_name) is None)

    def set_bucket_class(self, bucket_class):
        """
        Set the Bucket class associated with this bucket.  By default, this
        would be the boto.s3.key.Bucket class but if you want to subclass that
        for some reason this allows you to associate your new class.

        :type bucket_class: class
        :param bucket_class: A subclass of Bucket that can be more specific
        """
        self.bucket_class = bucket_class

    def build_post_policy(self, expiration_time, conditions):
        """
        Taken from the AWS book Python examples and modified for use with boto
        """
        assert isinstance(expiration_time, time.struct_time), \
            'Policy document must include a valid expiration Time object'

        # Convert conditions object mappings to condition statements

        return '{"expiration": "%s",\n"conditions": [%s]}' % \
            (time.strftime(boto.utils.ISO8601, expiration_time), ",".join(conditions))

    def build_post_form_args(self, bucket_name, key, expires_in = 6000,
                             acl = None, success_action_redirect = None,
                             max_content_length = None,
                             http_method = "http", fields=None,
                             conditions=None):
        """
        Taken from the AWS book Python examples and modified for use with boto
        This only returns the arguments required for the post form, not the
        actual form.  This does not return the file input field which also
        needs to be added

        :type bucket_name: string
        :param bucket_name: Bucket to submit to

        :type key: string
        :param key:  Key name, optionally add ${filename} to the end to
            attach the submitted filename

        :type expires_in: integer
        :param expires_in: Time (in seconds) before this expires, defaults
            to 6000

        :type acl: :class:`boto.s3.acl.ACL`
        :param acl: ACL rule to use, if any

        :type success_action_redirect: string
        :param success_action_redirect: URL to redirect to on success

        :type max_content_length: integer
        :param max_content_length: Maximum size for this file

        :type http_method: string
        :param http_method:  HTTP Method to use, "http" or "https"

        :rtype: dict
        :return: A dictionary containing field names/values as well as
            a url to POST to

            .. code-block:: python

                {
                    "action": action_url_to_post_to,
                    "fields": [
                        {
                            "name": field_name,
                            "value":  field_value
                        },
                        {
                            "name": field_name2,
                            "value": field_value2
                        }
                    ]
                }

        """
        if fields == None:
            fields = []
        if conditions == None:
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
        fields.append({"name": "AWSAccessKeyId",
                       "value": self.aws_access_key_id})

        # Add signature for encoded policy document as the 'AWSAccessKeyId' field
        signature = self._auth_handler.sign_string(policy_b64)
        fields.append({"name": "signature", "value": signature})
        fields.append({"name": "key", "value": key})

        # HTTPS protocol will be used if the secure HTTP option is enabled.
        url = '%s://%s/' % (http_method,
                            self.calling_format.build_host(self.server_name(),
                                                           bucket_name))

        return {"action": url, "fields": fields}

    def generate_url(self, expires_in, method, bucket='', key='', headers=None,
                     query_auth=True, force_http=False, response_headers=None,
                     expires_in_absolute=False, version_id=None):
        headers = headers or {}
        if expires_in_absolute:
            expires = int(expires_in)
        else:
            expires = int(time.time() + expires_in)
        auth_path = self.calling_format.build_auth_path(bucket, key)
        auth_path = self.get_path(auth_path)
        # optional version_id and response_headers need to be added to
        # the query param list.
        extra_qp = []
        if version_id is not None:
            extra_qp.append("versionId=%s" % version_id)
        if response_headers:
            for k, v in response_headers.items():
                extra_qp.append("%s=%s" % (k, urllib.quote(v)))
        if self.provider.security_token:
            headers['x-amz-security-token'] = self.provider.security_token
        if extra_qp:
            delimiter = '?' if '?' not in auth_path else '&'
            auth_path += delimiter + '&'.join(extra_qp)
        c_string = boto.utils.canonical_string(method, auth_path, headers,
                                               expires, self.provider)
        b64_hmac = self._auth_handler.sign_string(c_string)
        encoded_canonical = urllib.quote(b64_hmac, safe='')
        self.calling_format.build_path_base(bucket, key)
        if query_auth:
            query_part = '?' + self.QueryString % (encoded_canonical, expires,
                                                   self.aws_access_key_id)
        else:
            query_part = ''
        if headers:
            hdr_prefix = self.provider.header_prefix
            for k, v in headers.items():
                if k.startswith(hdr_prefix):
                    # headers used for sig generation must be
                    # included in the url also.
                    extra_qp.append("%s=%s" % (k, urllib.quote(v)))
        if extra_qp:
            delimiter = '?' if not query_part else '&'
            query_part += delimiter + '&'.join(extra_qp)
        if force_http:
            protocol = 'http'
            port = 80
        else:
            protocol = self.protocol
            port = self.port
        return self.calling_format.build_url_base(self, protocol,
                                                  self.server_name(port),
                                                  bucket, key) + query_part

    def get_all_buckets(self, headers=None):
        response = self.make_request('GET', headers=headers)
        body = response.read()
        if response.status > 300:
            raise self.provider.storage_response_error(
                response.status, response.reason, body)
        rs = ResultSet([('Bucket', self.bucket_class)])
        h = handler.XmlHandler(rs, self)
        xml.sax.parseString(body, h)
        return rs

    def get_canonical_user_id(self, headers=None):
        """
        Convenience method that returns the "CanonicalUserID" of the
        user who's credentials are associated with the connection.
        The only way to get this value is to do a GET request on the
        service which returns all buckets associated with the account.
        As part of that response, the canonical userid is returned.
        This method simply does all of that and then returns just the
        user id.

        :rtype: string
        :return: A string containing the canonical user id.
        """
        rs = self.get_all_buckets(headers=headers)
        return rs.owner.id

    def get_bucket(self, bucket_name, validate=True, headers=None):
        bucket = self.bucket_class(self, bucket_name)
        if validate:
            bucket.get_all_keys(headers, maxkeys=0)
        return bucket

    def lookup(self, bucket_name, validate=True, headers=None):
        try:
            bucket = self.get_bucket(bucket_name, validate, headers=headers)
        except:
            bucket = None
        return bucket

    def create_bucket(self, bucket_name, headers=None,
                      location=Location.DEFAULT, policy=None):
        """
        Creates a new located bucket. By default it's in the USA. You can pass
        Location.EU to create an European bucket.

        :type bucket_name: string
        :param bucket_name: The name of the new bucket

        :type headers: dict
        :param headers: Additional headers to pass along with the request to AWS.

        :type location: :class:`boto.s3.connection.Location`
        :param location: The location of the new bucket

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the
            new key in S3.

        """
        check_lowercase_bucketname(bucket_name)

        if policy:
            if headers:
                headers[self.provider.acl_header] = policy
            else:
                headers = {self.provider.acl_header: policy}
        if location == Location.DEFAULT:
            data = ''
        else:
            data = '<CreateBucketConfiguration><LocationConstraint>' + \
                    location + '</LocationConstraint></CreateBucketConfiguration>'
        response = self.make_request('PUT', bucket_name, headers=headers,
                data=data)
        body = response.read()
        if response.status == 409:
            raise self.provider.storage_create_error(
                response.status, response.reason, body)
        if response.status == 200:
            return self.bucket_class(self, bucket_name)
        else:
            raise self.provider.storage_response_error(
                response.status, response.reason, body)

    def delete_bucket(self, bucket, headers=None):
        response = self.make_request('DELETE', bucket, headers=headers)
        body = response.read()
        if response.status != 204:
            raise self.provider.storage_response_error(
                response.status, response.reason, body)

    def make_request(self, method, bucket='', key='', headers=None, data='',
            query_args=None, sender=None, override_num_retries=None):
        if isinstance(bucket, self.bucket_class):
            bucket = bucket.name
        if isinstance(key, Key):
            key = key.name
        path = self.calling_format.build_path_base(bucket, key)
        boto.log.debug('path=%s' % path)
        auth_path = self.calling_format.build_auth_path(bucket, key)
        boto.log.debug('auth_path=%s' % auth_path)
        host = self.calling_format.build_host(self.server_name(), bucket)
        if query_args:
            path += '?' + query_args
            boto.log.debug('path=%s' % path)
            auth_path += '?' + query_args
            boto.log.debug('auth_path=%s' % auth_path)
        return AWSAuthConnection.make_request(self, method, path, headers,
                data, host, auth_path, sender,
                override_num_retries=override_num_retries)
