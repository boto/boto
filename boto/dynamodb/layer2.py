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

from boto.dynamodb.layer1 import Layer1
from boto.dynamodb.table import Table
from boto.dynamodb.schema import Schema
from boto.dynamodb.item import Item
from boto.dynamodb.batch import BatchList

"""
Some utility functions to deal with mapping Amazon DynamoDB types to
Python types and vice-versa.
"""

def is_num(n):
    return isinstance(n, (int, long, float, bool))

def is_str(n):
    return isinstance(n, basestring)

def convert_num(s):
    if '.' in s:
        n = float(s)
    else:
        n = int(s)
    return n

def item_object_hook(dct):
    """
    A custom object hook for use when decoding JSON item bodys.
    This hook will transform Amazon DynamoDB JSON responses to something
    that maps directly to native Python types.
    """
    if len(dct.keys()) > 1:
        return dct
    if 'S' in dct:
        return dct['S']
    if 'N' in dct:
        return convert_num(dct['N'])
    if 'SS' in dct:
        return set(dct['SS'])
    if 'NS' in dct:
        return set(map(convert_num, dct['NS']))
    return dct

class Layer2(object):

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 host=None, debug=0, session_token=None):
        self.layer1 = Layer1(aws_access_key_id, aws_secret_access_key,
                             is_secure, port, proxy, proxy_port,
                             host, debug, session_token)

    def dynamize_attribute_updates(self, pending_updates):
        """
        Convert a set of pending item updates into the structure
        required by Layer1.
        """
        d = {}
        for attr_name in pending_updates:
            action, value = pending_updates[attr_name]
            if value is None:
                # DELETE without an attribute value
                d[attr_name] = {"Action": action}
            else:
                d[attr_name] = {"Action": action,
                                "Value": self.dynamize_value(value)}
        return d

    def dynamize_item(self, item):
        d = {}
        for attr_name in item:
            d[attr_name] = self.dynamize_value(item[attr_name])
        return d

    def dynamize_range_key_condition(self, range_key_condition):
        """
        Convert a layer2 range_key_condition parameter into the
        structure required by Layer1.
        """
        d = None
        if range_key_condition:
            d = {}
            for range_value in range_key_condition:
                range_condition = range_key_condition[range_value]
                if range_condition == 'BETWEEN':
                    if isinstance(range_value, tuple):
                        avl = [self.dynamize_value(v) for v in range_value]
                    else:
                        msg = 'BETWEEN condition requires a tuple value'
                        raise TypeError(msg)
                elif isinstance(range_value, tuple):
                    msg = 'Tuple can only be supplied with BETWEEN condition'
                    raise TypeError(msg)
                else:
                    avl = [self.dynamize_value(range_value)]
            d = {'AttributeValueList': avl,
                 'ComparisonOperator': range_condition}
        return d

    def dynamize_scan_filter(self, scan_filter):
        """
        Convert a layer2 scan_filter parameter into the
        structure required by Layer1.
        """
        d = None
        if scan_filter:
            d = {}
            for attr_name, op, value in scan_filter:
                if op == 'BETWEEN':
                    if isinstance(value, tuple):
                        avl = [self.dynamize_value(v) for v in value]
                    else:
                        msg = 'BETWEEN condition requires a tuple value'
                        raise TypeError(msg)
                elif op == 'NULL' or op == 'NOT_NULL':
                    avl = None
                elif isinstance(value, tuple):
                    msg = 'Tuple can only be supplied with BETWEEN condition'
                    raise TypeError(msg)
                else:
                    avl = [self.dynamize_value(value)]
            dd = {'ComparisonOperator': op}
            if avl:
                dd['AttributeValueList'] = avl
            d[attr_name] = dd
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
                    val = self.dynamize_value(expected_value[attr_name])
                    attr_value = {'Value': val}
                d[attr_name] = attr_value
        return d

    def dynamize_last_evaluated_key(self, last_evaluated_key):
        """
        Convert a last_evaluated_key parameter into the data structure
        required for Layer1.
        """
        d = None
        if last_evaluated_key:
            hash_key = last_evaluated_key['HashKeyElement']
            d = {'HashKeyElement': self.dynamize_value(hash_key)}
            if 'RangeKeyElement' in last_evaluated_key:
                range_key = last_evaluated_key['RangeKeyElement']
                d['RangeKeyElement'] = self.dynamize_value(range_key)
        return d

    def dynamize_request_items(self, batch_list):
        """
        Convert a request_items parameter into the data structure
        required for Layer1.
        """
        d = None
        if batch_list:
            d = {}
            for batch in batch_list:
                batch_dict = {}
                key_list = []
                for key in batch.keys:
                    if isinstance(key, tuple):
                        hash_key, range_key = key
                    else:
                        hash_key = key
                        range_key = None
                    k = self.build_key_from_values(batch.table.schema,
                                                   hash_key, range_key)
                    key_list.append(k)
                batch_dict['Keys'] = key_list
                if batch.attributes_to_get:
                    batch_dict['AttributesToGet'] = batch.attributes_to_get
            d[batch.table.name] = batch_dict
        return d

    def get_dynamodb_type(self, val):
        """
        Take a scalar Python value and return a string representing
        the corresponding Amazon DynamoDB type.  If the value passed in is
        not a supported type, raise a TypeError.
        """
        dynamodb_type = None
        if is_num(val):
            dynamodb_type = 'N'
        elif is_str(val):
            dynamodb_type = 'S'
        elif isinstance(val, (set, frozenset)):
            if False not in map(is_num, val):
                dynamodb_type = 'NS'
            elif False not in map(is_str, val):
                dynamodb_type = 'SS'
        if dynamodb_type is None:
            raise TypeError('Unsupported type "%s" for value "%s"' % (type(val), val))
        return dynamodb_type

    def dynamize_value(self, val):
        """
        Take a scalar Python value and return a dict consisting
        of the Amazon DynamoDB type specification and the value that
        needs to be sent to Amazon DynamoDB.  If the type of the value
        is not supported, raise a TypeError
        """
        def _str(val):
            """
            DynamoDB stores booleans as numbers. True is 1, False is 0.
            This function converts Python booleans into DynamoDB friendly
            representation.
            """
            if isinstance(val, bool):
                return str(int(val))
            return str(val)

        dynamodb_type = self.get_dynamodb_type(val)
        if dynamodb_type == 'N':
            val = {dynamodb_type : _str(val)}
        elif dynamodb_type == 'S':
            val = {dynamodb_type : val}
        elif dynamodb_type == 'NS':
            val = {dynamodb_type : [ str(n) for n in val]}
        elif dynamodb_type == 'SS':
            val = {dynamodb_type : [ n for n in val]}
        return val

    def build_key_from_values(self, schema, hash_key, range_key=None):
        """
        Build a Key structure to be used for accessing items
        in Amazon DynamoDB.  This method takes the supplied hash_key
        and optional range_key and validates them against the
        schema.  If there is a mismatch, a TypeError is raised.
        Otherwise, a Python dict version of a Amazon DynamoDB Key
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
        dynamodb_value = self.dynamize_value(hash_key)
        if dynamodb_value.keys()[0] != schema.hash_key_type:
            msg = 'Hashkey must be of type: %s' % schema.hash_key_type
            raise TypeError(msg)
        dynamodb_key['HashKeyElement'] = dynamodb_value
        if range_key is not None:
            dynamodb_value = self.dynamize_value(range_key)
            if dynamodb_value.keys()[0] != schema.range_key_type:
                msg = 'RangeKey must be of type: %s' % schema.range_key_type
                raise TypeError(msg)
            dynamodb_key['RangeKeyElement'] = dynamodb_value
        return dynamodb_key

    def new_batch_list(self):
        """
        Return a new, empty :class:`boto.dynamodb.batch.BatchList`
        object.
        """
        return BatchList(self)

    def list_tables(self, limit=None, start_table=None):
        """
        Return a list of the names of all Tables associated with the
        current account and region.
        TODO - Layer2 should probably automatically handle pagination.

        :type limit: int
        :param limit: The maximum number of tables to return.

        :type start_table: str
        :param limit: The name of the table that starts the
            list.  If you ran a previous list_tables and not
            all results were returned, the response dict would
            include a LastEvaluatedTableName attribute.  Use
            that value here to continue the listing.
        """
        result = self.layer1.list_tables(limit, start_table)
        return result['TableNames']

    def describe_table(self, name):
        """
        Retrieve information about an existing table.

        :type name: str
        :param name: The name of the desired table.

        """
        return self.layer1.describe_table(name)

    def get_table(self, name):
        """
        Retrieve the Table object for an existing table.

        :type name: str
        :param name: The name of the desired table.

        :rtype: :class:`boto.dynamodb.table.Table`
        :return: A Table object representing the table.
        """
        response = self.layer1.describe_table(name)
        return Table(self,  response)

    lookup = get_table
    def create_table(self, name, schema, read_units, write_units):
        """
        Create a new Amazon DynamoDB table.
        
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
        :return: A Table object representing the new Amazon DynamoDB table.
        """
        response = self.layer1.create_table(name, schema.dict,
                                            {'ReadCapacityUnits': read_units,
                                             'WriteCapacityUnits': write_units})
        return Table(self,  response)

    def update_throughput(self, table, read_units, write_units):
        """
        Update the ProvisionedThroughput for the Amazon DynamoDB Table.

        :type table: :class:`boto.dynamodb.table.Table`
        :param table: The Table object whose throughput is being updated.
        
        :type read_units: int
        :param read_units: The new value for ReadCapacityUnits.
        
        :type write_units: int
        :param write_units: The new value for WriteCapacityUnits.
        """
        response = self.layer1.update_table(table.name,
                                            {'ReadCapacityUnits': read_units,
                                             'WriteCapacityUnits': write_units})
        table.update_from_response(response['TableDescription'])
        
    def delete_table(self, table):
        """
        Delete this table and all items in it.  After calling this
        the Table objects status attribute will be set to 'DELETING'.

        :type table: :class:`boto.dynamodb.table.Table`
        :param table: The Table object that is being deleted.
        """
        response = self.layer1.delete_table(table.name)
        table.update_from_response(response)

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
        hash_key_type = self.get_dynamodb_type(hash_key_proto_value)
        hash_key['AttributeType'] = hash_key_type
        schema['HashKeyElement'] = hash_key
        if range_key_name and range_key_proto_value is not None:
            range_key = {}
            range_key['AttributeName'] = range_key_name
            range_key_type = self.get_dynamodb_type(range_key_proto_value)
            range_key['AttributeType'] = range_key_type
            schema['RangeKeyElement'] = range_key
        return Schema(schema)

    def get_item(self, table, hash_key, range_key=None,
                 attributes_to_get=None, consistent_read=False,
                 item_class=Item):
        """
        Retrieve an existing item from the table.

        :type table: :class:`boto.dynamodb.table.Table`
        :param table: The Table object from which the item is retrieved.
        
        :type hash_key: int|long|float|str|unicode
        :param hash_key: The HashKey of the requested item.  The
            type of the value must match the type defined in the
            schema for the table.
        
        :type range_key: int|long|float|str|unicode
        :param range_key: The optional RangeKey of the requested item.
            The type of the value must match the type defined in the
            schema for the table.
            
        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.

        :type consistent_read: bool
        :param consistent_read: If True, a consistent read
            request is issued.  Otherwise, an eventually consistent
            request is issued.

        :type item_class: Class
        :param item_class: Allows you to override the class used
            to generate the items. This should be a subclass of
            :class:`boto.dynamodb.item.Item`
        """
        key = self.build_key_from_values(table.schema, hash_key, range_key)
        response = self.layer1.get_item(table.name, key,
                                        attributes_to_get, consistent_read,
                                        object_hook=item_object_hook)
        item = item_class(table, hash_key, range_key, response['Item'])
        if 'ConsumedCapacityUnits' in response:
            item.consumed_units = response['ConsumedCapacityUnits']
        return item

    def batch_get_item(self, batch_list):
        """
        Return a set of attributes for a multiple items in
        multiple tables using their primary keys.

        :type batch_list: :class:`boto.dynamodb.batch.BatchList`
        :param batch_list: A BatchList object which consists of a
            list of :class:`boto.dynamoddb.batch.Batch` objects.
            Each Batch object contains the information about one
            batch of objects that you wish to retrieve in this
            request.
        """
        request_items = self.dynamize_request_items(batch_list)
        return self.layer1.batch_get_item(request_items,
                                          object_hook=item_object_hook)

    def put_item(self, item, expected_value=None, return_values=None):
        """
        Store a new item or completely replace an existing item
        in Amazon DynamoDB.

        :type item: :class:`boto.dynamodb.item.Item`
        :param item: The Item to write to Amazon DynamoDB.
        
        :type expected_value: dict
        :param expected_value: A dictionary of name/value pairs that you expect.
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
        expected_value = self.dynamize_expected_value(expected_value)
        response = self.layer1.put_item(item.table.name,
                                        self.dynamize_item(item),
                                        expected_value, return_values,
                                        object_hook=item_object_hook)
        if 'ConsumedCapacityUnits' in response:
            item.consumed_units = response['ConsumedCapacityUnits']
        return response
            
    def update_item(self, item, expected_value=None, return_values=None):
        """
        Commit pending item updates to Amazon DynamoDB.

        :type item: :class:`boto.dynamodb.item.Item`
        :param item: The Item to update in Amazon DynamoDB.  It is expected
            that you would have called the add_attribute, put_attribute
            and/or delete_attribute methods on this Item prior to calling
            this method.  Those queued changes are what will be updated.

        :type expected_value: dict
        :param expected_value: A dictionary of name/value pairs that you
            expect.  This dictionary should have name/value pairs where the
            name is the name of the attribute and the value is either the
            value you are expecting or False if you expect the attribute
            not to exist.

        :type return_values: str
        :param return_values: Controls the return of attribute name/value pairs
            before they were updated. Possible values are: None, 'ALL_OLD',
            'UPDATED_OLD', 'ALL_NEW' or 'UPDATED_NEW'. If 'ALL_OLD' is
            specified and the item is overwritten, the content of the old item
            is returned. If 'ALL_NEW' is specified, then all the attributes of
            the new version of the item are returned. If 'UPDATED_NEW' is
            specified, the new versions of only the updated attributes are
            returned.

        """
        expected_value = self.dynamize_expected_value(expected_value)
        key = self.build_key_from_values(item.table.schema,
                                         item.hash_key, item.range_key)
        attr_updates = self.dynamize_attribute_updates(item._updates)

        response = self.layer1.update_item(item.table.name, key,
                                           attr_updates,
                                           expected_value, return_values,
                                           object_hook=item_object_hook)
        item._updates.clear()
        if 'ConsumedCapacityUnits' in response:
            item.consumed_units = response['ConsumedCapacityUnits']
        return response
            
    def delete_item(self, item, expected_value=None, return_values=None):
        """
        Delete the item from Amazon DynamoDB.

        :type item: :class:`boto.dynamodb.item.Item`
        :param item: The Item to delete from Amazon DynamoDB.
        
        :type expected_value: dict
        :param expected_value: A dictionary of name/value pairs that you expect.
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
        expected_value = self.dynamize_expected_value(expected_value)
        key = self.build_key_from_values(item.table.schema,
                                         item.hash_key, item.range_key)
        return self.layer1.delete_item(item.table.name, key,
                                       expected=expected_value,
                                       return_values=return_values,
                                       object_hook=item_object_hook)

    def query(self, table, hash_key, range_key_condition=None,
              attributes_to_get=None, request_limit=None,
              max_results=None, consistent_read=False,
              scan_index_forward=True, exclusive_start_key=None,
              item_class=Item):
        """
        Perform a query on the table.
        
        :type table: :class:`boto.dynamodb.table.Table`
        :param table: The Table object that is being queried.
        
        :type hash_key: int|long|float|str|unicode
        :param hash_key: The HashKey of the requested item.  The
            type of the value must match the type defined in the
            schema for the table.

        :type range_key_condition: dict
        :param range_key_condition: A dict where the key is either
            a scalar value appropriate for the RangeKey in the schema
            of the database or a tuple of such values.  The value 
            associated with this key in the dict will be one of the
            following conditions:

            'EQ'|'LE'|'LT'|'GE'|'GT'|'BEGINS_WITH'|'BETWEEN'

            The only condition which expects or will accept a tuple
            of values is 'BETWEEN', otherwise a scalar value should
            be used as the key in the dict.
        
        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.

        :type request_limit: int
        :param request_limit: The maximum number of items to retrieve
            from Amazon DynamoDB on each request.  You may want to set
            a specific request_limit based on the provisioned throughput
            of your table.  The default behavior is to retrieve as many
            results as possible per request.

        :type max_results: int
        :param max_results: The maximum number of results that will
            be retrieved from Amazon DynamoDB in total.  For example,
            if you only wanted to see the first 100 results from the
            query, regardless of how many were actually available, you
            could set max_results to 100 and the generator returned
            from the query method will only yeild 100 results max.

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

        :type item_class: Class
        :param item_class: Allows you to override the class used
            to generate the items. This should be a subclass of
            :class:`boto.dynamodb.item.Item`

        :rtype: generator
        """
        rkc = self.dynamize_range_key_condition(range_key_condition)
        response = True
        n = 0
        while response:
            if response is True:
                pass
            elif response.has_key("LastEvaluatedKey"):
                lek = response['LastEvaluatedKey']
                exclusive_start_key = self.dynamize_last_evaluated_key(lek)
            else:
                break
            response = self.layer1.query(table.name,
                                         self.dynamize_value(hash_key),
                                         rkc, attributes_to_get, request_limit,
                                         consistent_read, scan_index_forward,
                                         exclusive_start_key,
                                         object_hook=item_object_hook)
            for item in response['Items']:
                if max_results and n == max_results:
                    break
                yield item_class(table, attrs=item)
                n += 1
    
    def scan(self, table, scan_filter=None,
             attributes_to_get=None, request_limit=None, max_results=None,
             count=False, exclusive_start_key=None, item_class=Item):
        """
        Perform a scan of DynamoDB.

        :type table: :class:`boto.dynamodb.table.Table`
        :param table: The Table object that is being scanned.

        :type scan_filter: A list of tuples
        :param scan_filter: A list of tuples where each tuple consists
            of an attribute name, a comparison operator, and either
            a scalar or tuple consisting of the values to compare
            the attribute to.  Valid comparison operators are shown below
            along with the expected number of values that should be supplied.

             * EQ - equal (1)
             * NE - not equal (1)
             * LE - less than or equal (1)
             * LT - less than (1)
             * GE - greater than or equal (1)
             * GT - greater than (1)
             * NOT_NULL - attribute exists (0, use None)
             * NULL - attribute does not exist (0, use None)
             * CONTAINS - substring or value in list (1)
             * NOT_CONTAINS - absence of substring or value in list (1)
             * BEGINS_WITH - substring prefix (1)
             * IN - exact match in list (N)
             * BETWEEN - >= first value, <= second value (2)

        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.

        :type request_limit: int
        :param request_limit: The maximum number of items to retrieve
            from Amazon DynamoDB on each request.  You may want to set
            a specific request_limit based on the provisioned throughput
            of your table.  The default behavior is to retrieve as many
            results as possible per request.

        :type max_results: int
        :param max_results: The maximum number of results that will
            be retrieved from Amazon DynamoDB in total.  For example,
            if you only wanted to see the first 100 results from the
            query, regardless of how many were actually available, you
            could set max_results to 100 and the generator returned
            from the query method will only yeild 100 results max.

        :type count: bool
        :param count: If True, Amazon DynamoDB returns a total
            number of items for the Scan operation, even if the
            operation has no matching items for the assigned filter.

        :type exclusive_start_key: list or tuple
        :param exclusive_start_key: Primary key of the item from
            which to continue an earlier query.  This would be
            provided as the LastEvaluatedKey in that query.

        :type item_class: Class
        :param item_class: Allows you to override the class used
            to generate the items. This should be a subclass of
            :class:`boto.dynamodb.item.Item`

        :rtype: generator
        """
        sf = self.dynamize_scan_filter(scan_filter)
        response = True
        n = 0
        while response:
            if response is True:
                pass
            elif response.has_key("LastEvaluatedKey"):
                exclusive_start_key = response['LastEvaluatedKey']
            else:
                break

            response = self.layer1.scan(table.name, sf,
                                        attributes_to_get,request_limit,
                                        count, exclusive_start_key,
                                        object_hook=item_object_hook)
            if response:
                for item in response['Items']:
                    if max_results and n == max_results:
                        break
                    yield item_class(table, attrs=item)
                    n += 1

