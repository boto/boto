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

from boto.connection import AWSQueryConnection
from boto.regioninfo import RegionInfo
from credentials import Credentials, FederationToken
import boto

class STSConnection(AWSQueryConnection):

    DefaultRegionName = 'us-east-1'
    DefaultRegionEndpoint = 'sts.amazonaws.com'
    APIVersion = '2011-06-15'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None, path='/',
                 converter=None):
        if not region:
            region = RegionInfo(self, self.DefaultRegionName,
                                self.DefaultRegionEndpoint,
                                connection_cls=STSConnection)
        self.region = region
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
                                    proxy_user, proxy_pass,
                                    self.region.endpoint, debug,
                                    https_connection_factory, path)

    def _required_auth_capability(self):
        return ['sign-v2']

    def get_session_token(self, duration=None):
        """
        :type duration: int
        :param duration: The number of seconds the credentials should
                         remain valid.

        """
        params = {}
        if duration:
            params['Duration'] = duration
        return self.get_object('GetSessionToken', params,
                                Credentials, verb='POST')
        
        
    def get_federation_token(self, name, duration=None, policy=None):
        """
        :type name: str
        :param name: The name of the Federated user associated with
                     the credentials.
                     
        :type duration: int
        :param duration: The number of seconds the credentials should
                         remain valid.

        :type policy: str
        :param policy: A JSON policy to associate with these credentials.

        """
        params = {'Name' : name}
        if duration:
            params['Duration'] = duration
        if policy:
            params['Policy'] = policy
        return self.get_object('GetFederationToken', params,
                                FederationToken, verb='POST')
        
        
