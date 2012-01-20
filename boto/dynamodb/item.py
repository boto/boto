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

class Item(dict):
    """
    An item in Amazon DynamoDB.

    :ivar hash_key: The HashKey of this item.
    :ivar range_key: The RangeKey of this item or None if no RangeKey
        is defined.
    :ivar hash_key_name: The name of the HashKey associated with this item.
    :ivar range_key_name: The name of the RangeKey associated with this item.
    :ivar table: The Table this item belongs to.
    """

    def __init__(self, table, hash_key=None, range_key=None, attrs=None):
        self.table = table
        self._hash_key_name = self.table.schema.hash_key_name
        self._range_key_name = self.table.schema.range_key_name
        if hash_key:
            self[self._hash_key_name] = hash_key
        if range_key:
            self[self._range_key_name] = range_key
        if attrs:
            self.update(attrs)
        self.consumed_units = 0

    @property
    def hash_key(self):
        return self[self._hash_key_name]
                                             
    @property
    def range_key(self):
        return self[self._range_key_name]
                                             
    @property
    def hash_key_name(self):
        return self._hash_key_name
    
    @property
    def range_key_name(self):
        return self._range_key_name
    
    def delete(self, expected_value=None, return_values=None):
        """
        Delete the item from DynamoDB.

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
        self.table.layer2.delete_item(self, expected_value, return_values)

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
        self.table.layer2.put_item(self, expected_value, return_values)
