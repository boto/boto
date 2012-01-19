# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
#

from boto.dynamodb.utils import item_object_hook, dynamize_value

class Item(object):

    def __init__(self, table, hash_key=None, range_key=None, attrs=None):
        self.table = table
        self._hash_key = hash_key
        self._range_key = range_key
        if attrs is None:
            attrs = {}
        self.attrs = attrs
        # We don't want the hashkey/rangekey in the attrs dict
        if self.hash_key_name in self.attrs:
            del self.attrs[self.hash_key_name]
        if self.range_key_name in self.attrs:
            del self.attrs[self.range_key_name]
        self.consumed_units = 0

    @property
    def hash_key(self):
        return self._hash_key
                                             
    @property
    def range_key(self):
        return self._range_key
                                             
    @property
    def hash_key_name(self):
        return self.table.schema.hash_key_name
    
    @property
    def range_key_name(self):
        return self.table.schema.range_key_name
    
    def dynamize(self):
        d = {self.hash_key_name: dynamize_value(self.hash_key)}
        if self.range_key:
            d[self.range_key_name] = dynamize_value(self.range_key)
        for attr_name in self.attrs:
            d[attr_name] = dynamize_value(self.attrs[attr_name])
        return d

    def dynamize_expected_value(self, expected_value):
        """
        Convert an expected_value parameter into the data structure
        required for Layer1.
        """
        d = None
        if expected_value:
            d = {}
            for attr_name in expected_value:
                attr_value = expected_value[attr_name]
                if attr_value is True:
                    attr_value = {'Exists': True}
                elif attr_value is False:
                    attr_value = {'Exists': False}
                else:
                    attr_value = dynamize_value(expected_value[attr_name])
                d[attr_name] = attr_value
        return d

    def delete(self, expected_value=None, return_values=None):
        """
        Delete the item from DynamoDB.

        :type expected: dict
        :param expected: A dictionary of name/value pairs that you expect.
            This dictionary should have name/value pairs where the name
            is the name of the attribute and the value is either the value
            you are expecting or False if you expect the attribute not to
            exist.
        """
        expected_value = self.dynamize_expected_value(expected_value)
        key = self.table.schema.build_key_from_values(self.hash_key,
                                                      self.range_key)
        response = self.table.layer1.delete_item(self.table.name, key,
                                                 expected=expected_value)

    def put(self, expected_value=None, return_values=None):
        """
        Store a new item or completely replace an existing item
        in Amazon DynamoDB.

        :type expected: dict
        :param expected: A dictionary of name/value pairs that you expect.
            This dictionary should have name/value pairs where the name
            is the name of the attribute and the value is either the value
            you are expecting or False if you expect the attribute not to
            exist.

        :type return_values: str
        :param return_values: Controls the return of attribute
            name-value pairs before then were changed.  Possible
            values are: None or 'ALL_OLD'. If 'ALL_OLD' is
            specified and the item is overwritten, the content
            of the old item is returned.
            
        """
        response = self.table.layer1.put_item(self.table.name,
                                              self.dynamize(),
                                              expected_value, return_values)
        if 'ConsumedCapacityUnits' in response:
            self.consumed_units = response['ConsumedCapacityUnits']
        
