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
import boto.utils
import datetime
import threading

_session_token_cache = {}

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
        self._mutex = threading.Semaphore()
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
                                    proxy_user, proxy_pass,
                                    self.region.endpoint, debug,
                                    https_connection_factory, path)

    def _required_auth_capability(self):
        return ['sign-v2']

    def _check_token_cache(self, token_key, duration=None, window_seconds=60):
        token = _session_token_cache.get(token_key, None)
        if token:
            now = datetime.datetime.utcnow()
            expires = boto.utils.parse_ts(token.expiration)
            delta = expires - now
            if delta.total_seconds() < window_seconds:
                msg = 'Cached session token %s is expired' % token_key
                boto.log.debug(msg)
                token = None
        return token

    def _get_session_token(self, duration=None):
        params = {}
        if duration:
            params['DurationSeconds'] = duration
        return self.get_object('GetSessionToken', params,
                                Credentials, verb='POST')

    def get_session_token(self, duration=None, force_new=False):
        """
        Return a valid session token.  Because retrieving new tokens
        from the Secure Token Service is a fairly heavyweight operation
        this module caches previously retrieved tokens and returns
        them when appropriate.  Each token is cached with a key
        consisting of the region name of the STS endpoint
        concatenated with the requesting user's access id.  If there
        is a token in the cache meeting with this key, the session
        expiration is checked to make sure it is still valid and if
        so, the cached token is returned.  Otherwise, a new session
        token is requested from STS and it is placed into the cache
        and returned.

        :type duration: int
        :param duration: The number of seconds the credentials should
            remain valid.

        :type force_new: bool
        :param force_new: If this parameter is True, a new session token
            will be retrieved from the Secure Token Service regardless
            of whether there is a valid cached token or not.
        """
        token_key = '%s:%s' % (self.region.name, self.provider.access_key)
        token = self._check_token_cache(token_key, duration)
        if force_new or not token:
            boto.log.debug('fetching a new token for %s' % token_key)
            self._mutex.acquire()
            token = self._get_session_token(duration)
            _session_token_cache[token_key] = token
            self._mutex.release()
        return token
        
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
            params['DurationSeconds'] = duration
        if policy:
            params['Policy'] = policy
        return self.get_object('GetFederationToken', params,
                                FederationToken, verb='POST')
        
        
