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
from credentials import Credentials, FederationToken, AssumedRole
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
                 converter=None, validate_certs=True):
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
                                    https_connection_factory, path,
                                    validate_certs=validate_certs)

    def _required_auth_capability(self):
        return ['sign-v2']

    def _check_token_cache(self, token_key, duration=None, window_seconds=60):
        token = _session_token_cache.get(token_key, None)
        if token:
            now = datetime.datetime.utcnow()
            expires = boto.utils.parse_ts(token.expiration)
            delta = expires - now
            if delta < datetime.timedelta(seconds=window_seconds):
                msg = 'Cached session token %s is expired' % token_key
                boto.log.debug(msg)
                token = None
        return token

    def _get_session_token(self, duration=None,
                           mfa_serial_number=None, mfa_token=None):
        params = {}
        if duration:
            params['DurationSeconds'] = duration
        if mfa_serial_number:
            params['SerialNumber'] = mfa_serial_number
        if mfa_token:
            params['TokenCode'] = mfa_token
        return self.get_object('GetSessionToken', params,
                                Credentials, verb='POST')

    def get_session_token(self, duration=None, force_new=False,
                          mfa_serial_number=None, mfa_token=None):
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

        :type mfa_serial_number: str
        :param mfa_serial_number: The serial number of an MFA device.
            If this is provided and if the mfa_passcode provided is
            valid, the temporary session token will be authorized with
            to perform operations requiring the MFA device authentication.

        :type mfa_token: str
        :param mfa_token: The 6 digit token associated with the
            MFA device.
        """
        token_key = '%s:%s' % (self.region.name, self.provider.access_key)
        token = self._check_token_cache(token_key, duration)
        if force_new or not token:
            boto.log.debug('fetching a new token for %s' % token_key)
            try:
                self._mutex.acquire()
                token = self._get_session_token(duration,
                                                mfa_serial_number,
                                                mfa_token)
                _session_token_cache[token_key] = token
            finally:
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
        params = {'Name': name}
        if duration:
            params['DurationSeconds'] = duration
        if policy:
            params['Policy'] = policy
        return self.get_object('GetFederationToken', params,
                                FederationToken, verb='POST')

    def assume_role(self, role_arn, role_session_name, policy=None,
                    duration_seconds=None, unique_client_id=None):
        """
        Returns a set of temporary credentials that the caller can use to
        access resources that are allowed by the temporary credentials.  The
        credentials are valid for the duration that the caller specified, which
        can be from 1 to 36 hours.

        :type role_arn: str
        :param role_arn: The Amazon Resource Name (ARN) of the role that the
            caller is assuming.

        :type role_session_name: str
        :param role_session_name: The session name of the temporary security
            credentials. The session name is part of the AssumedRoleUser.

        :type policy: str
        :param policy: A supplemental policy that can be associated with the
            temporary security credentials. The caller can limit the
            permissions that are available on the role's temporary security
            credentials to maintain the least amount of privileges.  When a
            service call is made with the temporary security credentials, both
            policies (the role policy and supplemental policy) are checked.


        :type duration_seconds: int
        :param duration_seconds: he duration, in seconds, of the role session.
            The value can range from 3600 seconds (one hour) to 129600 seconds
            (36 hours).  By default, the value is set to 43200 seconds (12
            hours).

        :type unique_client_id: str
        :param unique_client_id: A unique identifier that is used by
            third-party services to ensure that they are assuming a role that
            corresponds to the correct users. For third-party services that
            have access to resources across multiple AWS accounts, the unique
            client ID helps third-party services simplify access control
            verification.

        :return: An instance of :class:`boto.sts.credentials.AssumedRole`

        """
        params = {
            'RoleArn': role_arn,
            'RoleSessionName': role_session_name
        }
        if policy is not None:
            params['Policy'] = policy
        if duration_seconds is not None:
            params['DurationSeconds'] = duration_seconds
        if unique_client_id is not None:
            params['UniqueClientId'] = unique_client_id
        return self.get_object('AssumeRole', params, AssumedRole, verb='POST')
