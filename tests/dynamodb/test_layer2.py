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
import uuid
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

        # Create another schema without a range key
        schema2 = c.create_schema('post_id', '')

        # Now create a table
        index = int(time.time())
        table_name = 'test-%d' % index
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

        # Create the second table
        table2_name = 'test-%d' % (index + 1)
        table2 = c.create_table(table2_name, schema2, read_units, write_units)

        # Wait for table to become active
        table.refresh(wait_for_active=True)
        table2.refresh(wait_for_active=True)

        # List tables and make sure new one is there
        table_names = c.list_tables()
        assert table_name in table_names
        assert table2_name in table_names

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
            'Public': True,
            'Tags': set(['index', 'primarykey', 'table']),
            'LastPostDateTime':  '12/9/2011 11:36:03 PM'}

        item1 = table.new_item(item1_key, item1_range, item1_attrs)
        # make sure the put() succeeds
        try:
            item1.put()
        except c.layer1.ResponseError, e:
            raise Exception("Item put failed: %s" % e)

        # Try to get an item that does not exist.
        self.assertRaises(DynamoDBKeyNotFoundError,
                          table.get_item, 'bogus_key', item1_range)

        # Now do a consistent read and check results
        item1_copy = table.get_item(item1_key, item1_range,
                                    consistent_read=True)
        assert item1_copy.hash_key == item1.hash_key
        assert item1_copy.range_key == item1.range_key
        for attr_name in item1_copy:
            val = item1_copy[attr_name]
            if isinstance(val, (int, long, float, basestring)):
                assert val == item1[attr_name]

        # Try retrieving only select attributes
        attributes = ['Message', 'Views']
        item1_small = table.get_item(item1_key, item1_range,
                                     attributes_to_get=attributes,
                                     consistent_read=True)
        for attr_name in item1_small:
            # The item will include the attributes we asked for as
            # well as the hashkey and rangekey, so filter those out.
            if attr_name not in (item1_small.hash_key_name,
                                 item1_small.range_key_name):
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

        # Now update the existing object
        item1.add_attribute('Replies', 2)

        removed_attr = 'Public'
        item1.delete_attribute(removed_attr)

        removed_tag = item1_attrs['Tags'].copy().pop()
        item1.delete_attribute('Tags', set([removed_tag]))

        replies_by_set = set(['Adam', 'Arnie'])
        item1.put_attribute('RepliesBy', replies_by_set)
        retvals = item1.save(return_values='ALL_OLD')
        # Need more tests here for variations on return_values
        assert 'Attributes' in retvals

        # Check for correct updates
        item1_updated = table.get_item(item1_key, item1_range,
                                       consistent_read=True)
        assert item1_updated['Replies'] == item1_attrs['Replies'] + 2
        self.assertFalse(item1_updated.has_key(removed_attr))
        self.assertTrue(removed_tag not in item1_updated['Tags'])
        self.assertTrue(item1_updated.has_key('RepliesBy'))
        self.assertTrue(item1_updated['RepliesBy'] == replies_by_set)

        # Put a few more items into the table
        item2_key = 'Amazon DynamoDB'
        item2_range = 'DynamoDB Thread 2'
        item2_attrs = {
            'Message': 'DynamoDB thread 2 message text',
            'LastPostedBy': 'User A',
            'Views': 0,
            'Replies': 0,
            'Answered': 0,
            'Tags': set(["index", "primarykey", "table"]),
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
            'Tags': set(['largeobject', 'multipart upload']),
            'LastPostDateTime': '12/9/2011 11:36:03 PM'
            }
        item3 = table.new_item(item3_key, item3_range, item3_attrs)
        item3.put()

        # Put an item into the second table
        table2_item1_key = uuid.uuid4().hex
        table2_item1_attrs = {
            'DateTimePosted': '25/1/2011 12:34:56 PM',
            'Text': 'I think boto rocks and so does DynamoDB'
            }
        table2_item1 = table2.new_item(table2_item1_key,
                                       attrs=table2_item1_attrs)
        table2_item1.put()

        # Try a few queries
        items = table.query('Amazon DynamoDB',
                             {'DynamoDB': 'BEGINS_WITH'})
        n = 0
        for item in items:
            n += 1
        assert n == 2

        items = table.query('Amazon DynamoDB',
                             {'DynamoDB': 'BEGINS_WITH'},
                            request_limit=1, max_results=1)
        n = 0
        for item in items:
            n += 1
        assert n == 1

        # Try a few scans
        items = table.scan()
        n = 0
        for item in items:
            n += 1
        assert n == 3

        # Test some integer and float attributes
        integer_value = 42
        float_value = 345.678
        item3['IntAttr'] = integer_value
        item3['FloatAttr'] = float_value

        # Test booleans
        item3['TrueBoolean'] = True
        item3['FalseBoolean'] = False

        # Test some set values
        integer_set = set([1,2,3,4,5])
        float_set = set([1.1, 2.2, 3.3, 4.4, 5.5])
        mixed_set = set([1, 2, 3.3, 4, 5.555])
        str_set = set(['foo', 'bar', 'fie', 'baz'])
        item3['IntSetAttr'] = integer_set
        item3['FloatSetAttr'] = float_set
        item3['MixedSetAttr'] = mixed_set
        item3['StrSetAttr'] = str_set
        item3.put()

        # Now do a consistent read
        item4 = table.get_item(item3_key, item3_range, consistent_read=True)
        assert item4['IntAttr'] == integer_value
        assert item4['FloatAttr'] == float_value
        assert item4['TrueBoolean'] == True
        assert item4['FalseBoolean'] == False
        # The values will not necessarily be in the same order as when
        # we wrote them to the DB.
        for i in item4['IntSetAttr']:
            assert i in integer_set
        for i in item4['FloatSetAttr']:
            assert i in float_set
        for i in item4['MixedSetAttr']:
            assert i in mixed_set
        for i in item4['StrSetAttr']:
            assert i in str_set

        # Try a batch get
        batch_list = c.new_batch_list()
        batch_list.add_batch(table, [(item2_key, item2_range),
                                     (item3_key, item3_range)])
        response = batch_list.submit()
        assert len(response['Responses'][table.name]['Items']) == 2

        # Try queries
        results = table.query('Amazon DynamoDB',
                              range_key_condition={'DynamoDB': 'BEGINS_WITH'})
        n = 0
        for item in results:
            n += 1
        assert n == 2
        
        # Try scans
        results = table.scan([('Tags', 'CONTAINS', 'table')])
        n = 0
        for item in results:
            n += 1
        assert n == 2

        # Try to delete the item with the right Expected value
        expected = {'Views': 0}
        item1.delete(expected_value=expected)

        self.assertFalse(table.has_item(item1_key, range_key=item1_range,
                                       consistent_read=True))
        # Now delete the remaining items
        ret_vals = item2.delete(return_values='ALL_OLD')
        # some additional checks here would be useful
        assert ret_vals['Attributes'][hash_key_name] == item2_key
        assert ret_vals['Attributes'][range_key_name] == item2_range
        
        item3.delete()
        table2_item1.delete()

        # Now delete the tables
        table.delete()
        table2.delete()
        assert table.status == 'DELETING'
        assert table2.status == 'DELETING'

        print '--- tests completed ---'
