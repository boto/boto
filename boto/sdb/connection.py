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

import urllib
import xml.sax
import threading
import boto
from boto import handler
from boto.connection import AWSQueryConnection
from boto.sdb.domain import Domain, DomainMetaData
from boto.sdb.item import Item
from boto.exception import SDBResponseError
from boto.resultset import ResultSet

class ItemThread(threading.Thread):
    
    def __init__(self, name, domain_name, item_names):
        threading.Thread.__init__(self, name=name)
        print 'starting %s with %d items' % (name, len(item_names))
        self.domain_name = domain_name
        self.conn = SDBConnection()
        self.item_names = item_names
        self.items = []
        
    def run(self):
        for item_name in self.item_names:
            item = self.conn.get_attributes(self.domain_name, item_name)
            self.items.append(item)

class SDBConnection(AWSQueryConnection):

    APIVersion = '2007-11-07'
    SignatureVersion = '2'
    ResponseError = SDBResponseError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, host='sdb.amazonaws.com', debug=0,
                 https_connection_factory=None):
        AWSQueryConnection.__init__(self, aws_access_key_id, aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                                    host, debug, https_connection_factory)
        self.box_usage = 0.0

    def build_name_value_list(self, params, attributes, replace=False):
        keys = attributes.keys()
        keys.sort()
        i = 1
        for key in keys:
            value = attributes[key]
            if isinstance(value, list):
                for v in value:
                    params['Attribute.%d.Name'%i] = key
                    params['Attribute.%d.Value'%i] = v
                    if replace:
                        params['Attribute.%d.Replace'%i] = 'true'
                    i += 1
            else:
                params['Attribute.%d.Name'%i] = key
                params['Attribute.%d.Value'%i] = value
                if replace:
                    params['Attribute.%d.Replace'%i] = 'true'
            i += 1

    def build_name_list(self, params, attribute_names):
        i = 1
        attribute_names.sort()
        for name in attribute_names:
            params['Attribute.%d.Name'%i] = name
            i += 1

    def get_usage(self):
        """
        Returns the BoxUsage accumulated on this SDBConnection object.

        @rtype: float
        @return: The accumulated BoxUsage of all requests made on the connection.
        """
        return self.box_usage

    def print_usage(self):
        """
        Print the BoxUsage and approximate costs of all requests made on this connection.
        """
        print 'Total Usage: %f compute seconds' % self.box_usage
        cost = self.box_usage * 0.14
        print 'Approximate Cost: $%f' % cost

    def get_domain(self, domain_name, validate=True):
        domain = Domain(self, domain_name)
        if validate:
            self.query(domain, '', max_items=1)
        return domain

    def lookup(self, domain_name, validate=True):
        """
        Lookup an existing SimpleDB domain

        @type domain_name: string
        @param domain_name: The name of the new domain

        @rtype: L{Domain<boto.sdb.domain.Domain>} object or None
        @return: The Domain object or None if the domain does not exist.
        """
        try:
            domain = self.get_domain(domain_name, validate)
        except:
            domain = None
        return domain

    def get_all_domains(self, max_domains=None, next_token=None):
        params = {}
        if max_domains:
            params['MaxNumberOfDomains'] = max_domains
        if next_token:
            params['NextToken'] = next_token
        return self.get_list('ListDomains', params, [('DomainName', Domain)])
        
    def create_domain(self, domain_name):
        """
        Create a SimpleDB domain.

        @type domain_name: string
        @param domain_name: The name of the new domain

        @rtype: L{Domain<boto.sdb.domain.Domain>} object
        @return: The newly created domain
        """
        params = {'DomainName':domain_name}
        d = self.get_object('CreateDomain', params, Domain)
        d.name = domain_name
        return d

    def get_domain_and_name(self, domain_or_name):
        if (isinstance(domain_or_name, Domain)):
            return (domain_or_name, domain_or_name.name)
        else:
            return (self.get_domain(domain_or_name), domain_or_name)
        
    def delete_domain(self, domain_or_name):
        """
        Delete a SimpleDB domain.

        @type domain_or_name: string or L{Domain<boto.sdb.domain.Domain>} object.
        @param domain_or_name: Either the name of a domain or a Domain object

        @rtype: bool
        @return: True if successful
        
        B{Note:} This will delete the domain and all items within the domain.
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName':domain_name}
        return self.get_status('DeleteDomain', params)
        
    def domain_metadata(self, domain_or_name):
        """
        Get the Metadata for a SimpleDB domain.

        @type domain_or_name: string or L{Domain<boto.sdb.domain.Domain>} object.
        @param domain_or_name: Either the name of a domain or a Domain object

        @rtype: L{DomainMetaData<boto.sdb.domain.DomainMetaData>} object
        @return: The newly created domain metadata object
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName':domain_name}
        d = self.get_object('DomainMetadata', params, DomainMetaData)
        d.domain = domain
        return d
        
    def put_attributes(self, domain_or_name, item_name, attributes, replace=True):
        """
        Store attributes for a given item in a domain.

        @type domain_or_name: string or L{Domain<boto.sdb.domain.Domain>} object.
        @param domain_or_name: Either the name of a domain or a Domain object

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
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName' : domain_name,
                  'ItemName' : item_name}
        self.build_name_value_list(params, attributes, replace)
        return self.get_status('PutAttributes', params)

    def get_attributes(self, domain_or_name, item_name, attribute_names=None, item=None):
        """
        Retrieve attributes for a given item in a domain.

        @type domain_or_name: string or L{Domain<boto.sdb.domain.Domain>} object.
        @param domain_or_name: Either the name of a domain or a Domain object

        @type item_name: string
        @param item_name: The name of the item whose attributes are being retrieved.

        @type attribute_names: string or list of strings
        @param attribute_names: An attribute name or list of attribute names.  This
                                parameter is optional.  If not supplied, all attributes
                                will be retrieved for the item.

        @rtype: L{Item<boto.sdb.item.Item>}
        @return: An Item mapping type containing the requested attribute name/values
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName' : domain_name,
                  'ItemName' : item_name}
        if attribute_names:
            if not isinstance(attribute_names, list):
                attribute_names = [attribute_names]
            self.build_list_params(params, attribute_names, 'AttributeName')
        response = self.make_request('GetAttributes', params)
        body = response.read()
        if response.status == 200:
            if item == None:
                item = Item(domain, item_name)
            h = handler.XmlHandler(item, self)
            xml.sax.parseString(body, h)
            return item
        else:
            raise SDBResponseError(response.status, response.reason, body)
        
    def delete_attributes(self, domain_or_name, item_name, attr_names=None):
        """
        Delete attributes from a given item in a domain.

        @type domain_or_name: string or L{Domain<boto.sdb.domain.Domain>} object.
        @param domain_or_name: Either the name of a domain or a Domain object

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
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName':domain_name,
                  'ItemName' : item_name}
        if attr_names:
            if isinstance(attr_names, list):
                self.build_name_list(params, attr_names)
            elif isinstance(attr_names, dict) or isinstance(attr_names, Item):
                self.build_name_value_list(params, attr_names)
        return self.get_status('DeleteAttributes', params)
        
    def query(self, domain_or_name, query='', max_items=None, next_token=None):
        """
        Returns a list of item names within domain_name that match the query.
        
        @type domain_or_name: string or L{Domain<boto.sdb.domain.Domain>} object.
        @param domain_or_name: Either the name of a domain or a Domain object

        @type query: string
        @param query: The SimpleDB query to be performed.

        @type max_items: int
        @param max_items: The maximum number of items to return.  If not
                          supplied, the default is None which returns all
                          items matching the query.

        @rtype: ResultSet
        @return: An iterator containing the results.
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName':domain_name,
                  'QueryExpression' : query}
        if max_items:
            params['MaxNumberOfItems'] = max_items
        if next_token:
            params['NextToken'] = next_token
        return self.get_object('Query', params, ResultSet)

    def query_with_attributes(self, domain_or_name, query='', attr_names=None,
                              max_items=None, next_token=None):
        """
        Returns a set of Attributes for item names within domain_name that match the query.
        
        @type domain_or_name: string or L{Domain<boto.sdb.domain.Domain>} object.
        @param domain_or_name: Either the name of a domain or a Domain object

        @type query: string
        @param query: The SimpleDB query to be performed.

        @type attr_names: list
        @param attr_names: The name of the attributes to be returned.
                           If no attributes are specified, all attributes
                           will be returned.

        @type max_items: int
        @param max_items: The maximum number of items to return.  If not
                          supplied, the default is None which returns all
                          items matching the query.

        @rtype: ResultSet
        @return: An iterator containing the results.
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName':domain_name,
                  'QueryExpression' : query}
        if max_items:
            params['MaxNumberOfItems'] = max_items
        if next_token:
            params['NextToken'] = next_token
        if attr_names:
            self.build_list_params(params, attr_names, 'AttributeName')
        return self.get_list('QueryWithAttributes', params, [('Item', Item)], parent=domain)

    def threaded_query(self, domain_or_name, query='', max_items=None, next_token=None, num_threads=6):
        """
        Returns a list of fully populated items that match the query provided.

        The name/value pairs for all of the matching item names are retrieved in a number of separate
        threads (specified by num_threads) to achieve maximum throughput.
        The ResultSet that is returned has an attribute called next_token that can be used
        to retrieve additional results for the same query.
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        if max_items and num_threads > max_items:
            num_threads = max_items
        rs = self.query(domain_or_name, query, max_items, next_token)
        threads = []
        n = len(rs) / num_threads
        for i in range(0, num_threads):
            if i+1 == num_threads:
                thread = ItemThread('Thread-%d' % i, domain_name, rs[n*i:])
            else:
                thread = ItemThread('Thread-%d' % i, domain_name, rs[n*i:n*(i+1)])
            threads.append(thread)
            thread.start()
        del rs[0:]
        for thread in threads:
            thread.join()
            for item in thread.items:
                rs.append(item)
        return rs

