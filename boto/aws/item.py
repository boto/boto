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

from lxml import etree

from boto.aws import AMAZON_NAMESPACE

class Item(object):
    """
    """
    
    def __init__(self):
        """
        """
        self.ASIN = None
        self.DetailPageURL = None
        self.ItemAttributes = {}

    @staticmethod
    def normalize(name):
        """
        Return the name of a tag without it namespace
        """
        if name[0] == "{":
            uri, tag = name[1:].split("}")
            return tag
        else:
            return name

    @staticmethod
    def fromXML(xml):
        """
        Create an Item from an etree.Element.
        """
        if not isinstance(xml, etree._Element):
            raise TypeError("Item.fromXML expect an etree.Element instance")
            
        item = Item()
        for element in xml:
            tag_name = Item.normalize(element.tag)
            if len(element) > 0:
                for attributes in element:
                    item.ItemAttributes[Item.normalize(attributes.tag)] = attributes.text.strip()
            else:
                setattr(item, tag_name, element.text.strip())
        return item

    def __str__(self):
        return "<%s: ASIN: %s>" % ( self.__class__.__name__, self.ASIN)

