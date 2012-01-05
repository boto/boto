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

class Credentials(object):
    """
    :ivar access_key: The AccessKeyID.
    :ivar secret_key: The SecretAccessKey.
    :ivar session_token: The session token that must be passed with
                         requests to use the temporary credentials
    :ivar expiration: The timestamp for when the credentials will expire
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.access_key = None
        self.secret_key = None
        self.session_token = None
        self.expiration = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'AccessKeyId':
            self.access_key = value
        elif name == 'SecretAccessKey':
            self.secret_key = value
        elif name == 'SessionToken':
            self.session_token = value
        elif name == 'Expiration':
            self.expiration = value
        elif name == 'RequestId':
            self.request_id = value
        else:
            pass
    
class FederationToken(object):
    """
    :ivar credentials: A Credentials object containing the credentials.
    :ivar federated_user_arn: ARN specifying federated user using credentials.
    :ivar federated_user_id: The ID of the federated user using credentials.
    :ivar packed_policy_size: A percentage value indicating the size of
                             the policy in packed form
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.credentials = None
        self.federated_user_arn = None
        self.federated_user_id = None
        self.packed_policy_size = None

    def startElement(self, name, attrs, connection):
        if name == 'Credentials':
            self.credentials = Credentials()
            return self.credentials
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'Arn':
            self.federated_user_arn = value
        elif name == 'FederatedUserId':
            self.federated_user_id = value
        elif name == 'PackedPolicySize':
            self.packed_policy_size = int(value)
        elif name == 'RequestId':
            self.request_id = value
        else:
            pass
        
