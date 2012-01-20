# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# All rights reserved.
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

"""
Tests for Layer2 of Amazon DynamoDB
"""

import unittest
import time
from boto.dynamodb.exceptions import DynamoDBKeyNotFoundError
from boto.dynamodb.layer2 import Layer2

class DynamoDBLayer2Test (unittest.TestCase):

    def test_layer2_basic(self):
        print '--- running Amazon DynamoDB Layer2 tests ---'
        c = Layer2()

        # First create a schema for the table
        hash_key_name = 'forum_name'
        hash_key_proto_value = ''
        range_key_name = 'subject'
        range_key_proto_value = ''
        schema = c.create_schema(hash_key_name, hash_key_proto_value,
                                 range_key_name, range_key_proto_value)
        # Now create a table
        table_name = 'test-%d' % int(time.time())
        read_units = 5
        write_units = 5
        table = c.create_table(table_name, schema, read_units, write_units)
        assert table.name == table_name
        assert table.schema.hash_key_name == hash_key_name
        assert table.schema.hash_key_type == c.get_dynamodb_type(hash_key_proto_value)
        assert table.schema.range_key_name == range_key_name
        assert table.schema.range_key_type == c.get_dynamodb_type(range_key_proto_value)
        assert table.read_units == read_units
        assert table.write_units == write_units

        # Wait for table to become active
        table.refresh(wait_for_active=True)

        # List tables and make sure new one is there
        table_names = c.list_tables()
        assert table_name in table_names

        # Update the tables ProvisionedThroughput
        new_read_units = 10
        new_write_units = 5
        table.update_throughput(new_read_units, new_write_units)

        # Wait for table to be updated
        table.refresh(wait_for_active=True)
        assert table.read_units == new_read_units
        assert table.write_units == new_write_units

        # Put an item
        item1_key = 'Amazon DynamoDB'
        item1_range = 'DynamoDB Thread 1'
        item1_attrs = {
            'Message': 'DynamoDB thread 1 message text',
            'LastPostedBy': 'User A',
            'Views': 0,
            'Replies': 0,
            'Answered': 0,
            'Tags': ['index', 'primarykey', 'table'],
            'LastPostDateTime':  '12/9/2011 11:36:03 PM'}

        item1 = table.new_item(item1_key, item1_range, item1_attrs)
        item1.put()

        # Try to get an item that does not exist.
        self.assertRaises(DynamoDBKeyNotFoundError,
                          table.get_item, 'bogus_key', item1_range)

        # Now do a consistent read and check results
        item1_copy = table.get_item(item1_key, item1_range,
                                    consistent_read=True)
        assert item1_copy.hash_key == item1.hash_key
        assert item1_copy.range_key == item1.range_key
        for attr_name in item1_copy.attrs:
            val = item1_copy.attrs[attr_name]
            if isinstance(val, (int, long, float, basestring)):
                assert val == item1.attrs[attr_name]

        # Try retrieving only select attributes
        attributes = ['Message', 'Views']
        item1_small = table.get_item(item1_key, item1_range,
                                     attributes_to_get=attributes)
        for attr_name in item1_small.attrs:
            assert attr_name in attributes

        self.assertTrue(table.has_item(item1_key, range_key=item1_range,
                                       consistent_read=True))

        # Try to delete the item with the wrong Expected value
        expected = {'Views': 1}
        try:
            item1.delete(expected_value=expected)
        except c.layer1.ResponseError, e:
            pass
        else:
            raise Exception("Expected Value condition failed")

        # Try to delete a value while expecting a non-existant attribute
        expected = {'FooBar': True}
        try:
            item1.delete(expected_value=expected)
        except c.layer1.ResponseError, e:
            pass


        # # Now update the existing object
        # attribute_updates = {'Views': {'Value': {'N': '5'},
        #                                'Action': 'PUT'},
        #                      'Tags': {'Value': {'SS': ['foobar']},
        #                               'Action': 'ADD'}}
        # result = c.update_item(table_name, key=key1,
        #                        attribute_updates=attribute_updates)

        # Put a few more items into the table
        item2_key = 'Amazon DynamoDB'
        item2_range = 'DynamoDB Thread 2'
        item2_attrs = {
            'Message': 'DynamoDB thread 2 message text',
            'LastPostedBy': 'User A',
            'Views': 0,
            'Replies': 0,
            'Answered': 0,
            'Tags': ["index", "primarykey", "table"],
            'LastPost2DateTime':  '12/9/2011 11:36:03 PM'}
        item2 = table.new_item(item2_key, item2_range, item2_attrs)
        item2.put()

        item3_key = 'Amazon S3'
        item3_range = 'S3 Thread 1'
        item3_attrs = {
            'Message': 'S3 Thread 1 message text',
            'LastPostedBy': 'User A',
            'Views': 0,
            'Replies': 0,
            'Answered': 0,
            'Tags': ['largeobject', 'multipart upload'],
            'LastPostDateTime': '12/9/2011 11:36:03 PM'
            }
        item3 = table.new_item(item3_key, item3_range, item3_attrs)
        item3.put()

        # Try a few queries
        items = table.query('Amazon DynamoDB',
                             {'DynamoDB': 'BEGINS_WITH'})
        assert len(items) == 2

        # # Try a few scans
        # result = c.scan(table_name,
        #                 {'Tags': {'AttributeValueList':[{'S': 'table'}],
        #                           'ComparisonOperator': 'CONTAINS'}})
        # assert 'Count' in result
        # assert result['Count'] == 2

        # Test some integer and float attributes
        integer_value = 42
        float_value = 345.678
        integer_list = [1,2,3,4,5]
        float_list = [1.1, 2.2, 3.3, 4.4, 5.5]
        mixed_list = [1, 2, 3.3, 4, 5.555]
        item3.attrs['IntAttr'] = integer_value
        item3.attrs['FloatAttr'] = float_value
        item3.attrs['IntListAttr'] = integer_list
        item3.attrs['FloatListAttr'] = float_list
        item3.attrs['MixedListAttr'] = mixed_list
        item3.put()

        # Now do a consistent read
        item4 = table.get_item(item3_key, item3_range, consistent_read=True)
        assert item4.attrs['IntAttr'] == integer_value
        assert item4.attrs['FloatAttr'] == float_value
        # The values will not necessarily be in the same order as when
        # we wrote them to the DB.
        for i in item4.attrs['IntListAttr']:
            assert i in integer_list
        for i in item4.attrs['FloatListAttr']:
            assert i in float_list
        for i in item4.attrs['MixedListAttr']:
            assert i in mixed_list
        
        # Now delete the items
        item1.delete()

        self.assertFalse(table.has_item(item1_key, range_key=item1_range,
                                       consistent_read=True))
        item2.delete()
        item3.delete()

        # Now delete the table
        table.delete()
        assert table.status == 'DELETING'

        print '--- tests completed ---'

