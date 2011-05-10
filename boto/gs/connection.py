# Copyright 2010 Google Inc.
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

from boto.gs.bucket import Bucket            
from boto.s3.connection import S3Connection
from boto.s3.connection import SubdomainCallingFormat
from boto.s3.connection import check_lowercase_bucketname

class Location:
    DEFAULT = '' # US
    EU = 'EU'

class GSConnection(S3Connection):

    DefaultHost = 'commondatastorage.googleapis.com'
    QueryString = 'Signature=%s&Expires=%d&AWSAccessKeyId=%s'

    def __init__(self, gs_access_key_id=None, gs_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None,
                 host=DefaultHost, debug=0, https_connection_factory=None,
                 calling_format=SubdomainCallingFormat(), path='/'):
        S3Connection.__init__(self, gs_access_key_id, gs_secret_access_key,
                 is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                 host, debug, https_connection_factory, calling_format, path,
                 "google", Bucket)

    def create_bucket(self, bucket_name, headers=None,
                      location=Location.DEFAULT, policy=None):
        """
        Creates a new bucket. By default it's located in the USA. You can
        pass Location.EU to create an European bucket. You can also pass
        a LocationConstraint, which (in addition to locating the bucket
        in the specified location) informs Google that Google services
        must not copy data out of that location.

        :type bucket_name: string
        :param bucket_name: The name of the new bucket
        
        :type headers: dict
        :param headers: Additional headers to pass along with the request to AWS.

        :type location: :class:`boto.gs.connection.Location`
        :param location: The location of the new bucket

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the new key in S3.
             
        """
        check_lowercase_bucketname(bucket_name)

        if policy:
            if headers:
                headers[self.provider.acl_header] = policy
            else:
                headers = {self.provider.acl_header : policy}
        if not location:
            data = ''
        else:
            data = ('<CreateBucketConfiguration>'
                        '<LocationConstraint>%s</LocationConstraint>'
                    '</CreateBucketConfiguration>' % location)
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

