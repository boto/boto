# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
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
Represents an SDB Domain
"""
from boto.sdb.queryresultset import QueryResultSet
from boto.sdb.item import Item

class Domain:
    
    def __init__(self, connection=None, name=None):
        self.connection = connection
        self.name = name
        self._metadata = None

    def __repr__(self):
        return 'Domain:%s' % self.name

    def __iter__(self):
        return iter(QueryResultSet(self))

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'DomainName':
            self.name = value
        else:
            setattr(self, name, value)

    def get_metadata(self):
        if not self._metadata:
            self._metadata = self.connection.domain_metadata(self)
        return self._metadata
    
    def put_attributes(self, item_name, attributes, replace=True):
        return self.connection.put_attributes(self, item_name, attributes, replace)

    def get_attributes(self, item_name, attribute_name=None, item=None):
        return self.connection.get_attributes(self, item_name, attribute_name, item)

    def delete_attributes(self, item_name, attributes=None):
        return self.connection.delete_attributes(self, item_name, attributes)

    def query(self, query='', max_items=None, attr_names=None):
        """
        Returns a list of items within domain that match the query.
        
        @type query: string
        @param query: The SimpleDB query to be performed.

        @type max_items: int
        @param max_items: The maximum number of items to return.  If not
                          supplied, the default is None which returns all
                          items matching the query.

        @type attr_names: list
        @param attr_names: Either None, meaning return all attributes
                           or a list of attribute names which means to return
                           only those attributes.

        @rtype: iter
        @return: An iterator containing the results.  This is actually a generator
                 function that will iterate across all search results, not just the
                 first page.
        """
        return iter(QueryResultSet(self, query, max_items, attr_names))
    
    def get_item(self, item_name):
        item = self.get_attributes(item_name)
        if item:
            item.domain = self
            return item
        else:
            return None

    def new_item(self, item_name):
        return Item(self, item_name)

    def delete_item(self, item):
        self.delete_attributes(item.name)

class DomainMetaData:
    
    def __init__(self, domain=None):
        self.domain = domain
        self.item_count = None
        self.item_names_size = None
        self.attr_name_count = None
        self.attr_names_size = None
        self.attr_value_count = None
        self.attr_values_size = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'ItemCount':
            self.item_count = int(value)
        elif name == 'ItemNamesSizeBytes':
            self.item_names_size = int(value)
        elif name == 'AttributeNameCount':
            self.attr_name_count = int(value)
        elif name == 'AttributeNamesSizeBytes':
            self.attr_names_size = int(value)
        elif name == 'AttributeValueCount':
            self.attr_value_count = int(value)
        elif name == 'AttributeValuesSizeBytes':
            self.attr_values_size = int(value)
        elif name == 'Timestamp':
            self.timestamp = value
        else:
            setattr(self, name, value)

