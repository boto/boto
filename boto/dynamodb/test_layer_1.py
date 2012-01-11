from layer1 import Layer1
import time

c = Layer1()

print '+++ First create a table +++'

table_name = 'mitch-test-%d' % int(time.time())
hash_key_name = 'forum_name'
hash_key_type = 'S'
range_key_name = 'subject'
range_key_type = 'S'
read_thruput = 10
write_thruput = 5
schema = {'HashKeyElement': {'AttributeName': hash_key_name,
                             'AttributeType': hash_key_type},
          'RangeKeyElement': {'AttributeName': range_key_name,
                              'AttributeType': range_key_type}}
provisioned_throughput = {'ReadsPerSecond': read_thruput,
                          'WritesPerSecond': write_thruput}

result = c.create_table(table_name, schema, provisioned_throughput)
assert result['TableDescription']['TableName'] == table_name
result_schema = result['TableDescription']['KeySchema']
assert result_schema['HashKeyElement']['AttributeName'] == hash_key_name
assert result_schema['HashKeyElement']['AttributeType'] == hash_key_type
assert result_schema['RangeKeyElement']['AttributeName'] == range_key_name
assert result_schema['RangeKeyElement']['AttributeType'] == range_key_type
result_thruput = result['TableDescription']['ProvisionedThroughput']
assert result_thruput['ReadsPerSecond'] == read_thruput
assert result_thruput['WritesPerSecond'] == write_thruput

print '+++ Wait for table to become active +++'
result = c.describe_table(table_name)
while result['Table']['TableStatus'] != 'ACTIVE':
    time.sleep(5)
    print '...checking'
    result = c.describe_table(table_name)

print '+++ Table is now active +++'

print '+++ List tables and make sure new one is there +++'
result = c.list_tables()
assert table_name in result['TableNames']

print '+++ Update the tables ProvisionedThroughput +++'
new_read_thruput = 20
new_write_thruput = 10
new_provisioned_throughput = {'ReadsPerSecond': new_read_thruput,
                              'WritesPerSecond': new_write_thruput}
result = c.update_table(table_name, new_provisioned_throughput)

print '+++ Wait for table to be updated +++'
result = c.describe_table(table_name)
while result['Table']['TableStatus'] == 'UPDATING':
    time.sleep(5)
    print '...checking'
    result = c.describe_table(table_name)

result_thruput = result['Table']['ProvisionedThroughput']
assert result_thruput['ReadsPerSecond'] == new_read_thruput
assert result_thruput['WritesPerSecond'] == new_write_thruput

print '+++ Put an item +++'
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

print '+++ Now do a consistent read and check results +++'
key1 = {'HashKeyElement': {hash_key_type: item1_key},
       'RangeKeyElement': {range_key_type: item1_range}}
result = c.get_item(table_name, key=key1, consistent_read=True)
for name in item1_data:
    assert name in result['Item']

print '+++ Try retrieving only select attributes +++'
attributes = ['Message', 'Views']
result = c.get_item(table_name, key=key1, consistent_read=True,
                    attributes_to_get=attributes)
for name in result['Item']:
    assert name in attributes

print '+++ Try to delete the item with the wrong Expected value +++'
expected = {'Views': {'Value': {'N': '1'}}}
try:
    result = c.delete_item('table_name', key=key1, expected=expected)
except c.ResponseError, e:
    print 'Detected error', e

print '+++ Now update the existing object +++'
attribute_updates = {'Views': {'Value': {'N': '5'},
                               'Action': 'PUT'},
                     'Tags': {'Value': {'SS': ['foobar']},
                              'Action': 'ADD'}}
result = c.update_item(table_name, key=key1, attribute_updates=attribute_updates)

print '+++ Put a few more items into the table +++'
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

print '+++ Try a few queries +++'
result = c.query(table_name, {'S': 'Amazon DynamoDB'},
                 {'AttributeValueList': [{'S': 'DynamoDB'}],
                  'ComparisonOperator': 'BEGINS_WITH'})
assert 'Count' in result
assert result['Count'] == 2
    
print '+++ Try a few scans +++'
result = c.scan(table_name,
                {'Tags': {'AttributeValueList':[{'S': 'table'}],
                          'ComparisonOperator': 'CONTAINS'}})
assert 'Count' in result
assert result['Count'] == 2
    
print '+++ Now delete the items +++'
result = c.delete_item(table_name, key=key1)
result = c.delete_item(table_name, key=key2)
result = c.delete_item(table_name, key=key3)

print '+++ Now delete the table +++'
result = c.delete_table(table_name)
assert result['TableDescription']['TableStatus'] == 'DELETING'

