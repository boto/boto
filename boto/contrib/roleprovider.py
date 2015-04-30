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

import datetime

import boto.utils
import boto.provider
import boto.sts

"""
This module provides a derivative of the Provider class that leverages the 
temporary credential management and auto-renewal code of that class to manage 
temporary credentials from an assumed AWS iam role.

To use, create a RoleProvider using your role urn, and then pass it into any 
Boto connect method or Connection object constructor via the provider parameter.

This is useful for quickly converting legacy scripts to use cross-account
resources which require a role to be assumed before use by just changing a
couple of lines at the start of the script.

E.g. Convert a script that does:

      r53conn = Route53Connection()
      <load of stuff using r53conn>

by just changing a couple of lines:

      from boto.contrib.roleprovider import RoleProvider

      my_provider = RoleProvider(my_cross_account_access_role)
      r53conn = Route53Connection(provider=my_provider)
      <load of stuff using r53conn>

"""

class RoleProvider(boto.provider.Provider):
    """
    :ivar role: The role to assume
    """

    def __init__(self, role, access_key=None, secret_key=None,
                 security_token=None, profile_name=None):
        self._role = role
        try:
            self._rolename = role.split('/')[1]
        except:
            self._rolename = role
        boto.provider.Provider.__init__(self, 'aws', access_key=access_key, secret_key=secret_key, security_token=security_token, profile_name=profile_name)

    def _populate_keys_from_metadata_server(self):
        boto.log.debug("Retrieveing role keys")
        stsconn = boto.sts.connect_to_region('us-east-1')
        creds = stsconn.assume_role(self._role, self._rolename)
        self._access_key = creds.credentials.access_key
        self._secret_key = self._convert_key_to_str(creds.credentials.secret_key)
        self._security_token = creds.credentials.session_token
        ts = boto.utils.parse_ts(creds.credentials.expiration)
        self._credential_expiry_time = ts


