.. dynamodb_tut:

=======================================
An Introduction to boto's DynamoDB interface
=======================================

This tutorial focuses on the boto interface to AWS' DynamoDB.  This tutorial assumes that you have boto already downloaded and installed.

Creating a Connection
---------------------
The first step in accessing DynamoDB is to create a connection to the service. To do so, the most straight forward way is the following:

>>> from boto.dynamodb.layer1 import Layer1
>>> conn = Layer1(aws_access_key_id='<YOUR_AWS_KEY_ID>',aws_secret_access_key='<YOUR_AWS_SECRET_KEY>')

Bear in mind that if you have your credentials in boto config in your home directory, the two parameters in the call above are not needed. Also important to note is that just as any other AWS service, DynamoDB is region-specific and as such you might want to specify which region to connect to, by default, it'll connect to the US-EAST-1 region.

Now that we have a DynamoDB connection object, we can then query for a list of existing tables in that region:

>>> conn.list_tables()
{u'TableNames': [u'test-table']}
>>>

Creating Tables
---------------------
To create a table we need to define a few things. Firstly, we need to define a table name. Secondly, we need a minimal schema specifying the key name and key range. And lastly, we need to define our provisioned read/write throughput. To do so, one could write code as follows:

>>> table_name = 'table-name'
>>> hash_key_name = 'key_name'
>>> hash_key_type = 'S'
>>> range_key_name = 'range_key_name'
>>> range_key_type = 'S'
>>> read_units = 10 
>>> write_units = 10
>>> schema = {'HashKeyElement': {'AttributeName': hash_key_name,
                             'AttributeType': hash_key_type},
          'RangeKeyElement': {'AttributeName': range_key_name,
                              'AttributeType': range_key_type}}
>>> provisioned_throughput = {'ReadCapacityUnits': read_units,
                          'WriteCapacityUnits': write_units}
                          
Then, we can actually send the request for table creation:

>>> conn.create_table(table_name, schema, provisioned_throughput)
{u'TableDescription': {u'KeySchema': {u'RangeKeyElement': {u'AttributeName': u'subject', u'AttributeType': u'S'}, u'HashKeyElement': {u'AttributeName': u'forum_name', u'AttributeType': u'S'}}, u'TableName': u'table-name', u'CreationDateTime': 1327092563.8180001, u'TableStatus': u'CREATING', u'ProvisionedThroughput': {u'WriteCapacityUnits': 10, u'ReadCapacityUnits': 10}}}
>>>

Describing Tables
--------------------
To get a complete description of the table we just created, we can issue the following call:

>>> l1.describe_table(table_name)

which, if successful,  returns a dictionary with set of attributes describing the table.

Adding Items
--------------------
Now that we have requested the creation of the table, after a few moments you will want to add records or items. To do so, you need to create a dictionary containing the data you wish to store. So, continuing with our example above, we can create the follwoing data structure:

>>> item_data = {
        hash_key_name: {hash_key_type: 'Sample Key Value'},
        range_key_name: {range_key_type: 'Sample Range Key Value'},
        'Subject': {'S': 'LOL watch this lolcat'},
        'Body' : {'S': 'http://url_to_lolcat.gif'},
        'SentBy': {'S': 'User A'},
        'ReceivedTime':  {'S': '12/9/2011 11:36:03 PM'}
        }
       
After we have that defined, we can use the following code to add the item to the table:

>>> result = conn.put_item(table_name, item_data)
{u'ConsumedCapacityUnits': 1.0}
>>>

Retrieving Items
------------------
Now, let's check if it got added correctly. Since DynamoDB works under an 'eventual consistency' mode, we need to specify that we wish a consistent read, as follows:

>>> key1 = {'HashKeyElement': {hash_key_type: item1_key},
       'RangeKeyElement': {range_key_type: item1_range}}
>>> result = conn.get_item(table_name, key=key1, consistent_read=True)
>>> result
{u'Item': u'Sample Key Value': {u'S': u'Amazon DynamoDB'},  u'ReceivedTime': {u'S': u'12/9/2011 11:36:03 PM'}, u'SentBy': {u'S': u'User A'}, u'Subject': {u'S': u'LOL watch this lolcat'}, u'Body' : {u'S': u'http://url_to_lolcat.gif'}, u'ConsumedCapacityUnits': 1.0}
>>>

Updating Items
------------------
If you wish to update an existing item, boto has a convenience method to such end and it's used as follows:

>>> attrs_to_update = {'Subject':{'Value':{'S':'Sup, Groovycat'}, 'Action': 'PUT'}}
>>> conn.update_item(table_name, key=key1, attrs_to_update)

Deleting Items
------------------
To delete items, you need to provide the table name and the key of the item you wish to delete:

>>> conn.delete_item(table_name,key=key1)

Deleting Tables
------------------
To delete a table all you need to provide is a table name, as follows:

>>> conn.delete_table(table_name)
{u'TableDescription': {u'ProvisionedThroughput': {u'WriteCapacityUnits': 10, u'ReadCapacityUnits': 10}, u'TableName': u'table-name', u'TableStatus': u'DELETING'}}

Notice
-----------------
This tutorial is a living document and is currently in flux. If you find any inaccuracies, please be sure to file a bug report.
