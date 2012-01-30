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

from boto.dynamodb.schema import Schema
from boto.dynamodb.item import Item
from boto.dynamodb import exceptions as dynamodb_exceptions
import time

class Table(object):
    """
    An Amazon DynamoDB table.

    :ivar name: The name of the table.
    :ivar create_time: The date and time that the table was created.
    :ivar status: The current status of the table.  One of:
        'ACTIVE', 'UPDATING', 'DELETING'.
    :ivar schema: A :class:`boto.dynamodb.schema.Schema` object representing
        the schema defined for the table.
    :ivar item_count: The number of items in the table.  This value is
        set only when the Table object is created or refreshed and
        may not reflect the actual count.
    :ivar size_bytes: Total size of the specified table, in bytes.
        Amazon DynamoDB updates this value approximately every six hours.
        Recent changes might not be reflected in this value.
    :ivar read_units: The ReadCapacityUnits of the tables
        Provisioned Throughput.
    :ivar write_units: The WriteCapacityUnits of the tables
        Provisioned Throughput.
    :ivar schema: The Schema object associated with the table.
    """

    def __init__(self, layer2, response=None):
        self.layer2 = layer2
        self._dict = {}
        self.update_from_response(response)

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
    
    def update_from_response(self, response):
        """
        Update the state of the Table object based on the response
        data received from Amazon DynamoDB.
        """
        if 'Table' in response:
            self._dict.update(response['Table'])
        elif 'TableDescription' in response:
            self._dict.update(response['TableDescription'])
        if 'KeySchema' in self._dict:
            self._schema = Schema(self._dict['KeySchema'])

    def refresh(self, wait_for_active=False, retry_seconds=5):
        """
        Refresh all of the fields of the Table object by calling
        the underlying DescribeTable request.

        :type wait_for_active: bool
        :param wait_for_active: If True, this command will not return
            until the table status, as returned from Amazon DynamoDB, is
            'ACTIVE'.

        :type retry_seconds: int
        :param retry_seconds: If wait_for_active is True, this
            parameter controls the number of seconds of delay between
            calls to update_table in Amazon DynamoDB.  Default is 5 seconds.
        """
        done = False
        while not done:
            response = self.layer2.describe_table(self.name)
            self.update_from_response(response)
            if wait_for_active:
                if self.status == 'ACTIVE':
                    done = True
                else:
                    time.sleep(retry_seconds)
            else:
                done = True

    def update_throughput(self, read_units, write_units):
        """
        Update the ProvisionedThroughput for the Amazon DynamoDB Table.

        :type read_units: int
        :param read_units: The new value for ReadCapacityUnits.
        
        :type write_units: int
        :param write_units: The new value for WriteCapacityUnits.
        """
        self.layer2.update_throughput(self, read_units, write_units)
        
    def delete(self):
        """
        Delete this table and all items in it.  After calling this
        the Table objects status attribute will be set to 'DELETING'.
        """
        self.layer2.delete_table(self)

    def get_item(self, hash_key, range_key=None,
                 attributes_to_get=None, consistent_read=False,
                 item_class=Item):
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

        :type item_class: Class
        :param item_class: Allows you to override the class used
            to generate the items. This should be a subclass of
            :class:`boto.dynamodb.item.Item`
        """
        return self.layer2.get_item(self, hash_key, range_key,
                                    attributes_to_get, consistent_read,
                                    item_class)
    lookup = get_item
    
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
        Return an new, unsaved Item which can later be PUT to
        Amazon DynamoDB.
        """
        return Item(self, hash_key, range_key, attrs)

    def query(self, hash_key, range_key_condition=None,
              attributes_to_get=None, limit=None, consistent_read=False,
              scan_index_forward=True, exclusive_start_key=None,
              item_class=Item):
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

        :type item_class: Class
        :param item_class: Allows you to override the class used
            to generate the items. This should be a subclass of
            :class:`boto.dynamodb.item.Item`
        """
        return self.layer2.query(self, hash_key, range_key_condition,
                                 attributes_to_get=attributes_to_get,
                                 consistent_read=consistent_read,
                                 item_class=item_class)

    def scan(self, scan_filter=None,
             attributes_to_get=None, limit=None,
             count=False, exclusive_start_key=None,
             item_class=Item):
        """
        Scan through this table, this is a very long
        and expensive operation, and should be avoided if
        at all possible.

        :type scan_filter: dict
        :param scan_filter: A Python version of the
            ScanFilter data structure.

        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.

        :type limit: int
        :param limit: The maximum number of items to return.

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
        return self.layer2.scan(self, scan_filter,
            attributes_to_get, limit, count,
            exclusive_start_key, item_class=item_class)
