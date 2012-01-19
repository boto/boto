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

from schema import Schema
from item import Item
from utils import item_object_hook, dynamize_value
import time
from boto.dynamodb import exceptions as dynamodb_exceptions

class Table(object):
    """
    A DynamoDB table.

    :ivar name: The name of the table.
    :ivar create_time: The date and time that the table was created.
    :ivar status: The current status of the table.  One of:
        'ACTIVE', 'UPDATING', 'DELETING'.
    :ivar schema: A :class:`boto.dynamodb.schema.Schema` object representing
        the schema defined for the table.
    :ivar item_count: The number of items in the table.  This value is
        set only when the Table object is created or refreshed and
        may not reflect the actual count.
    """

    def __init__(self, layer1, table_dict=None):
        self.layer1 = layer1
        self._dict = {}
        self._update(table_dict)

    def _update(self, response):
        if 'Table' in response:
            self._dict.update(response['Table'])
        elif 'TableDescription' in response:
            self._dict.update(response['TableDescription'])
        if 'KeySchema' in self._dict:
            self._schema = Schema(self._dict['KeySchema'])

    def __repr__(self):
        return 'Table(%s)' % self.name

    @property
    def name(self):
        return self._dict['TableName']
    
    @property
    def create_time(self):
        return self._dict['CreationDateTime']
    
    @property
    def status(self):
        return self._dict['TableStatus']
    
    @property
    def item_count(self):
        return self._dict['ItemCount']
    
    @property
    def size_bytes(self):
        return self._dict['TableSizeBytes']
    
    @property
    def schema(self):
        return self._schema

    @property
    def read_units(self):
        return self._dict['ProvisionedThroughput']['ReadCapacityUnits']
    
    @property
    def write_units(self):
        return self._dict['ProvisionedThroughput']['WriteCapacityUnits']
    
    def dynamize_range_key_condition(self, range_key_condition):
        """
        Convert a range_key_condition parameter into the
        structure required by Layer1.
        """
        d = None
        if range_key_condition:
            d = {}
            for range_value in range_key_condition:
                range_condition = range_key_condition[range_value]
                if range_condition == 'BETWEEN':
                    if isinstance(range_value, tuple):
                        avl = [dynamize_value(v) for v in range_value]
                    else:
                        msg = 'BETWEEN condition requires a tuple value'
                        raise TypeError(msg)
                elif isinstance(range_value, tuple):
                    msg = 'Tuple can only be supplied with BETWEEN condition'
                    raise TypeError(msg)
                else:
                    avl = [dynamize_value(range_value)]
            d['RangeKeyCondition'] = {'AttributeValueList': avl,
                                      'ComparisonOperator': range_condition}
        return d

    def refresh(self, wait_for_active=False, retry_seconds=5):
        """
        Refresh all of the fields of the Table object by calling
        the underlying DescribeTable request.

        :type wait_for_active: bool
        :param wait_for_active: If True, this command will not return
            until the table status, as returned from DynamoDB, is
            'ACTIVE'.

        :type retry_seconds: int
        :param retry_seconds: If wait_for_active is True, this
            parameter controls the number of seconds of delay between
            calls to update_table in DynamoDB.  Default is 5 seconds.
        """
        done = False
        while not done:
            response = self.layer1.describe_table(self.name)
            self._update(response)
            if wait_for_active:
                if self.status == 'ACTIVE':
                    done = True
                else:
                    time.sleep(retry_seconds)
            else:
                done = True

    def update_throughput(self, read_units, write_units):
        """
        Update the ProvisionedThroughput for the DynamoDB Table.

        :type read_units: int
        :param read_units: The new value for ReadCapacityUnits.
        
        :type write_units: int
        :param write_units: The new value for WriteCapacityUnits.
        """
        response = self.layer1.update_table(self.name,
                                            {'ReadCapacityUnits': read_units,
                                             'WriteCapacityUnits': write_units})
        self._update(response['TableDescription'])
        
    def delete(self):
        """
        Delete this table and all items in it.  After calling this
        the Table objects status attribute will be set to 'DELETING'.
        """
        response = self.layer1.delete_table(self.name)
        self._update(response)

    def get_item(self, hash_key, range_key=None,
                 attributes_to_get=None, consistent_read=False):
        """
        Retrieve an existing item from the table.

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
        """
        key = self.schema.build_key_from_values(hash_key, range_key)
        response = self.layer1.get_item(self.name, key,
                                        attributes_to_get, consistent_read,
                                        object_hook=item_object_hook)
        item = Item(self, hash_key, range_key, response['Item'])
        if 'ConsumedCapacityUnits' in response:
            item.consumed_units = response['ConsumedCapacityUnits']
        return item

    def has_item(self, hash_key, range_key=None, consistent_read=False):
        """
        Checks the table to see if the Item with the specified ``hash_key``
        exists. This may save a tiny bit of time/bandwidth over a
        straight :py:meth:`get_item` if you have no intention to touch
        the data that is returned, since this method specifically tells
        Amazon not to return anything but the Item's key.

        :type hash_key: int|long|float|str|unicode
        :param hash_key: The HashKey of the requested item.  The
            type of the value must match the type defined in the
            schema for the table.

        :type range_key: int|long|float|str|unicode
        :param range_key: The optional RangeKey of the requested item.
            The type of the value must match the type defined in the
            schema for the table.

        :type consistent_read: bool
        :param consistent_read: If True, a consistent read
            request is issued.  Otherwise, an eventually consistent
            request is issued.

        :rtype: bool
        :returns: ``True`` if the Item exists, ``False`` if not.
        """
        try:
            # Attempt to get the key. If it can't be found, it'll raise
            # an exception.
            self.get_item(hash_key, range_key=range_key,
                          # This minimizes the size of the response body.
                          attributes_to_get=[hash_key],
                          consistent_read=consistent_read)
        except dynamodb_exceptions.DynamoDBKeyNotFoundError:
            # Key doesn't exist.
            return False
        return True

    def new_item(self, hash_key, range_key=None, attrs=None):
        """
        Return an new, unsaved Item which can later be PUT to DynamoDB.
        """
        return Item(self, hash_key, range_key, attrs)

    def query(self, hash_key, range_key_condition=None,
              attributes_to_get=None, limit=None, consistent_read=False,
              scan_index_forward=True, exclusive_start_key=None):
        """
        Perform a query on the table.
        
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
        rkc = self.dynamize_range_key_condition(range_key_condition)
        response = self.layer1.query(self.name, dynamize_value(hash_key),
                                     rkc, attributes_to_get, limit,
                                     consistent_read, scan_index_forward,
                                     exclusive_start_key,
                                     object_hook=item_object_hook)
        items = []
        for item in response['Items']:
            hash_key = item[self.schema.hash_key_name]
            range_key = item[self.schema.range_key_name]
            items.append(Item(self, hash_key, range_key, item))
        return items

    def scan(self):
        pass
        


        
        

