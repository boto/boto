#!/usr/bin/python
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
"""
Required environmental variables

    ACTIVATION_KEY          - (Customer) Obtained during purchase

    PRODUCT_CODE            - (Owner) Obtained during product registration
    PRODUCT_TOKEN           - (Owner) Obtained during product registration
    AWS_ACCESS_KEY_ID       - (Owner) AWS Access Key of product owner
    AWS_SECRET_ACCESS_KEY   - (Owner) AWS Secret Access Key of product owner

"""
import os
import sys

from boto.license.actions import *

def fatal(e):
    print >> sys.stderr, "error: " + str(e)
    print >> sys.stderr, __doc__.strip()
    sys.exit(1)

def _getenv(s):
    val = os.getenv(s, None)
    if not val:
        fatal('%s is not set' % s)

    return val

def main():
    ACTIVATION_KEY = _getenv('ACTIVATION_KEY')
    PRODUCT_CODE = _getenv('PRODUCT_CODE')
    PRODUCT_TOKEN = _getenv('PRODUCT_TOKEN')
    ACCESSKEY = _getenv('AWS_ACCESS_KEY_ID')
    SECRETKEY = _getenv('AWS_SECRET_ACCESS_KEY')

    auth_owner = [ACCESSKEY, SECRETKEY]

    print "== Test: ActivateDesktopProduct"
    product = ActivateDesktopProduct(PRODUCT_TOKEN)
    product.activate(ACTIVATION_KEY)
    auth_customer = [product.accesskey, product.secretkey]
    usertoken_desktop = product.usertoken
    print product.usertoken[:50] + "..."
    print product.accesskey
    print product.secretkey
    print

    print "== Test: ActivateHostedProduct"
    product = ActivateHostedProduct(PRODUCT_TOKEN, *auth_owner)
    product.activate(ACTIVATION_KEY)
    usertoken_hosted = product.usertoken
    persistentid = product.persistentid
    print product.usertoken[:50] + "..."
    print product.persistentid
    print

    print "== Test: GetActiveSubscriptionsByPid"
    subscriptions = GetActiveSubscriptionsByPid(*auth_owner)
    subscriptions.get(persistentid)
    print subscriptions.productcodes
    print

    print "== Test: VerifyProductSubscriptionsByPid"
    subscription = VerifyProductSubscriptionByPid(PRODUCT_CODE, *auth_owner)
    subscription.verify(persistentid)
    print subscription.subscribed
    print

    print "== Test: VerifyProductSubscriptionByTokens"
    subscription = VerifyProductSubscriptionByTokens(PRODUCT_TOKEN)
    subscription.verify(usertoken_desktop, *auth_customer)
    print subscription.subscribed
    print

    print "== Test: RefreshUserToken"
    newusertoken = RefreshUserToken(PRODUCT_TOKEN)
    newusertoken.refresh(usertoken_desktop, *auth_customer)
    print newusertoken.usertoken[:50] + "..."
    print

if __name__ == "__main__":
    main()

