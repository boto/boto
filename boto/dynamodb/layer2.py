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

from layer1 import Layer1
from table import Table
from schema import Schema
from boto.dynamodb.utils import get_dynamodb_type

class Layer2(object):

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 host=None, debug=0):
        self.layer1 = Layer1(aws_access_key_id, aws_secret_access_key,
                             is_secure, port, proxy, proxy_port,
                             host, debug)

    def list_tables(self):
        """
        Return a list of the names of all Tables associated with the
        current account and region.
        """
        return self.layer1.list_tables()['TableNames']

    def get_table(self, name):
        """
        Retrieve the Table object for an existing table.

        :type name: str
        :param name: The name of the desired table.

        :rtype: :class:`boto.dynamodb.table.Table`
        :return: A Table object representing the table.
        """
        response = self.layer1.describe_table(name)
        return Table(self.layer1,  response)

    def create_table(self, name, schema, read_units, write_units):
        """
        Create a new DynamoDB table.
        
        :type name: str
        :param name: The name of the desired table.

        :type schema: :class:`boto.dynamodb.schema.Schema`
        :param schema: The Schema object that defines the schema used
            by this table.
            
        :type read_units: int
        :param read_units: The value for ReadCapacityUnits.
        
        :type write_units: int
        :param write_units: The value for WriteCapacityUnits.
        
        :rtype: :class:`boto.dynamodb.table.Table`
        :return: A Table object representing the new DynamoDB table.
        """
        response = self.layer1.create_table(name, schema.dict,
                                            {'ReadCapacityUnits': read_units,
                                             'WriteCapacityUnits': write_units})
        return Table(self.layer1,  response)

    def create_schema(self, hash_key_name, hash_key_proto_value,
                      range_key_name=None, range_key_proto_value=None):
        """
        Create a Schema object used when creating a Table.

        :type hash_key_name: str
        :param hash_key_name: The name of the HashKey for the schema.

        :type hash_key_proto_value: int|long|float|str|unicode
        :param hash_key_proto_value: A sample or prototype of the type
            of value you want to use for the HashKey.
            
        :type range_key_name: str
        :param range_key_name: The name of the RangeKey for the schema.
            This parameter is optional.

        :type range_key_proto_value: int|long|float|str|unicode
        :param range_key_proto_value: A sample or prototype of the type
            of value you want to use for the RangeKey.  This parameter
            is optional.
        """
        schema = {}
        hash_key = {}
        hash_key['AttributeName'] = hash_key_name
        hash_key['AttributeType'] = get_dynamodb_type(hash_key_proto_value)
        schema['HashKeyElement'] = hash_key
        if range_key_name and range_key_proto_value is not None:
            range_key = {}
            range_key['AttributeName'] = range_key_name
            range_key['AttributeType'] = get_dynamodb_type(range_key_proto_value)
            schema['RangeKeyElement'] = range_key
        return Schema(schema)
