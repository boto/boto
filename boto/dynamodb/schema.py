# Copyright (c) 2011 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2011 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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

def is_num(n):
    return (isinstance(n, int) or isinstance(n, float))

def is_str(n):
    return isinstance(n, basestring)

def get_dynamodb_type(val):
    """
    Take a scalar Python value and return a string representing
    the corresponding DynamoDB type.  If the value passed in is
    not a supported type, raise a TypeError.
    """
    if isinstance(val, int) or isinstance(val, float):
        dynamodb_type = 'N'
    elif isinstance(val, basestring):
        dynamodb_type = 'S'
    elif isinstance(val, list):
        if False not in map(is_num, val):
            dynamodb_type = 'NS'
        elif False not in map(is_str, val):
            dynamodb_type = 'SS'
    else:
        raise TypeError('Unsupported type')
    return dynamodb_type

def dynamize_value(val):
    """
    Take a scalar Python value and return a dict consisting
    of the DynamoDB type specification and the value that
    needs to be sent to DynamoDB.  If the type of the value
    is not supported, raise a TypeError
    """
    dynamodb_type = get_dynamodb_type(val)
    if dynamodb_type == 'N':
        val = {dynamodb_type : str(val)}
    elif dynamodb_type == 'S':
        val = {dynamodb_type : val}
    elif dynamodb_type == 'NS':
        val = {dynamodb_type : [ str(n) for n in val]}
    elif dynamodb_type == 'SS':
        val = {dynamodb_type : val}
    return val

class Schema(object):

    def __init__(self, table, schema_dict):
        self.table = table
        self._dict = schema_dict

    def __repr__(self):
        return repr(self._dict)
        
    @property
    def hash_key_name(self):
        return self._dict['HashKeyElement']['AttributeName']
    
    @property
    def hash_key_type(self):
        return self._dict['HashKeyElement']['AttributeType']
    
    @property
    def range_key_name(self):
        name = None
        if 'RangeKeyElement' in self._dict:
            name = self._dict['RangeKeyElement']['AttributeName']
        return name
    
    @property
    def range_key_type(self):
        type = None
        if 'RangeKeyElement' in self._dict:
            type = self._dict['RangeKeyElement']['AttributeType']
        return type
    
    def build_key_from_values(self, hash_key, range_key=None):
        """
        Build a Key structure to be used for accessing items
        in DynamoDB.  This method takes the supplied hash_key
        and optional range_key and validates them against the
        schema.  If there is a mismatch, a TypeError is raised.
        Otherwise, a Python dict version of a DynamoDB Key
        data structure is returned.

        :type hash_key: int, float, str, or unicode
        :param hash_key: The hash key of the item you are looking for.
            The type of the hash key should match the type defined in
            the schema.

        :type range_key: int, float, str or unicode
        :param range_key: The range key of the item your are looking for.
            This should be supplied only if the schema requires a
            range key.  The type of the range key should match the
            type defined in the schema.
        """
        # Need to do type checking
        dynamodb_key = {}
        dynamodb_key['HashKeyElement'] = dynamize_value(hash_key)
        if range_key:
            dynamodb_key['RangeKeyElement'] = dynamize_value(range_key)
        return dynamodb_key

        
