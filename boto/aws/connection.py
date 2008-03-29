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

from boto.aws.result import SearchResult
from boto.aws.item import Item
from boto.aws import AMAZON_NAMESPACE

from lxml import etree
import urllib

class AWSConnection(object):

    base_url = "http://ecs.amazonaws.com/onca/xml?%s"

    def __init__(self, AccessKeyID, AssociateTag):
        """
        Initialize the AWSConnection with the user AccessKeyID and his
        AssociateTag
        """
        self.AccessKeyID = AccessKeyID
        self.AssociateTag = AssociateTag
    
    def ItemSearch(self, query, index):
        """
        Search in the given index, all the items for the query passed as
        first parameter.
        """
        parameters = {
            "Service":"AWSECommerceService",
            "AWSAccessKeyId":self.AccessKeyID,
            "Operation":"ItemSearch",
            "SearchIndex":index,
            "Title":urllib.quote(query),
            "AssociateTag":self.AssociateTag,
            "Version":"2008-03-03"
        }
        handler = urllib.urlopen(self.base_url % urllib.urlencode(parameters))
        return self._ItemSearchFromHandler(handler)
        
    
    def _ItemSearchFromHandler(self, handler):
        tree = etree.parse(handler)

        items = tree.xpath("/amazon:ItemSearchResponse/amazon:Items/amazon:Item",
                           namespaces={'amazon':AMAZON_NAMESPACE})


        result = SearchResult()
        result.items = [Item.fromXML(item) for item in items]
        return result

    def ItemLookup(self, item_id):
        
        parameters = {
            "Service":"AWSECommerceService",
            "AWSAccessKeyId":self.AccessKeyID,
            "Operation":"ItemLookup",
            "AssociateTag":self.AssociateTag,
            "ItemId":item_id,
            "Version":"2008-03-03"
        }
        handler = urllib.urlopen(self.base_url % urllib.urlencode(parameters))
        return self._ItemLookupFromHandler(handler)
    
    def _ItemLookupFromHandler(self, handler):
        tree = etree.parse(handler)

        xml_item = tree.xpath("/amazon:ItemLookupResponse/amazon:Items/amazon:Item",
                              namespaces={'amazon':AMAZON_NAMESPACE})

        item = Item.fromXML(xml_item[0])
        return item
    
    def SimilarityLookup(self, item_id):
        parameters = {
            "Service":"AWSECommerceService",
            "AWSAccessKeyId":self.AccessKeyID,
            "Operation":"SimilarityLookup",
            "ItemId":item_id,
            "Version":"2008-03-03"
        }
        f = urllib.urlopen(self.base_url % urllib.urlencode(parameters))
        
        print f.read()