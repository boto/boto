# Copyright (c) 2010 Alon Swartz <alon@turnkeylinux.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# Implements AWS DevPay License API:
# http://docs.amazonwebservices.com/AmazonDevPay/latest/DevPayDeveloperGuide/LSAPI.html

import xml.sax

from boto import handler
from boto.connection import AWSQueryConnection
from boto.exception import BotoServerError

class LicenseConn:
    """Super class to handle making request and setting responses"""

    DEFAULT_HOST = "ls.amazonaws.com"
    API_VERSION = "2008-04-28"
    ResponseError = BotoServerError

    def __init__(self):
        self.action = None
        self.auth_accesskey = None
        self.auth_secretkey = None

    def _make_request(self, params, debug=False):
        self._cleanupParsedProperties()
        conn = AWSQueryConnection(host=self.DEFAULT_HOST,
                                  aws_access_key_id=self.auth_accesskey,
                                  aws_secret_access_key=self.auth_secretkey)

        conn.APIVersion = self.API_VERSION

        response = conn.make_request(self.action, params=params)
        body = response.read()

        if debug:
            print body

        if not response.status == 200:
            raise self.ResponseError(response.status, response.reason, body)

        h = handler.XmlHandler(self, self)
        xml.sax.parseString(body, h)

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        return None

    def _cleanupParsedProperties(self):
        pass

class ActivateDesktopProduct(LicenseConn):
    def __init__(self, producttoken):
        """Activate Desktop DevPay product

        Usage:
            product = ActivateDesktopProduct(producttoken)
            product.activate(activationkey)

            print product.usertoken
            print product.accesskey
            print product.secretkey

            OR

            usertoken, accesskey, secretkey = product.activate(activationkey)

        Errors:
            ExpiredActivationKey    Expired key, lifespan is one hour after creation.
            IncorrectActivationKey  Key does not correspond to the product token.
            InvalidActivationKey    Key is invalid or malformed.
            InvalidProductToken     The product token is invalid for the signer.

        """
        self.action = "ActivateDesktopProduct"

        self.producttoken = producttoken
        self.usertoken = None

        # ugly hack to fake awsauth (so as not to re-implement AWSAuthConnection)
        self.auth_accesskey = "1"
        self.auth_secretkey = "1"

    def activate(self, activationkey, tokenexpiration=None):
        """activate product specified by producttoken using activationkey

            tokenexpiration     Lifespan (in seconds) for returned usertoken

        returns:

            usertoken, accesskey, secretkey

        """
        params = {'ActivationKey': activationkey, 'ProductToken': self.producttoken}
        if tokenexpiration:
            params['TokenExpiration'] = tokenexpiration

        self._make_request(params)

        return self.usertoken, self.accesskey, self.secretkey

    def endElement(self, name, value, connection):
        if name == "UserToken":
            self.usertoken = value
        elif name == "AWSAccessKeyId":
            self.accesskey = value
        elif name == "SecretAccessKey":
            self.secretkey = value
        return None

    def _cleanupParsedProperties(self):
        self.usertoken = None
        self.accesskey = None
        self.secretkey = None

class ActivateHostedProduct(LicenseConn):
    def __init__(self, producttoken, owner_accesskey, owner_secretkey):
        """Activate Hosted DevPay product

        Usage:
            product = ActivateHostedProduct(producttoken, accesskey, secretkey)
            product.activate(activationkey)

            print product.usertoken
            print product.persistentid

            OR

            usertoken, persistentid = product.activate(activationkey)

        Errors:
            ExpiredActivationKey    Expired key, lifespan is one hour after creation.
            IncorrectActivationKey  Key does not correspond to the product token.
            InvalidActivationKey    Key is invalid or malformed.
            InvalidProductToken     The product token is invalid for the signer.

        Notes:
            access and secret keys are those belonging to the *product owner*,
            not the customer

        """
        self.action = "ActivateHostedProduct"

        self.producttoken = producttoken
        self.auth_accesskey = owner_accesskey
        self.auth_secretkey = owner_secretkey

        self.usertoken = None
        self.persistentid = None

    def activate(self, activationkey, tokenexpiration=None):
        """activate product specified by producttoken using activationkey

            tokenexpiration     Lifespan (in seconds) for returned usertoken

        returns:

            usertoken, persistentid

        """
        params = {'ActivationKey': activationkey, 'ProductToken': self.producttoken}
        if tokenexpiration:
            params['TokenExpiration'] = tokenexpiration

        self._make_request(params)

        return self.usertoken, self.persistentid

    def endElement(self, name, value, connection):
        if name == "UserToken":
            self.usertoken = value
        elif name == "PersistentIdentifier":
            self.persistentid = value
        return None

    def _cleanupParsedProperties(self):
        self.usertoken = None
        self.persistentid = None

class GetActiveSubscriptionsByPid(LicenseConn):
    def __init__(self, owner_accesskey, owner_secretkey):
        """Get list of active productcodes PID is subscribed to

        Usage:
            subscriptions = GetActiveSubscriptionsByPid(owner_accesskey,
                                                        owner_secretkey)
            subscriptions.get(persistentid)

            print subscriptions.productcodes:

            OR

            productcodes = subscriptions.get(persistentid)

        Notes:
            access and secret keys are those belonging to the *product owner*,
            not the customer

        Errors:
            InvalidPersistentIdentifier     Invalid or malformed PID

        """
        self.action = "GetActiveSubscriptionsByPid"

        self.auth_accesskey = owner_accesskey
        self.auth_secretkey = owner_secretkey

        self.productcodes = []

    def get(self, persistentid):
        """returns list of product codes"""
        params = {'PersistentIdentifier': persistentid}
        self._make_request(params)

        return self.productcodes

    def endElement(self, name, value, connection):
        if name == "ProductCode":
            self.productcodes.append(value)
        return None

    def _cleanupParsedProperties(self):
        self.productcodes = []

class VerifySubscription(LicenseConn):
    """class to handle verify subscription response"""

    @staticmethod
    def _get_bool(s):
        if s.lower() == "true":
            return True
        return False

    def endElement(self, name, value, connection):
        if name == "Subscribed":
            self.subscribed = self._get_bool(value)
        return None

    def _cleanupParsedProperties(self):
        self.subscribed = None

class VerifyProductSubscriptionByPid(VerifySubscription):
    def __init__(self, productcode, owner_accesskey, owner_secretkey):
        """Verify PID is subscribed to DevPay product

        Usage:
            subscription = VerifyProductSubscriptionByPid(productcode, 
                                                          accesskey, secretkey)
            subscription.verify(persistentid)
            print subscription.subscribed

            OR

            subscribed = subscription.verify(persistentid)

        Notes:
            access and secret keys are those belonging to the *product owner*,
            not the customer

        Errors:
            InvalidProductToken     The product token is invalid for the signer.
            InvalidParameterValue   Missing or invalid parameter(s)

        """
        self.action = "VerifyProductSubscriptionByPid"

        self.productcode = productcode
        self.auth_accesskey = owner_accesskey
        self.auth_secretkey = owner_secretkey

        self.subscribed = None

    def verify(self, persistentid):
        """returns boolean whether subscribed or not"""
        params = {'PersistentIdentifier': persistentid, 'ProductCode': self.productcode}
        self._make_request(params)

        return self.subscribed

class VerifyProductSubscriptionByTokens(VerifySubscription):
    def __init__(self, producttoken):
        """Verify usertoken is subscribed to DevPay product

        Usage:
            subscription = VerifyProductSubscriptionByTokens(producttoken)

            subscription.verify(usertoken, accesskey, secretkey)
            print subscription.subscribed

            OR

            subscribed = subscription.verify(usertoken, accesskey, secretkey)

        Notes:
            access and secret keys are those belonging to the *customer*,
            not the owner

            the usertoken must be received from ActivateDesktopProduct

        Errors:
            InvalidProductToken     The product token is invalid for the signer.
            InvalidParameterValue   Missing or invalid parameter(s)

        """
        self.action = "VerifyProductSubscriptionByTokens"

        self.producttoken = producttoken
        self.subscribed = None

    def verify(self, usertoken, customer_accesskey, customer_secretkey):
        """returns boolean whether subscribed or not"""
        self.auth_accesskey = customer_accesskey
        self.auth_secretkey = customer_secretkey

        params = {'ProductToken': self.producttoken, 'UserToken': usertoken}
        self._make_request(params)

        return self.subscribed

class RefreshUserToken(LicenseConn):
    def __init__(self, producttoken):
        """Refresh DevPay product user token

        Usage:
            newusertoken = RefreshUserToken(producttoken)
            newusertoken.refresh(usertoken, accesskey, secretkey)

            print newusertoken.usertoken

            OR

            usertoken = newusertoken.refresh(usertoken, accesskey, secretkey)

        Notes:
            access and secret keys are those belonging to the *customer*, 
            not the product owner

            the usertoken must be received from ActivateDesktopProduct

        Errors:
            InvalidProductToken     The product token is invalid for the signer.
            InvalidParameterValue   Missing or invalid parameter(s)

        """
        self.action = "RefreshUserToken"

        self.producttoken = producttoken
        self.usertoken = None

    def refresh(self, usertoken, customer_accesskey, customer_secretkey):
        """returns new usertoken"""
        self.auth_accesskey = customer_accesskey
        self.auth_secretkey = customer_secretkey

        params = {'AdditionalTokens': self.producttoken, 'UserToken': usertoken}
        self._make_request(params)

        return self.usertoken

    def endElement(self, name, value, connection):
        if name == "UserToken":
            self.usertoken = value
        return None

    def _cleanupParsedProperties(self):
        self.usertoken = None

