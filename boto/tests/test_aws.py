#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Copyright (c) 2008 Fabien Schwob http://fabien.schwob.org
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

"""
Some unit tests for the AWS
"""

import unittest
import pmock
import StringIO
import os

from boto.tests.aws_data import item_search_response_xml

from boto.aws.connection import AWSConnection
from boto.aws.item import Item

class AWSConnectionTest(unittest.TestCase):

    def setUp(self):
        self.AccessKeyID = os.environ['AWS_ACCESS_KEY_ID']
        self.AssociateTag = os.environ['AWS_ASSOCIATE_TAG']
        
    def test_connection(self):
        connection = AWSConnection(self.AccessKeyID, self.AssociateTag)
        self.assertEqual(connection.AccessKeyID, self.AccessKeyID)
        self.assertEqual(connection.AssociateTag, self.AssociateTag)
    
    def test_ItemSearch(self):
        connection = AWSConnection(self.AccessKeyID, self.AssociateTag)
        
        # Mock object for urllib
        import urllib
        mock = pmock.Mock()
        mock.expects(pmock.once()).method("urlopen").will(pmock.return_value(StringIO.StringIO(item_search_response_xml)))
        urllib.urlopen = mock.urlopen
        
        result = connection.ItemSearch("Harry Potter", index="Books")
        
        self.assertEqual(len(result.items), 10)
        
        for item in result.items:
            self.assertNotEqual(item.ASIN, None)
        
        first_item = result.items[0]
        self.assertEqual(first_item.ASIN, "0545010225")
        self.assertEqual(first_item.DetailPageURL, "http://www.amazon.com/gp/redirect.html%3FASIN=0545010225%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0545010225%253FSubscriptionId=06Z1EY48VX81JPFG3082")
        self.assertEqual(first_item.ItemAttributes['Author'], u"J. K. Rowling")
        self.assertEqual(first_item.ItemAttributes['Creator'], u"Mary GrandPré")
        self.assertEqual(first_item.ItemAttributes['Manufacturer'], u"Arthur A. Levine Books")
        self.assertEqual(first_item.ItemAttributes['ProductGroup'], u"Book")
        self.assertEqual(first_item.ItemAttributes['Title'], u"Harry Potter and the Deathly Hallows (Book 7)")
        
        third_item = result.items[2]
        self.assertEqual(third_item.ASIN, "0439785960")
        self.assertEqual(third_item.DetailPageURL, "http://www.amazon.com/gp/redirect.html%3FASIN=0439785960%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0439785960%253FSubscriptionId=06Z1EY48VX81JPFG3082")
        self.assertEqual(third_item.ItemAttributes['Author'], u"J.K. Rowling")
        self.assertEqual(third_item.ItemAttributes['Creator'], u"Mary GrandPré")
        self.assertEqual(third_item.ItemAttributes['Manufacturer'], u"Scholastic Paperbacks")
        self.assertEqual(third_item.ItemAttributes['ProductGroup'], u"Book")
        self.assertEqual(third_item.ItemAttributes['Title'], u"Harry Potter and the Half-Blood Prince (Book 6)")

if __name__ == '__main__':
    unittest.main()

