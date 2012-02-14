.. dynamodb_tut:

============================================
An Introduction to boto's DynamoDB interface
============================================

This tutorial focuses on the boto interface to AWS' DynamoDB_. This tutorial
assumes that you have boto already downloaded and installed.

.. _DynamoDB: http://aws.amazon.com/dynamodb/

Creating a Connection
---------------------

The first step in accessing DynamoDB is to create a connection to the service.
To do so, the most straight forward way is the following::

    >>> import boto
    >>> conn = boto.connect_dynamodb(
            aws_access_key_id='<YOUR_AWS_KEY_ID>',
            aws_secret_access_key='<YOUR_AWS_SECRET_KEY>')
    >>> conn
    <boto.dynamodb.layer2.Layer2 object at 0x3fb3090>

Bear in mind that if you have your credentials in boto config in your home
directory, the two keyword arguments in the call above are not needed. More
details on configuration can be found in :doc:`boto_config_tut`.

.. note:: At this
    time, Amazon DynamoDB is available only in the US-EAST-1 region. The
    ``connect_dynamodb`` method automatically connect to that region.

The :py:func:`boto.connect_dynamodb` functions returns a
:py:class:`boto.dynamodb.layer2.Layer2` instance, which is a high-level API
for working with DynamoDB. Layer2 is a set of abstractions that sit atop
the lower level :py:class:`boto.dynamodb.layer1.Layer1` API, which closely
mirrors the Amazon DynamoDB API. For the purpose of this tutorial, we'll
just be covering Layer2.

Listing Tables
--------------

Now that we have a DynamoDB connection object, we can then query for a list of
existing tables in that region::

    >>> conn.list_tables()
    ['test-table', 'another-table']

Creating Tables
---------------

DynamoDB tables are created with the
:py:meth:`Layer2.create_table <boto.dynamodb.layer2.Layer2.create_table>`
method. While DynamoDB's items (a rough equivalent to a relational DB's row)
don't have a fixed schema, you do need to create a schema for the table's
hash key element, and the optional range key element. This is explained in
greater detail in DynamoDB's `Data Model`_ documentation.

We'll start by defining a schema that has a hash key and a range key that
are both keys::

    >>> message_table_schema = conn.create_schema(
            hash_key_name='forum_name',
            hash_key_proto_value='S',
            range_key_name='subject',
            range_key_proto_value='S'
        )

The next few things to determine are table name and read/write throughput. We'll
defer explaining throughput to the DynamoDB's `Provisioned Throughput`_ docs.

We're now ready to create the table::

    >>> table = conn.create_table(
            name='messages',
            schema=message_table_schema,
            read_units=10,
            write_units=10
        )
    >>> table
    Table(messages)

This returns a :py:class:`boto.dynamodb.table.Table` instance, which provides
simple ways to create (put), update, and delete items.

.. _Data Model: http://docs.amazonwebservices.com/amazondynamodb/latest/developerguide/DataModel.html
.. _Provisioned Throughput: http://docs.amazonwebservices.com/amazondynamodb/latest/developerguide/ProvisionedThroughputIntro.html

Getting a Table
---------------

To retrieve an existing table, use
:py:meth:`Layer2.get_table <boto.dynamodb.layer2.Layer2.get_table>`::

    >>> conn.list_tables()
    ['test-table', 'another-table', 'messages']
    >>> table = conn.get_table('messages')
    >>> table
    Table(messages)

:py:meth:`Layer2.get_table <boto.dynamodb.layer2.Layer2.get_table>`, like
:py:meth:`Layer2.create_table <boto.dynamodb.layer2.Layer2.create_table>`,
returns a :py:class:`boto.dynamodb.table.Table` instance.

Describing Tables
-----------------

To get a complete description of a table, use
:py:meth:`Layer2.describe_table <boto.dynamodb.layer2.Layer2.describe_table>`::

    >>> conn.list_tables()
    ['test-table', 'another-table', 'messages']
    >>> conn.describe_table('messages')
    {
        'Table': {
            'CreationDateTime': 1327117581.624,
            'ItemCount': 0,
            'KeySchema': {
                'HashKeyElement': {
                    'AttributeName': 'forum_name',
                    'AttributeType': 'S'
                },
                'RangeKeyElement': {
                    'AttributeName': 'subject',
                    'AttributeType': 'S'
                }
            },
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            },
            'TableName': 'messages',
            'TableSizeBytes': 0,
            'TableStatus': 'ACTIVE'
        }
    }

Adding Items
------------

Continuing on with our previously created ``messages`` table, adding an::

    >>> table = conn.get_table('messages')
    >>> item_data = {
            'Body': 'http://url_to_lolcat.gif',
            'SentBy': 'User A',
            'ReceivedTime': '12/9/2011 11:36:03 PM',
        }
    >>> item = table.new_item(
            # Our hash key is 'forum'
            hash_key='LOLCat Forum',
            # Our range key is 'subject'
            range_key='Check this out!',
            # This has the
            attrs=item_data
        )

The
:py:meth:`Table.new_item <boto.dynamodb.table.Table.new_item>` method creates
a new :py:class:`boto.dynamodb.item.Item` instance with your specified
hash key, range key, and attributes already set.
:py:class:`Item <boto.dynamodb.item.Item>` is a :py:class:`dict` sub-class,
meaning you can edit your data as such::

    item['a_new_key'] = 'testing'
    del item['a_new_key']

After you are happy with the contents of the item, use
:py:meth:`Item.put <boto.dynamodb.item.Item.put>` to commit it to DynamoDB::

    >>> item.put()

Retrieving Items
----------------

Now, let's check if it got added correctly. Since DynamoDB works under an
'eventual consistency' mode, we need to specify that we wish a consistent read,
as follows::

    >>> table = conn.get_table('messages')
    >>> item = table.get_item(
            # Your hash key was 'forum_name'
            hash_key='LOLCat Forum',
            # Your range key was 'subject'
            range_key='Check this out!'
        )
    >>> item
    {
        # Note that this was your hash key attribute (forum_name)
        'forum_name': 'LOLCat Forum',
        # This is your range key attribute (subject)
        'subject': 'Check this out!'
        'Body': 'http://url_to_lolcat.gif',
        'ReceivedTime': '12/9/2011 11:36:03 PM',
        'SentBy': 'User A',
    }

Updating Items
--------------

To update an item's attributes, simply retrieve it, modify the value, then
:py:meth:`Item.put <boto.dynamodb.item.Item.put>` it again::

    >>> table = conn.get_table('messages')
    >>> item = table.get_item(
            hash_key='LOLCat Forum',
            range_key='Check this out!'
        )
    >>> item['SentBy'] = 'User B'
    >>> item.put()

Deleting Items
--------------

To delete items, use the
:py:meth:`Item.delete <boto.dynamodb.item.Item.delete>` method::

    >>> table = conn.get_table('messages')
    >>> item = table.get_item(
            hash_key='LOLCat Forum',
            range_key='Check this out!'
        )
    >>> item.delete()

Deleting Tables
---------------
There are two easy ways to delete a table. Through your top-level
:py:class:`Layer2 <boto.dynamodb.layer2.Layer2>` object::

    >>> conn.delete_table(table)

Or by getting the table, then using
:py:meth:`Table.delete <boto.dynamodb.table.Table.delete>`::

    >>> table = conn.get_table('messages')
    >>> table.delete()
