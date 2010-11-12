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

import xml.sax
import threading
from boto import handler
from boto.connection import AWSQueryConnection
from boto.sdb.domain import Domain, DomainMetaData
from boto.sdb.item import Item
from boto.sdb.regioninfo import SDBRegionInfo
from boto.exception import SDBResponseError

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

#boto.set_stream_logger('sdb')

class SDBConnection(AWSQueryConnection):

    DefaultRegionName = 'us-east-1'
    DefaultRegionEndpoint = 'sdb.amazonaws.com'
    APIVersion = '2009-04-15'
    SignatureVersion = '2'
    ResponseError = SDBResponseError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None, path='/', converter=None):
        if not region:
            region = SDBRegionInfo(self, self.DefaultRegionName, self.DefaultRegionEndpoint)
        self.region = region
        AWSQueryConnection.__init__(self, aws_access_key_id, aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                                    self.region.endpoint, debug, https_connection_factory, path)
        self.box_usage = 0.0
        self.converter = converter
        self.item_cls = Item

    def set_item_cls(self, cls):
        self.item_cls = cls

    def build_name_value_list(self, params, attributes, replace=False,
                              label='Attribute'):
        keys = attributes.keys()
        keys.sort()
        i = 1
        for key in keys:
            value = attributes[key]
            if isinstance(value, list):
                for v in value:
                    params['%s.%d.Name'%(label,i)] = key
                    if self.converter:
                        v = self.converter.encode(v)
                    params['%s.%d.Value'%(label,i)] = v
                    if replace:
                        params['%s.%d.Replace'%(label,i)] = 'true'
                    i += 1
            else:
                params['%s.%d.Name'%(label,i)] = key
                if self.converter:
                    value = self.converter.encode(value)
                params['%s.%d.Value'%(label,i)] = value
                if replace:
                    params['%s.%d.Replace'%(label,i)] = 'true'
            i += 1

    def build_expected_value(self, params, expected_value):
        params['Expected.1.Name'] = expected_value[0]
        if expected_value[1] is True:
            params['Expected.1.Exists'] = 'true'
        elif expected_value[1] is False:
            params['Expected.1.Exists'] = 'false'
        else:
            params['Expected.1.Value'] = expected_value[1]
            

    def build_batch_list(self, params, items, replace=False):
        item_names = items.keys()
        i = 0
        for item_name in item_names:
            j = 0
            item = items[item_name]
            attr_names = item.keys()
            params['Item.%d.ItemName' % i] = item_name
            for attr_name in attr_names:
                value = item[attr_name]
                if isinstance(value, list):
                    for v in value:
                        if self.converter:
                            v = self.converter.encode(v)
                        params['Item.%d.Attribute.%d.Name' % (i,j)] = attr_name
                        params['Item.%d.Attribute.%d.Value' % (i,j)] = v
                        if replace:
                            params['Item.%d.Attribute.%d.Replace' % (i,j)] = 'true'
                        j += 1
                else:
                    params['Item.%d.Attribute.%d.Name' % (i,j)] = attr_name
                    if self.converter:
                        value = self.converter.encode(value)
                    params['Item.%d.Attribute.%d.Value' % (i,j)] = value
                    if replace:
                        params['Item.%d.Attribute.%d.Replace' % (i,j)] = 'true'
                    j += 1
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

        :rtype: float
        :return: The accumulated BoxUsage of all requests made on the connection.
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
            self.select(domain, """select * from `%s` limit 1""" % domain_name)
        return domain

    def lookup(self, domain_name, validate=True):
        """
        Lookup an existing SimpleDB domain

        :type domain_name: string
        :param domain_name: The name of the new domain

        :rtype: :class:`boto.sdb.domain.Domain` object or None
        :return: The Domain object or None if the domain does not exist.
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

        :type domain_name: string
        :param domain_name: The name of the new domain

        :rtype: :class:`boto.sdb.domain.Domain` object
        :return: The newly created domain
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

        :type domain_or_name: string or :class:`boto.sdb.domain.Domain` object.
        :param domain_or_name: Either the name of a domain or a Domain object

        :rtype: bool
        :return: True if successful
        
        B{Note:} This will delete the domain and all items within the domain.
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName':domain_name}
        return self.get_status('DeleteDomain', params)
        
    def domain_metadata(self, domain_or_name):
        """
        Get the Metadata for a SimpleDB domain.

        :type domain_or_name: string or :class:`boto.sdb.domain.Domain` object.
        :param domain_or_name: Either the name of a domain or a Domain object

        :rtype: :class:`boto.sdb.domain.DomainMetaData` object
        :return: The newly created domain metadata object
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName':domain_name}
        d = self.get_object('DomainMetadata', params, DomainMetaData)
        d.domain = domain
        return d
        
    def put_attributes(self, domain_or_name, item_name, attributes,
                       replace=True, expected_value=None):
        """
        Store attributes for a given item in a domain.
        
        :type domain_or_name: string or :class:`boto.sdb.domain.Domain` object.
        :param domain_or_name: Either the name of a domain or a Domain object
        
        :type item_name: string
        :param item_name: The name of the item whose attributes are being stored.
        
        :type attribute_names: dict or dict-like object
        :param attribute_names: The name/value pairs to store as attributes
        
        :type expected_value: list
        :param expected_value: If supplied, this is a list or tuple consisting
                               of a single attribute name and expected value.
                               The list can be of the form:
                               
                               * ['name', 'value']
                                
                               In which case the call will first verify
                               that the attribute "name" of this item has
                               a value of "value".  If it does, the delete
                               will proceed, otherwise a ConditionalCheckFailed
                               error will be returned.
                               The list can also be of the form:
                               
                               * ['name', True|False]
                                
                               which will simply check for the existence (True)
                               or non-existencve (False) of the attribute.
        
        :type replace: bool
        :param replace: Whether the attribute values passed in will replace
                        existing values or will be added as addition values.
                        Defaults to True.
        
        :rtype: bool
        :return: True if successful
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName' : domain_name,
                  'ItemName' : item_name}
        self.build_name_value_list(params, attributes, replace)
        if expected_value:
            self.build_expected_value(params, expected_value)
        return self.get_status('PutAttributes', params)

    def batch_put_attributes(self, domain_or_name, items, replace=True):
        """
        Store attributes for multiple items in a domain.
        
        :type domain_or_name: string or :class:`boto.sdb.domain.Domain` object.
        :param domain_or_name: Either the name of a domain or a Domain object

        :type items: dict or dict-like object
        :param items: A dictionary-like object.  The keys of the dictionary are
                      the item names and the values are themselves dictionaries
                      of attribute names/values, exactly the same as the
                      attribute_names parameter of the scalar put_attributes
                      call.
        
        :type replace: bool
        :param replace: Whether the attribute values passed in will replace
                        existing values or will be added as addition values.
                        Defaults to True.
        
        :rtype: bool
        :return: True if successful
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName' : domain_name}
        self.build_batch_list(params, items, replace)
        return self.get_status('BatchPutAttributes', params, verb='POST')

    def get_attributes(self, domain_or_name, item_name, attribute_names=None,
                       consistent_read=False, item=None):
        """
        Retrieve attributes for a given item in a domain.

        :type domain_or_name: string or :class:`boto.sdb.domain.Domain` object.
        :param domain_or_name: Either the name of a domain or a Domain object

        :type item_name: string
        :param item_name: The name of the item whose attributes are being retrieved.

        :type attribute_names: string or list of strings
        :param attribute_names: An attribute name or list of attribute names.  This
                                parameter is optional.  If not supplied, all attributes
                                will be retrieved for the item.

        :type consistent_read: bool
        :param consistent_read: When set to true, ensures that the most recent
                                data is returned.

        :rtype: :class:`boto.sdb.item.Item`
        :return: An Item mapping type containing the requested attribute name/values
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName' : domain_name,
                  'ItemName' : item_name}
        if consistent_read:
            params['ConsistentRead'] = 'true'
        if attribute_names:
            if not isinstance(attribute_names, list):
                attribute_names = [attribute_names]
            self.build_list_params(params, attribute_names, 'AttributeName')
        response = self.make_request('GetAttributes', params)
        body = response.read()
        if response.status == 200:
            if item == None:
                item = self.item_cls(domain, item_name)
            h = handler.XmlHandler(item, self)
            xml.sax.parseString(body, h)
            return item
        else:
            raise SDBResponseError(response.status, response.reason, body)
        
    def delete_attributes(self, domain_or_name, item_name, attr_names=None,
                          expected_value=None):
        """
        Delete attributes from a given item in a domain.

        :type domain_or_name: string or :class:`boto.sdb.domain.Domain` object.
        :param domain_or_name: Either the name of a domain or a Domain object

        :type item_name: string
        :param item_name: The name of the item whose attributes are being deleted.

        :type attributes: dict, list or :class:`boto.sdb.item.Item`
        :param attributes: Either a list containing attribute names which will cause
                           all values associated with that attribute name to be deleted or
                           a dict or Item containing the attribute names and keys and list
                           of values to delete as the value.  If no value is supplied,
                           all attribute name/values for the item will be deleted.
                           
        :type expected_value: list
        :param expected_value: If supplied, this is a list or tuple consisting
                               of a single attribute name and expected value.
                               The list can be of the form:
                               
                               * ['name', 'value']
                               
                               In which case the call will first verify
                               that the attribute "name" of this item has
                               a value of "value".  If it does, the delete
                               will proceed, otherwise a ConditionalCheckFailed
                               error will be returned.
                               The list can also be of the form:
                               
                               * ['name', True|False]
                               
                               which will simply check for the existence (True)
                               or non-existencve (False) of the attribute.

        :rtype: bool
        :return: True if successful
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName':domain_name,
                  'ItemName' : item_name}
        if attr_names:
            if isinstance(attr_names, list):
                self.build_name_list(params, attr_names)
            elif isinstance(attr_names, dict) or isinstance(attr_names, self.item_cls):
                self.build_name_value_list(params, attr_names)
        if expected_value:
            self.build_expected_value(params, expected_value)
        return self.get_status('DeleteAttributes', params)
        
    def select(self, domain_or_name, query='', next_token=None,
               consistent_read=False):
        """
        Returns a set of Attributes for item names within domain_name that match the query.
        The query must be expressed in using the SELECT style syntax rather than the
        original SimpleDB query language.
        Even though the select request does not require a domain object, a domain
        object must be passed into this method so the Item objects returned can
        point to the appropriate domain.
        
        :type domain_or_name: string or :class:`boto.sdb.domain.Domain` object.
        :param domain_or_name: Either the name of a domain or a Domain object

        :type query: string
        :param query: The SimpleDB query to be performed.

        :type consistent_read: bool
        :param consistent_read: When set to true, ensures that the most recent
                                data is returned.

        :rtype: ResultSet
        :return: An iterator containing the results.
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'SelectExpression' : query}
        if consistent_read:
            params['ConsistentRead'] = 'true'
        if next_token:
            params['NextToken'] = next_token
        try:
            return self.get_list('Select', params, [('Item', self.item_cls)],
                             parent=domain)
        except SDBResponseError, e:
            e.body = "Query: %s\n%s" % (query, e.body)
            raise e
