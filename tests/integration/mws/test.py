#!/usr/bin/env python
from tests.unit import unittest
import sys
import os
import os.path


simple = os.environ.get('MWS_MERCHANT', None)
if not simple:
    print """
        Please set the MWS_MERCHANT environmental variable
        to your Merchant or SellerId to enable MWS tests.
    """


advanced = False
isolator = True
if __name__ == "__main__":
    devpath = os.path.relpath(os.path.join('..', '..'),
                              start=os.path.dirname(__file__))
    sys.path = [devpath] + sys.path
    advanced = simple and True or False
    if advanced:
        print '>>> advanced MWS tests; using local boto sources'

from boto.mws.connection import MWSConnection


class MWSTestCase(unittest.TestCase):

    def setUp(self):
        self.mws = MWSConnection(Merchant=simple, debug=0)

    @unittest.skipUnless(simple and isolator, "skipping simple test")
    def test_feedlist(self):
        self.mws.get_feed_submission_list()

    @unittest.skipUnless(simple and isolator, "skipping simple test")
    def test_inbound_status(self):
        response = self.mws.get_inbound_service_status()
        status = response.GetServiceStatusResult.Status
        self.assertIn(status, ('GREEN', 'GREEN_I', 'YELLOW', 'RED'))

    @property
    def marketplace(self):
        response = self.mws.list_marketplace_participations()
        result = response.ListMarketplaceParticipationsResult
        return result.ListMarketplaces.Marketplace[0]

    @property
    def marketplace_id(self):
        return self.marketplace.MarketplaceId

    @unittest.skipUnless(simple and isolator, "skipping simple test")
    def test_marketplace_participations(self):
        response = self.mws.list_marketplace_participations()
        result = response.ListMarketplaceParticipationsResult
        self.assertTrue(result.ListMarketplaces.Marketplace[0].MarketplaceId)

    @unittest.skipUnless(simple and isolator, "skipping simple test")
    def test_get_product_categories_for_asin(self):
        asin = '144930544X'
        response = self.mws.get_product_categories_for_asin(\
            MarketplaceId=self.marketplace_id,
            ASIN=asin)
        result = response._result
        self.assertTrue(int(result.Self.ProductCategoryId) == 21)

    @unittest.skipUnless(simple and isolator, "skipping simple test")
    def test_list_matching_products(self):
        response = self.mws.list_matching_products(\
            MarketplaceId=self.marketplace_id,
            Query='boto')
        products = response._result.Products
        self.assertTrue(len(products))

    @unittest.skipUnless(simple and isolator, "skipping simple test")
    def test_get_matching_product(self):
        asin = 'B001UDRNHO'
        response = self.mws.get_matching_product(\
            MarketplaceId=self.marketplace_id,
            ASINList=[asin,])
        product = response._result[0].Product


    @unittest.skipUnless(simple and isolator, "skipping simple test")
    def test_get_lowest_offer_listings_for_asin(self):
        asin = '144930544X'
        response = self.mws.get_lowest_offer_listings_for_asin(\
            MarketplaceId=self.marketplace_id,
            ItemCondition='New',
            ASINList=[asin,])
        product = response._result[0].Product
        self.assertTrue(product.LowestOfferListings)

if __name__ == "__main__":
    unittest.main()
