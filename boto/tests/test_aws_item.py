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
from lxml import etree
from boto.aws.item import Item
from boto.tests.aws_data import item_xml_snippets1, item_xml_snippets2

class ItemTest(unittest.TestCase):
        
    def test_fromXML(self):
        
        item = Item.fromXML(item_xml_snippets1)
        self.assertEqual(item.ASIN, "0545010225")
        self.assertEqual(item.DetailPageURL, "http://www.amazon.com/gp/redirect.html%3FASIN=0545010225%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0545010225%253FSubscriptionId=06Z1EY48VX81JPFG3082")
        self.assertEqual(item.ItemAttributes['Author'], u"J. K. Rowling")
        self.assertEqual(item.ItemAttributes['Creator'], u"Mary GrandPré")
        self.assertEqual(item.ItemAttributes['Manufacturer'], u"Arthur A. Levine Books")
        self.assertEqual(item.ItemAttributes['ProductGroup'], u"Book")
        self.assertEqual(item.ItemAttributes['Title'], u"Harry Potter and the Deathly Hallows (Book 7)")
        
        
        item = Item.fromXML(item_xml_snippets2)
        self.assertEqual(item.ASIN, "0321503619")
        self.assertEqual(item.DetailPageURL, "http://www.amazon.com/gp/redirect.html%3FASIN=0321503619%26tag=ws%26lcode=xm2%26cID=2025%26ccmID=165953%26location=/o/ASIN/0321503619%253FSubscriptionId=06Z1EY48VX81JPFG3082")
        self.assertEqual(item.ItemAttributes['Author'], u"Aaron Hillegass")
        self.assertEqual(item.ItemAttributes['Manufacturer'], u"Addison-Wesley Professional")
        self.assertEqual(item.ItemAttributes['ProductGroup'], u"Book")
        self.assertEqual(item.ItemAttributes['Title'], u"Cocoa® Programming for Mac® OS X (3rd Edition)")
    
    def test_fromXML_errors(self):
        self.assertRaises(TypeError, Item.fromXML, etree.tostring(item_xml_snippets1))

    def test___init__(self):
        item = Item()
        self.assertEqual(item.ASIN, None)
        self.assertEqual(item.DetailPageURL, None)
        self.assertEqual(item.ItemAttributes, {})
        
        
        
        

if __name__ == '__main__':
    unittest.main()

