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

    def build_attr_list(self, params, attributes, do_value=True):
        keys = attributes.keys()
        keys.sort()
        i = 1
        for key in keys:
            if do_value:
                value = attributes[key]
                if isinstance(value, list):
                    for v in value:
                        params['Attribute.%d.Name'%i] = key
                        params['Attribute.%d.Value'%i] = v
                        i += 1
                else:
                    params['Attribute.%d.Name'%i] = key
                    params['Attribute.%d.Value'%i] = value
            else:
                params['Attribute.%d.Name'%i] = key
            i += 1

    def get_domain(self, domain_name, validate=True):
        """
        Returns a Domain object for a given domain_name.
        If the validate parameter is True, the domain_name is validated
        by performing a query (returning a max of 1 item) against the domain.
        """
        d = Domain(self, domain_name)
        if validate:
            self.query(domain_name, '', max_items=1)
        return d

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
        
    def delete_domain(self, domain_or_name):
        if (isinstance(domain_or_name, Domain)):
            domain_name = domain_or_name.name
        else:
            domain_name = domain_or_name
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
        
    def put_attributes(self, domain_name, item_name, attributes):
        """
        Store attributes for a given item in a domain.
        Parameters:
            domain_name - the name of the SDB domain
            item_name - the name of the SDB item the attributes will be
                        associated with
            attributes - a dict containing the name/value pairs to store
                         as attributes
        Returns:
            Boolean True or False or raises an exception
        """
        params = {'DomainName' : domain_name,
                  'ItemName' : item_name}
        self.build_attr_list(params, attributes, True)
        response = self.make_request('PutAttributes', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return True
        else:
            raise SDBResponseError(response.status, response.reason, body)

    def get_attributes(self, domain_name, item_name, attributes=None):
        params = {'DomainName' : domain_name,
                  'ItemName' : item_name}
        if attributes:
            self.build_list_params(params, attributes, 'AttributeName')
        response = self.make_request('GetAttributes', params)
        body = response.read()
        if response.status == 200:
            item = Item(self)
            item.name = item_name
            item.domain_name = domain_name
            h = handler.XmlHandler(item, self)
            xml.sax.parseString(body, h)
            return item
        else:
            raise SDBResponseError(response.status, response.reason, body)
        
    def delete_attributes(self, domain_name, item_name, attrs=None):
        params = {'DomainName':domain_name,
                  'ItemName' : item_name}
        if attrs:
            self.build_attr_list(params, attrs, False)
        response = self.make_request('DeleteAttributes', params)
        body = response.read()
        if response.status == 200:
            rs = ResultSet()
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return True
        else:
            raise SDBResponseError(response.status, response.reason, body)
        
    def query(self, domain_name, query='', max_items=None, next_token=None):
        """
        Returns a list of item names within domain_name that match the query.
        """
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
