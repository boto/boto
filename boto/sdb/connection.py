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
from boto import handler
from boto.connection import AWSQueryConnection
from boto.sdb.domain import Domain
from boto.sdb.item import Item
from boto.exception import SDBResponseError
from boto.resultset import ResultSet

class SDBConnection(AWSQueryConnection):

    APIVersion = '2007-11-07'
    SignatureVersion = '1'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=False, port=None, proxy=None, proxy_port=None,
                 host='sdb.amazonaws.com', debug=0,
                 https_connection_factory=None):
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
                                    host, debug, https_connection_factory)
        self.box_usage = 0.0

    def build_name_value_list(self, params, attributes, replace):
        keys = attributes.keys()
        keys.sort()
        i = 1
        for key in keys:
            value = attributes[key]
            if isinstance(value, list):
                for v in value:
                    params['Attribute.%d.Name'%i] = key
                    params['Attribute.%d.Value'%i] = v
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
        return self.box_usage

    def print_usage(self):
        print 'Total Usage: %f compute seconds' % self.box_usage
        cost = self.box_usage * 0.14
        print 'Approximate Cost: $%f' % cost

    def get_domain(self, domain_name, validate=True):
        """
        Returns a Domain object for a given domain_name.
        If the validate parameter is True, the domain_name is validated
        by performing a query (returning a max of 1 item) against the domain.
        """
        domain = Domain(self, domain_name)
        if validate:
            self.query(domain, '', max_items=1)
        return domain

    def get_all_domains(self, max_domains=None, next_token=None):
        params = {}
        if max_domains:
            params['MaxNumberOfDomains'] = max_domains
        if next_token:
            params['NextToken'] = next_token
        response = self.make_request('ListDomains', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet([('DomainName', Domain)])
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise SDBResponseError(response.status, response.reason, body)
        
    def create_domain(self, domain_name):
        params = {'DomainName':domain_name}
        response = self.make_request('CreateDomain', params)
        body = response.read()
        if response.status == 200:
            domain = Domain(self)
            domain.name = domain_name
            h = handler.XmlHandler(domain, self)
            xml.sax.parseString(body, h)
            return domain
        else:
            raise SDBResponseError(response.status, response.reason, body)

    def get_domain_and_name(self, domain_or_name):
        if (isinstance(domain_or_name, Domain)):
            return (domain_or_name, domain_or_name.name)
        else:
            return (self.get_domain(domain_or_name), domain_or_name)
        
    def delete_domain(self, domain_or_name):
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName':domain_name}
        response = self.make_request('DeleteDomain', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return True
        else:
            raise SDBResponseError(response.status, response.reason, body)
        
    def put_attributes(self, domain_or_name, item_name, attributes, replace=True):
        """
        Store attributes for a given item in a domain.
        Parameters:
            domain__or_name - either a domain object or the name of a domain in SimpleDB
            item_name - the name of the SDB item the attributes will be
                        associated with
            attributes - a dict containing the name/value pairs to store
                         as attributes
            replace - a boolean value that determines whether the attribute
                      values passed in will replace any existing values or will
                      be added as additional values.  Defaults to True.
        Returns:
            Boolean True or raises an exception
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName' : domain_name,
                  'ItemName' : item_name}
        self.build_name_value_list(params, attributes, replace)
        response = self.make_request('PutAttributes', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return True
        else:
            raise SDBResponseError(response.status, response.reason, body)

    def get_attributes(self, domain_or_name, item_name, attributes=None, item=None):
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName' : domain_name,
                  'ItemName' : item_name}
        if attributes:
            self.build_list_params(params, attributes, 'AttributeName')
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
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName':domain_name,
                  'ItemName' : item_name}
        if attr_names:
            self.build_name_list(params, attr_names)
        response = self.make_request('DeleteAttributes', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return True
        else:
            raise SDBResponseError(response.status, response.reason, body)
        
    def query(self, domain_or_name, query='', max_items=None, next_token=None):
        """
        Returns a list of item names within domain_name that match the query.
        """
        domain, domain_name = self.get_domain_and_name(domain_or_name)
        params = {'DomainName':domain_name,
                  'QueryExpression' : query}
        if max_items:
            params['MaxNumberOfItems'] = max_items
        if next_token:
            params['NextToken'] = next_token
        response = self.make_request('Query', params)
        body = response.read()
        if self.debug > 1:
            print body
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise SDBResponseError(response.status, response.reason, body)
