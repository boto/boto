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

from boto.dynamodb.utils import dynamize_value

class Schema(object):
    """
    Represents a DynamoDB schema.

    :ivar hash_key_name: The name of the hash key of the schema.
    :ivar hash_key_type: The DynamoDB type specification for the
        hash key of the schema.
    :ivar range_key_name: The name of the range key of the schema
        or None if no range key is defined.
    :ivar range_key_type: The DynamoDB type specification for the
        range key of the schema or None if no range key is defined.
    :ivar dict: The underlying Python dictionary that needs to be
        passed to Layer1 methods.
    """

    def __init__(self, schema_dict):
        self._dict = schema_dict

    def __repr__(self):
        if self.range_key_name:
            s = 'Schema(%s:%s)' % (self.hash_key_name, self.range_key_name)
        else:
            s = 'Schema(%s)' % self.hash_key_name
        return s

    @property
    def dict(self):
        return self._dict
    
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
        dynamodb_key = {}
        dynamodb_value = dynamize_value(hash_key)
        if dynamodb_value.keys()[0] != self.hash_key_type:
            msg = 'Hashkey must be of type: %s' % self.hash_key_type
            raise TypeError(msg)
        dynamodb_key['HashKeyElement'] = dynamodb_value
        if range_key:
            dynamodb_value = dynamize_value(range_key)
            if dynamodb_value.keys()[0] != self.range_key_type:
                msg = 'RangeKey must be of type: %s' % self.range_key_type
                raise TypeError(msg)
            dynamodb_key['RangeKeyElement'] = dynamodb_value
        return dynamodb_key

