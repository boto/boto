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
import time

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
        self._dict.update(response)
        self._schema = Schema(self, self._dict['Table']['KeySchema'])

    def __repr__(self):
        return 'Table(%s)' % self.name

    @property
    def name(self):
        return self._dict['Table']['TableName']
    
    @property
    def create_time(self):
        return self._dict['Table']['CreationDateTime']
    
    @property
    def status(self):
        return self._dict['Table']['TableStatus']
    
    @property
    def item_count(self):
        return self._dict['Table']['ItemCount']
    
    @property
    def size_bytes(self):
        return self._dict['Table']['TableSizeBytes']
    
    @property
    def schema(self):
        return self._schema
    
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

        :type read_thruput: int
        :param read_thruput: The new value for ReadCapacityUnits.
        
        :type write_thruput: int
        :param write_thruput: The new value for WriteCapacityUnits.
        """
        response = self.layer1.update_table(self.name,
                                            {'ReadCapacityUnits': read_units,
                                             'WriteCapacityUnits': write_units})
        self._update(response)
        return response
        
    def delete(self):
        """
        Delete this table and all items in it.  After calling this
        the Table objects status attribute will be set to 'DELETING'.
        """
        response = self.layer1.delete_table(self.name)
        self._update(response)

    def get_item(self, hash_key, range_key=None):
        """
        Retrieve an existing item from the table.

        :type hash_key: 
        """
        return Item(self, hash_key, range_key)

        
        

