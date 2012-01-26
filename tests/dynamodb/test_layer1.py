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
Tests for Layer1 of DynamoDB
"""

import unittest
import time
from boto.dynamodb.exceptions import DynamoDBKeyNotFoundError
from boto.dynamodb.layer1 import Layer1
from boto.sts.credentials import Credentials

json_doc = """{"access_key": "ASIAIV7R2NUUJ6SB7GKQ", "secret_key": "eIfijGxJlejHDSQiaGr6b7U805U0GKWmllCTt2ZM", "request_id": "28c17897-4555-11e1-8bb1-2529f165f2f0", "expiration": "2012-01-23T00:59:45.617Z", "session_token": "AQoDYXdzEPn//////////wEasAGDXeGY8bx36NLRSA1v3dy2x00k3FNA2KVsMEXkQuKY08gPTtYs2tefZTBsTjgjC+O6j8ieoB1on2bPyCq872+Yq3cipls8jna+PNSEcsXtC8CJBKai/FfYNg1XUHam6EUCtRiUHvqztOVgaGqUUS1UbrBKB7kKSXzgKrJ9AT0bvqi4hZS0ayaU8969f2HIbN9psXhRBKpJyB9FUPuVYpYYZsz9NY3y2kGtK+dgfrKvxyDxxfL4BA=="}"""

class DynamoDBLayer1Test (unittest.TestCase):

    def test_layer1_basic(self):
        print '--- running DynamoDB Layer1 tests ---'

        # Create a Layer1 connection with an expired set of
        # credentials to test the automatic renewal of tokens

        bad_creds = Credentials.from_json(json_doc)
        c = Layer1(session_token=bad_creds)

        # First create a table
        table_name = 'test-%d' % int(time.time())
        hash_key_name = 'forum_name'
        hash_key_type = 'S'
        range_key_name = 'subject'
        range_key_type = 'S'
        read_units = 5
        write_units = 5
        schema = {'HashKeyElement': {'AttributeName': hash_key_name,
                                     'AttributeType': hash_key_type},
                  'RangeKeyElement': {'AttributeName': range_key_name,
                                      'AttributeType': range_key_type}}
        provisioned_throughput = {'ReadCapacityUnits': read_units,
                                  'WriteCapacityUnits': write_units}

        result = c.create_table(table_name, schema, provisioned_throughput)
        assert result['TableDescription']['TableName'] == table_name
        result_schema = result['TableDescription']['KeySchema']
        assert result_schema['HashKeyElement']['AttributeName'] == hash_key_name
        assert result_schema['HashKeyElement']['AttributeType'] == hash_key_type
        assert result_schema['RangeKeyElement']['AttributeName'] == range_key_name
        assert result_schema['RangeKeyElement']['AttributeType'] == range_key_type
        result_thruput = result['TableDescription']['ProvisionedThroughput']
        assert result_thruput['ReadCapacityUnits'] == read_units
        assert result_thruput['WriteCapacityUnits'] == write_units

        # Wait for table to become active
        result = c.describe_table(table_name)
        while result['Table']['TableStatus'] != 'ACTIVE':
            time.sleep(5)
            result = c.describe_table(table_name)

        # List tables and make sure new one is there
        result = c.list_tables()
        assert table_name in result['TableNames']

        # Update the tables ProvisionedThroughput
        new_read_units = 10
        new_write_units = 5
        new_provisioned_throughput = {'ReadCapacityUnits': new_read_units,
                                      'WriteCapacityUnits': new_write_units}
        result = c.update_table(table_name, new_provisioned_throughput)

        # Wait for table to be updated
        result = c.describe_table(table_name)
        while result['Table']['TableStatus'] == 'UPDATING':
            time.sleep(5)
            result = c.describe_table(table_name)

        result_thruput = result['Table']['ProvisionedThroughput']
        assert result_thruput['ReadCapacityUnits'] == new_read_units
        assert result_thruput['WriteCapacityUnits'] == new_write_units

        # Put an item
        item1_key = 'Amazon DynamoDB'
        item1_range = 'DynamoDB Thread 1'
        item1_data = {
            hash_key_name: {hash_key_type: item1_key},
            range_key_name: {range_key_type: item1_range},
            'Message': {'S': 'DynamoDB thread 1 message text'},
            'LastPostedBy': {'S': 'User A'},
            'Views': {'N': '0'},
            'Replies': {'N': '0'},
            'Answered': {'N': '0'},
            'Tags': {'SS': ["index", "primarykey", "table"]},
            'LastPostDateTime':  {'S': '12/9/2011 11:36:03 PM'}
            }
        result = c.put_item(table_name, item1_data)

        # Now do a consistent read and check results
        key1 = {'HashKeyElement': {hash_key_type: item1_key},
               'RangeKeyElement': {range_key_type: item1_range}}
        result = c.get_item(table_name, key=key1, consistent_read=True)
        for name in item1_data:
            assert name in result['Item']

        # Try to get an item that does not exist.
        invalid_key = {'HashKeyElement': {hash_key_type: 'bogus_key'},
                       'RangeKeyElement': {range_key_type: item1_range}}
        self.assertRaises(DynamoDBKeyNotFoundError,
                          c.get_item, table_name, key=invalid_key)

        # Try retrieving only select attributes
        attributes = ['Message', 'Views']
        result = c.get_item(table_name, key=key1, consistent_read=True,
                            attributes_to_get=attributes)
        for name in result['Item']:
            assert name in attributes

        # Try to delete the item with the wrong Expected value
        expected = {'Views': {'Value': {'N': '1'}}}
        try:
            result = c.delete_item('table_name', key=key1, expected=expected)
        except c.ResponseError, e:
            pass

        # Now update the existing object
        attribute_updates = {'Views': {'Value': {'N': '5'},
                                       'Action': 'PUT'},
                             'Tags': {'Value': {'SS': ['foobar']},
                                      'Action': 'ADD'}}
        result = c.update_item(table_name, key=key1,
                               attribute_updates=attribute_updates)

        # Put a few more items into the table
        item2_key = 'Amazon DynamoDB'
        item2_range = 'DynamoDB Thread 2'
        item2_data = {
            hash_key_name: {hash_key_type: item2_key},
            range_key_name: {range_key_type: item2_range},
            'Message': {'S': 'DynamoDB thread 2 message text'},
            'LastPostedBy': {'S': 'User A'},
            'Views': {'N': '0'},
            'Replies': {'N': '0'},
            'Answered': {'N': '0'},
            'Tags': {'SS': ["index", "primarykey", "table"]},
            'LastPostDateTime':  {'S': '12/9/2011 11:36:03 PM'}
            }
        result = c.put_item(table_name, item2_data)
        key2 = {'HashKeyElement': {hash_key_type: item2_key},
               'RangeKeyElement': {range_key_type: item2_range}}

        item3_key = 'Amazon S3'
        item3_range = 'S3 Thread 1'
        item3_data = {
            hash_key_name: {hash_key_type: item3_key},
            range_key_name: {range_key_type: item3_range},
            'Message': {'S': 'S3 Thread 1 message text'},
            'LastPostedBy': {'S': 'User A'},
            'Views': {'N': '0'},
            'Replies': {'N': '0'},
            'Answered': {'N': '0'},
            'Tags': {'SS': ['largeobject', 'multipart upload']},
            'LastPostDateTime':  {'S': '12/9/2011 11:36:03 PM'}
            }
        result = c.put_item(table_name, item3_data)
        key3 = {'HashKeyElement': {hash_key_type: item3_key},
               'RangeKeyElement': {range_key_type: item3_range}}

        # Try a few queries
        result = c.query(table_name, {'S': 'Amazon DynamoDB'},
                         {'AttributeValueList': [{'S': 'DynamoDB'}],
                          'ComparisonOperator': 'BEGINS_WITH'})
        assert 'Count' in result
        assert result['Count'] == 2

        # Try a few scans
        result = c.scan(table_name,
                        {'Tags': {'AttributeValueList':[{'S': 'table'}],
                                  'ComparisonOperator': 'CONTAINS'}})
        assert 'Count' in result
        assert result['Count'] == 2

        # Now delete the items
        result = c.delete_item(table_name, key=key1)
        result = c.delete_item(table_name, key=key2)
        result = c.delete_item(table_name, key=key3)

        # Now delete the table
        result = c.delete_table(table_name)
        assert result['TableDescription']['TableStatus'] == 'DELETING'

        print '--- tests completed ---'

