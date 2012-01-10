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

import boto
from boto.connection import AWSAuthConnection
from boto.exception import DynamoDBResponseError
try:
    import simplejson as json
except ImportError:
    import json

def is_num(n):
    return (isinstance(n, int) or isinstance(n, float))

def is_str(n):
    return isinstance(n, basestring)

def item_object_hook(dct):
    """
    A custom object hook for use when decoding JSON item bodys.
    This hook will transform DynamoDB JSON responses to something
    that maps directly to native Python types.
    """
    if 'S' in dct:
        return dct['S']
    if 'N' in dct:
        try:
            return int(dct['N'])
        except ValueError:
            return float(dct['N'])
    if 'SS' in dct:
        return dct['SS']
    if 'NS' in dct:
        try:
            return map(int, dct['NS'])
        except ValueError:
            return map(float, dct['NS'])
    return dct

#
# To get full debug output, uncomment the following line and set the
# value of Debug to be 2
#
boto.set_stream_logger('dynamodb')
Debug=2

class DynamoDBConnection(AWSAuthConnection):
    DefaultHost = 'dynamodb.us-east-1.amazonaws.com'
    """The default DynamoDB API endpoint to connect to."""

    ServiceName = 'DynamoDB'
    """The name of the Service"""
    
    Version = '20110924'
    """DynamoDB API version."""
    
    ResponseError = DynamoDBResponseError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 host=DefaultHost, debug=Debug):
        self.sts = boto.connect_sts(aws_access_key_id, aws_secret_access_key)
        self.creds = self.sts.get_session_token()
        AWSAuthConnection.__init__(self, host,
                                   self.creds.access_key,
                                   self.creds.secret_key,
                                   is_secure, port, proxy, proxy_port,
                                   debug=debug,
                                   security_token=self.creds.session_token)

    def _required_auth_capability(self):
        return ['hmac-v3-http']

    def make_request(self, action, body='', object_hook=None):
        """Makes a request to the server, with stock multiple-retry logic."""
        headers = {'X-Amz-Target' : '%sv%s.%s' % (self.ServiceName,
                                                  self.Version, action),
                   'Content-Type' : 'application/x-amz-json-1.0',
                   'Content-Length' : str(len(body))}
        http_request = self.build_base_http_request('POST', '/', '/',
                                                    {}, headers, body, None)
        response = self._mexe(http_request, sender=None,
                              override_num_retries=0)
        body = response.read()
        boto.log.debug(body)
        json_response = json.loads(body, object_hook=object_hook)
        if response.status == 200:
            return json_response
        else:
            raise self.ResponseError(response.status, response.reason,
                                     json_response)

    def get_dynamodb_type(self, val):
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
        
    def dynamize_value(self, val):
        """
        Take a scalar Python value and return a dict consisting
        of the DynamoDB type specification and the value that
        needs to be sent to DynamoDB.  If the type of the value
        is not supported, raise a TypeError
        """
        dynamodb_type = self.get_dynamodb_type(val)
        if dynamodb_type == 'N':
            val = {dynamodb_type : '%d' % val}
        elif dynamodb_type == 'S':
            val = {dynamodb_type : val}
        elif dynamodb_type == 'NS':
            val = {dynamodb_type : [ str(n) for n in val]}
        elif dynamodb_type == 'SS':
            val = {dynamodb_type : val}
        return val
        
    def dynamize_item(self, item):
        """
        Take a normal Python dict and convert it into a structure
        required by DynamoDB.  For example, the input item
        {'foo' : 'item001', 'bar' : 42} would become
        {'foo' : {'S' : 'item001'}, 'bar' : {'N' : '42'}}.
        """
        dynamodb_item = {}
        for key in item:
            dynamodb_item[key] = self.dynamize_value(item[key])
        return dynamodb_item

    def dynamize_key(self, key):
        """
        Take a list of Python values and turn it into dict object as
        required by DynamoDB for Keys.  For example, the input item
        ['item001', 42] would become
        {'HashKeyElement':{'S':'item001'}, 'RangeKeyElement':{'N':'42'}}.
        """
        dynamodb_key = {}
        dynamodb_key['HashKeyElement'] = self.dynamize_value(key[0])
        if len(key) > 1:
            dynamodb_key['RangeKeyElement'] = self.dynamize_value(key[1])
        return dynamodb_key

    def dynamize_keys(self, keys):
        """
        """
        dynamodb_keys = {}
        for table_name in keys:
            dynamo_table = {}
            dynamo_keys[table_name] = dynamo_table
            l = []
            dynamo_keys[table_name]['Keys'] = l
            for key in keys[table_name]['Keys']:
                l.append(self.dynamize_key(key))
            if 'AttributesToGet' in keys[table_name]:
                value = keys[table_name]['AttributesToGet']
                dynamo_keys['AttributesToGet'] = value
        return dynamodb_keys

    def dynamize_throughput(self, throughput_tuple):
        """
        Take a list or tuple of integer values that represent the
        read and write provisioning for a table and return a dict
        formatted as required by DynamoDB.

        :type throughput_tuple: list or tuple
        :param throughput_tuple: A sequence containing two elements.
            The first is interpreted as the Read throughput and the
            second is interpreted as the Write throughput.
        """
        dynamodb_throughput = {}
        dynamodb_throughput['ReadsPerSecond'] = throughput_tuple[0]
        dynamodb_throughput['WritesPerSecond'] = throughput_tuple[1]
        return dynamodb_throughput

    def dynamize_schema(self, schema):
        """
        Takes a list of lists or tuples as passed to create_table
        and turns it into a dict structure as required by DynamoDB.
        
        :param schema: A list of lists or tuples.  The first tuple
            consists of a key name and a prototypical value and is used
            for the HashKey of the new table.  The second tuple, if present,
            also consists of a key name and a prototypical value and is
            used for the RangeKey of the new table.  For example:
        """
        dynamodb_schema = {}
        hash_key = {'AttributeName' : schema[0][0],
                    'AttributeType' : self.get_dynamodb_type(schema[0][1])}
        dynamodb_schema['HashKeyElement'] = hash_key
        if len(schema) > 1:
            range_key = {'AttributeName' : schema[1][0],
                         'AttributeType' : self.get_dynamodb_type(schema[1][1])}
            dynamodb_schema['RangeKeyElement'] = range_key
        return dynamodb_schema

    def dynamize_expected(self, expected):
        """
        Take a dict of expected values and turn that into
        a format required by DynamoDB.  Each key in the dict
        represents an AttributeName.  If the value is None,
        it means you are expecting the value not to exist.
        If the value is non-None, it is used as the expected
        value of the Attribute.
        """
        dynamodb_expected = {}
        for key in expected:
            value = expected[key]
            if value is None:
                dynamodb_expected[key] = {'Exists': False}
            else:
                dynamodb_expected[key] = {'Value': self.dynamize_value(value)}
        return dynamodb_expected

    def list_tables(self, limit=None, start_table=None):
        """
        Return an list of tables associated with the current account
        and endpoint.

        :type limit: int
        :param limit: The maximum number of tables to return.

        :type start_table: str
        :param limit: The name of the table that starts the
            list.  If you ran a previous list_tables and not
            all results were returned, the response dict would
            include a LastEvaluatedTableName attribute.  Use
            that value here to continue the listing.
        """
        data = {}
        if limit:
            data['Limit'] = limit
        if start_table:
            data['ExclusiveStartTableName'] = start_table
        json_input = json.dumps(data)
        return self.make_request('ListTables', json_input)

    def describe_table(self, table_name):
        """
        Returns information about the table including current
        state of the table, primary key schema and when the
        table was created.

        :type table_name: str
        :param table_name: The name of the table to delete.
        """
        data = {'TableName' : table_name}
        json_input = json.dumps(data)
        return self.make_request('DescribeTable', json_input)

    def create_table(self, table_name, schema, provisioned_throughput):
        """
        Add a new table to your account.  The table name must be unique
        among those associated with the account issuing the request.
        This request triggers an asynchronous workflow to begin creating
        the table.  When the workflow is complete, the state of the
        table will be ACTIVE.

        :type table_name: str
        :param table_name: The name of the table to delete.
        
        :type schema: list
        :param schema: A list of lists or tuples.  The first tuple
            consists of a key name and a prototypical value and is used
            for the HashKey of the new table.  The second tuple, if present,
            also consists of a key name and a prototypical value and is
            used for the RangeKey of the new table.  For example:

            [('foo', 1), ('bar', 'baz')]

            Would create a HashKey called 'foo' of type 'N' and a
            RangeKey called 'bar' of type 'S'.

        :type provisioned_throughput: list or tuple
        :param provisioned_throughput: A sequence containing two elements.
            The first is interpreted as the Read throughput and the
            second is interpreted as the Write throughput.
        
        """
        schema = self.dynamize_schema(schema)
        thruput = self.dynamize_throughput(provisioned_throughput)
        data = {'TableName' : table_name,
                'KeySchema' : schema,
                'ProvisionedThroughput' : thruput}
        json_input = json.dumps(data)
        return self.make_request('CreateTable', json_input)

    def update_table(self, table_name, provisioned_throughput):
        """
        Updates the provisioned throughput for a given table.
        
        :type table_name: str
        :param table_name: The name of the table to delete.
        
        :type provisioned_throughput: list or tuple
        :param provisioned_throughput: A sequence containing two elements.
            The first is interpreted as the Read throughput and the
            second is interpreted as the Write throughput.
        """
        thruput = self.dynamize_throughput(provisioned_throughput)
        data = {'TableName' : table_name,
                'ProvisionedThroughput' : thruput}
        json_input = json.dumps(data)
        return self.make_request('UpdateTable', json_input)

    def delete_table(self, table_name):
        """
        Deletes the table and all of it's data.  After this request
        the table will be in the DELETING state until DynamoDB
        completes the delete operation.

        :type table_name: str
        :param table_name: The name of the table to delete.
        """
        data = {'TableName' : table_name}
        json_input = json.dumps(data)
        return self.make_request('DeleteTable', json_input)

    def get_item(self, table_name, key, attributes_to_get=None,
                 consistent_read=False):
        """
        Return a set of attributes for an item that matches
        the supplied key.

        :type table_name: str
        :param table_name: The name of the table to delete.

        :type key: list
        :param key: A list of values where the first value
            is interpreted to be the hash key and the second value,
            if supplied, is interpreted to be the range key.

        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.

        :type consistent_read: bool
        :param consistent_read: If True, a consistent read
            request is issued.  Otherwise, an eventually consistent
            request is issued.
        """
        dynamodb_key = self.dynamize_key(key)
        data = {'TableName' : table_name,
                'Key' : dynamodb_key}
        if attributes_to_get:
            data['AttributesToGet'] = attributes_to_get
        if consistent_read:
            data['ConsistentRead'] = True
        json_input = json.dumps(data)
        return self.make_request('GetItem', json_input,
                                 object_hook=item_object_hook)
        
    def batch_get_item(self, table_name, keys):
        """
        Return a set of attributes for a multiple items in
        multiple tables using their primary keys.

        :type keys: dict
        :param keys:A dict where the key is the table name
            and the value is another dict with the following
            keys:

            Keys - which is a list of lists where each
            inner list contains either a hash key and a range
            key or just a hash key.

            AttributesToGet - which is a list of attribute
            names that will be retrieved for each item.

        """
        dynamodb_keys = self.dynamize_keys(keys)
        data = {'TableName' : table_name,
                'RequestItems' : dynamodb_keys}
        json_input = json.dumps(data)
        return self.make_request('BatchGetItem', json_input)
        
    def put_item(self, table_name, item,
                 expected=None, return_values=None):
        """
        Create a new item or replace an old item with a new
        item (including all attributes).  If an item already
        exists in the specified table with the same primary
        key, the new item will completely replace the old item.
        You can perform a conditional put by specifying an
        expected rule.

        :type table_name: str
        :param table_name: The name of the table to delete.

        :type item: dict
        :param item: A dict containing the new item attributes.
            This must include a primary key value.  Other attributes
            can also be provided.

        :type expected: dict
        :param expected: A dict of expected values.
            Each key in the dict represents an AttributeName.
            If the value is None, it means you are expecting the
            value not to exist.  If the value is non-None, it is
            used as the expected value of the Attribute.

        :type return_values: str
        :param return_values: Controls the return of attribute
            name-value pairs before then were changed.  Possible
            values are: None or 'ALL_OLD'. If 'ALL_OLD' is
            specified and the item is overwritten, the content
            of the old item is returned.
        """
        dynamodb_item = self.dynamize_item(item)
        data = {'TableName' : table_name,
                'Item' : dynamodb_item}
        if expected:
            data['Expected'] = self.dynamize_expected(expected)
        if return_values:
            data['ReturnValues'] = return_values
        json_input = json.dumps(data)
        return self.make_request('PutItem', json_input)

    def delete_item(self, table_name, key,
                    expected=None, return_values=None):
        """
        Delete an item and all of it's attributes by primary key.
        You can perform a conditional delete by specifying an
        expected rule.

        :type table_name: str
        :param table_name: The name of the table to delete.

        :type key: list
        :param key: A list of values where the first value
            is interpreted to be the hash key and the second value,
            if supplied, is interpreted to be the range key.

        :type expected: dict
        :param expected: Designates an attribute for a conditional
            put.  You can provide an attribute name and whether or
            not DynamoDB should check to see if the attribute
            already exists or if the attribute value is known to
            exist, if the attribute has a particular value before
            changing it.

        :type return_values: str
        :param return_values: Controls the return of attribute
            name-value pairs before then were changed.  Possible
            values are: None or 'ALL_OLD'. If 'ALL_OLD' is
            specified and the item is overwritten, the content
            of the old item is returned.
        """
        dynamodb_key = self.dynamize_key(key)
        data = {'TableName' : table_name,
                'Key' : dynamodb_key}
        if expected:
            data['Expected'] = expected
        if return_values:
            data['ReturnValues'] = return_values
        json_input = json.dumps(data)
        return self.make_request('DeleteItem', json_input)

    def query_raw(self, json_body):
        """
        Perform a query of DynamoDB.  This version is currently punting
        and expecting you to provide a full and correct JSON body
        which is passed as is to DynamoDB.
        """
        return self.make_request('Query', json_body)

    def query(self, table_name, hash_key_value, range_key_conditions=None,
              attributes_to_get=None, limit=None, consistent_read=False,
              scan_index_forward=True, exclusive_start_key=None):
        """
        Perform a query of DynamoDB.  This version is currently punting
        and expecting you to provide a full and correct JSON body
        which is passed as is to DynamoDB.

        :type table_name: str
        :param table_name: The name of the table to delete.

        :type hash_key_value: str or int or float
        :param key: The value of the HashKey you are searching for.

        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.

        :type limit: int
        :param limit: The maximum number of items to return.

        :type consistent_read: bool
        :param consistent_read: If True, a consistent read
            request is issued.  Otherwise, an eventually consistent
            request is issued.

        :type scan_index_forward: bool
        :param scan_index_forward: Specified forward or backward
            traversal of the index.  Default is forward (True).

        :type exclusive_start_key: list or tuple
        :param exclusive_start_key: Primary key of the item from
            which to continue an earlier query.  This would be
            provided as the LastEvaluatedKey in that query.
        """
        data = {'TableName': table_name,
                'HashKeyValue': self.dynamize_value(hash_key_value)}
        if attributes_to_get:
            data['AttributesToGet'] = attributes_to_get
        if consistent_read:
            data['ConsistentRead'] = True
        if scan_index_forward:
            data['ScanIndexForward'] = True
        else:
            data['ScanIndexForward'] = True
        if exclusive_start_key:
            data['ExclusiveStartKey'] = self.dynamize_key(exclusive_start_key)
        json_input = json.dumps(data)
        return self.make_request('Query', json_input)

    def scan(self, json_body):
        """
        Perform a scan of DynamoDB.  This version is currently punting
        and expecting you to provide a full and correct JSON body
        which is passed as is to DynamoDB.
        """
        return self.make_request('Scan', json_body)
    
