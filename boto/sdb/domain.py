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
from boto.sdb.queryresultset import QueryResultSet, SelectResultSet
from boto.sdb.item import Item

class Domain:
    
    def __init__(self, connection=None, name=None):
        self.connection = connection
        self.name = name
        self._metadata = None

    def __repr__(self):
        return 'Domain:%s' % self.name

    def __iter__(self):
        return self.select("SELECT * FROM %s" % self.name)

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
        """
        Store attributes for a given item.

        @type item_name: string
        @param item_name: The name of the item whose attributes are being stored.

        @type attribute_names: dict or dict-like object
        @param attribute_names: The name/value pairs to store as attributes

        @type replace: bool
        @param replace: Whether the attribute values passed in will replace
                        existing values or will be added as addition values.
                        Defaults to True.

        @rtype: bool
        @return: True if successful
        """
        return self.connection.put_attributes(self, item_name, attributes, replace)

    def batch_put_attributes(self, items, replace=True):
        """
        Store attributes for multiple items.

        @type items: dict or dict-like object
        @param items: A dictionary-like object.  The keys of the dictionary are
                      the item names and the values are themselves dictionaries
                      of attribute names/values, exactly the same as the
                      attribute_names parameter of the scalar put_attributes
                      call.

        @type replace: bool
        @param replace: Whether the attribute values passed in will replace
                        existing values or will be added as addition values.
                        Defaults to True.

        @rtype: bool
        @return: True if successful
        """
        return self.connection.batch_put_attributes(self, items, replace)

    def get_attributes(self, item_name, attribute_name=None, item=None):
        """
        Retrieve attributes for a given item.

        @type item_name: string
        @param item_name: The name of the item whose attributes are being retrieved.

        @type attribute_names: string or list of strings
        @param attribute_names: An attribute name or list of attribute names.  This
                                parameter is optional.  If not supplied, all attributes
                                will be retrieved for the item.

        @rtype: L{Item<boto.sdb.item.Item>}
        @return: An Item mapping type containing the requested attribute name/values
        """
        return self.connection.get_attributes(self, item_name, attribute_name, item)

    def delete_attributes(self, item_name, attributes=None):
        """
        Delete attributes from a given item.

        @type item_name: string
        @param item_name: The name of the item whose attributes are being deleted.

        @type attributes: dict, list or L{Item<boto.sdb.item.Item>}
        @param attributes: Either a list containing attribute names which will cause
                           all values associated with that attribute name to be deleted or
                           a dict or Item containing the attribute names and keys and list
                           of values to delete as the value.  If no value is supplied,
                           all attribute name/values for the item will be deleted.
                           
        @rtype: bool
        @return: True if successful
        """
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
    
    def select(self, query='', next_token=None, max_items=None):
        """
        Returns a set of Attributes for item names within domain_name that match the query.
        The query must be expressed in using the SELECT style syntax rather than the
        original SimpleDB query language.

        @type query: string
        @param query: The SimpleDB query to be performed.

        @type max_items: int
        @param max_items: The maximum number of items to return.

        @rtype: iter
        @return: An iterator containing the results.  This is actually a generator
                 function that will iterate across all search results, not just the
                 first page.
        """
        return iter(SelectResultSet(self, query, max_items))
    
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

    def to_xml(self):
        """
        Get this domain as an XML DOM Document
        """
        from xml.dom.minidom import getDOMImplementation
        impl = getDOMImplementation()
        doc = impl.createDocument(None, 'Domain', None)
        doc.documentElement.setAttribute("id", self.name)
        for item in self:
            obj_node = doc.createElement('Item')
            obj_node.setAttribute("id", item.name)
            for k in item:
                attr_node = doc.createElement("attribute")
                attr_node.setAttribute("id", k)
                values = item[k]
                if not isinstance(values, list):
                    values = [item[k]]

                for value in values:
                    value_node = doc.createElement("value")
                    value_node.appendChild(doc.createTextNode(str(value.encode('utf-8'))))
                    attr_node.appendChild(value_node)

                obj_node.appendChild(attr_node)
            doc.documentElement.appendChild(obj_node)
        return doc

    def from_xml(self, doc):
        """
        Load this domain based on an XML document
        """
        import xml.sax
        handler = DomainDumpParser(self)
        xml.sax.parse(doc, handler)
        return handler


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

from xml.sax.handler import ContentHandler
class DomainDumpParser(ContentHandler):
    """
    SAX parser for a domain that has been dumped
    """
    
    def __init__(self, domain):
        self.items = []
        self.item = None
        self.attribute = None
        self.value = ""
        self.domain = domain

    def startElement(self, name, attrs):
        if name == "Item":
            self.item = self.domain.new_item(attrs['id'])
        elif name == "attribute":
            self.attribute = attrs['id']
        elif name == "value":
            self.value = ""

    def characters(self, ch):
        self.value += ch

    def endElement(self, name):
        if name == "value":
            if self.value and self.attribute:
                self.item.add_value(self.attribute, self.value.strip())
        elif name == "Item":
            self.item.save()

