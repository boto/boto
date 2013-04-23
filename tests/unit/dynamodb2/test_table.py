import mock
import unittest
from boto.dynamodb2 import exceptions
from boto.dynamodb2.fields import (HashKey, RangeKey,
                                   AllIndex, KeysOnlyIndex, IncludeIndex)
from boto.dynamodb2.layer1 import DynamoDBConnection
from boto.dynamodb2.table import Item, Table, ResultSet
from boto.dynamodb2.types import STRING, NUMBER


FakeDynamoDBConnection = mock.create_autospec(DynamoDBConnection)



class SchemaFieldsTestCase(unittest.TestCase):
    def test_hash_key(self):
        hash_key = HashKey('hello')
        self.assertEqual(hash_key.name, 'hello')
        self.assertEqual(hash_key.data_type, STRING)
        self.assertEqual(hash_key.attr_type, 'HASH')

        self.assertEqual(hash_key.definition(), {
            'AttributeName': 'hello',
            'AttributeType': 'HASH'
        })
        self.assertEqual(hash_key.schema(), {
            'AttributeName': 'hello',
            'KeyType': 'S'
        })

    def test_range_key(self):
        range_key = RangeKey('hello')
        self.assertEqual(range_key.name, 'hello')
        self.assertEqual(range_key.data_type, STRING)
        self.assertEqual(range_key.attr_type, 'RANGE')

        self.assertEqual(range_key.definition(), {
            'AttributeName': 'hello',
            'AttributeType': 'RANGE'
        })
        self.assertEqual(range_key.schema(), {
            'AttributeName': 'hello',
            'KeyType': 'S'
        })

    def test_alternate_type(self):
        alt_key = HashKey('alt', data_type=NUMBER)
        self.assertEqual(alt_key.name, 'alt')
        self.assertEqual(alt_key.data_type, NUMBER)
        self.assertEqual(alt_key.attr_type, 'HASH')

        self.assertEqual(alt_key.definition(), {
            'AttributeName': 'alt',
            'AttributeType': 'HASH'
        })
        self.assertEqual(alt_key.schema(), {
            'AttributeName': 'alt',
            'KeyType': 'N'
        })


class IndexFieldTestCase(unittest.TestCase):
    def test_all_index(self):
        all_index = AllIndex('AllKeys', parts=[
            HashKey('username'),
            RangeKey('date_joined')
        ])
        self.assertEqual(all_index.name, 'AllKeys')
        self.assertEqual([part.attr_type for part in all_index.parts], [
            'HASH',
            'RANGE'
        ])
        self.assertEqual(all_index.projection_type, 'ALL')

        self.assertEqual(all_index.definition(), [
            {'AttributeName': 'username', 'AttributeType': 'HASH'},
            {'AttributeName': 'date_joined', 'AttributeType': 'RANGE'}
        ])
        self.assertEqual(all_index.schema(), {
            'IndexName': 'AllKeys',
            'KeySchema': [
                {
                    'AttributeName': 'username',
                    'KeyType': 'S'
                },
                {
                    'AttributeName': 'date_joined',
                    'KeyType': 'S'
                }
            ],
            'Projection': {
                'ProjectionType': 'ALL'
            }
        })

    def test_keys_only_index(self):
        keys_only = KeysOnlyIndex('KeysOnly', parts=[
            HashKey('username'),
            RangeKey('date_joined')
        ])
        self.assertEqual(keys_only.name, 'KeysOnly')
        self.assertEqual([part.attr_type for part in keys_only.parts], [
            'HASH',
            'RANGE'
        ])
        self.assertEqual(keys_only.projection_type, 'KEYS_ONLY')

        self.assertEqual(keys_only.definition(), [
            {'AttributeName': 'username', 'AttributeType': 'HASH'},
            {'AttributeName': 'date_joined', 'AttributeType': 'RANGE'}
        ])
        self.assertEqual(keys_only.schema(), {
            'IndexName': 'KeysOnly',
            'KeySchema': [
                {
                    'AttributeName': 'username',
                    'KeyType': 'S'
                },
                {
                    'AttributeName': 'date_joined',
                    'KeyType': 'S'
                }
            ],
            'Projection': {
                'ProjectionType': 'KEYS_ONLY'
            }
        })

    def test_include_index(self):
        include_index = IncludeIndex('IncludeKeys', parts=[
            HashKey('username'),
            RangeKey('date_joined')
        ], includes=[
            'gender',
            'friend_count'
        ])
        self.assertEqual(include_index.name, 'IncludeKeys')
        self.assertEqual([part.attr_type for part in include_index.parts], [
            'HASH',
            'RANGE'
        ])
        self.assertEqual(include_index.projection_type, 'INCLUDE')

        self.assertEqual(include_index.definition(), [
            {'AttributeName': 'username', 'AttributeType': 'HASH'},
            {'AttributeName': 'date_joined', 'AttributeType': 'RANGE'}
        ])
        self.assertEqual(include_index.schema(), {
            'IndexName': 'IncludeKeys',
            'KeySchema': [
                {
                    'AttributeName': 'username',
                    'KeyType': 'S'
                },
                {
                    'AttributeName': 'date_joined',
                    'KeyType': 'S'
                }
            ],
            'Projection': {
                'ProjectionType': 'INCLUDE',
                'NonKeyAttributes': [
                    'gender',
                    'friend_count',
                ]
            }
        })


class ItemTestCase(unittest.TestCase):
    def setUp(self):
        super(ItemTestCase, self).setUp()
        self.table = Table('whatever', connection=FakeDynamoDBConnection())
        self.johndoe = self.create_item({
            'username': 'johndoe',
            'first_name': 'John',
            'date_joined': 12345,
        })

    def create_item(self, data):
        return Item(self.table, data=data)

    def test_initialization(self):
        empty_item = Item(self.table)
        self.assertEqual(empty_item.table, self.table)
        self.assertEqual(empty_item._data, {})

        full_item = Item(self.table, data={
            'username': 'johndoe',
            'date_joined': 12345,
        })
        self.assertEqual(full_item.table, self.table)
        self.assertEqual(full_item._data, {
            'username': 'johndoe',
            'date_joined': 12345,
        })

    def test_attribute_access(self):
        self.assertEqual(self.johndoe['username'], 'johndoe')
        self.assertEqual(self.johndoe['first_name'], 'John')
        self.assertEqual(self.johndoe['date_joined'], 12345)

        # Test a missing key.
        self.assertEqual(self.johndoe['last_name'], None)

        # Set a key.
        self.johndoe['last_name'] = 'Doe'
        # Test accessing the new key.
        self.assertEqual(self.johndoe['last_name'], 'Doe')

    def test_needs_save(self):
        self.johndoe.mark_clean()
        self.assertFalse(self.johndoe.needs_save())
        self.johndoe['last_name'] = 'Doe'
        self.assertTrue(self.johndoe.needs_save())

    def test_mark_clean(self):
        self.johndoe['last_name'] = 'Doe'
        self.assertTrue(self.johndoe.needs_save())
        self.johndoe.mark_clean()
        self.assertFalse(self.johndoe.needs_save())

    def test_load(self):
        empty_item = Item(self.table)
        empty_item.load({
            'Item': {
                'username': {'S': 'johndoe'},
                'first_name': {'S': 'John'},
                'last_name': {'S': 'Doe'},
                'date_joined': {'N': '1366056668'},
                'friend_count': {'N': '3'},
                'friends': {'SS': ['alice', 'bob', 'jane']},
            }
        })
        self.assertEqual(empty_item['username'], 'johndoe')
        self.assertEqual(empty_item['date_joined'], 1366056668)
        self.assertEqual(sorted(empty_item['friends']), sorted(['alice', 'bob', 'jane']))

    def test_get_keys(self):
        # Setup the data.
        self.table.schema = [
            HashKey('username'),
            RangeKey('date_joined'),
        ]
        self.assertEqual(self.johndoe.get_keys(), {
            'username': {'S': 'johndoe'},
            'date_joined': {'N': '12345'}
        })

    def test_prepare(self):
        self.assertEqual(self.johndoe.prepare(), {
            'username': {'S': 'johndoe'},
            'first_name': {'S': 'John'},
            'date_joined': {'N': '12345'}
        })

    def test_save_no_changes(self):
        # Unchanged, no save.
        with mock.patch.object(self.table, '_put_item', return_value=True) as mock_put_item:
            # Pretend we loaded it via ``get_item``...
            self.johndoe.mark_clean()
            self.assertFalse(self.johndoe.save())

        self.assertFalse(mock_put_item.called)

    def test_save_with_changes(self):
        # With changed data.
        with mock.patch.object(self.table, '_put_item', return_value=True) as mock_put_item:
            self.johndoe['first_name'] = 'J'
            self.johndoe['new_attr'] = 'never_seen_before'
            self.assertTrue(self.johndoe.save())
            self.assertFalse(self.johndoe.needs_save())

        self.assertTrue(mock_put_item.called)
        mock_put_item.assert_called_once_with({
            'username': {'S': 'johndoe'},
            'first_name': {'S': 'J'},
            'new_attr': {'S': 'never_seen_before'},
            'date_joined': {'N': '12345'}
        })

    def test_delete(self):
        # Setup the data.
        self.table.schema = [
            HashKey('username'),
            RangeKey('date_joined'),
        ]

        with mock.patch.object(self.table, 'delete_item', return_value=True) as mock_delete_item:
            self.johndoe.delete()

        self.assertTrue(mock_delete_item.called)
        mock_delete_item.assert_called_once_with(key={
            'username': {'S': 'johndoe'},
            'date_joined': {'N': '12345'}
        })


def fake_results(name, greeting='hello', exclusive_start_key=None, limit=None):
    if exclusive_start_key is None:
        exclusive_start_key = -1

    end_cap = 13
    results = []
    start_key = exclusive_start_key + 1

    for i in range(start_key, start_key + 5):
        if i < end_cap:
            results.append("%s %s #%s" % (greeting, name, i))

    return {
        'results': results,
        'last_key': exclusive_start_key + 5
    }


class ResultSetTestCase(unittest.TestCase):
    def setUp(self):
        super(ResultSetTestCase, self).setUp()
        self.results = ResultSet()
        self.results.to_call(fake_results, 'john', greeting='Hello', limit=20)

    def test_first_key(self):
        self.assertEqual(self.results.first_key, 'exclusive_start_key')

    def test_fetch_more(self):
        # First "page".
        self.results.fetch_more()
        self.assertEqual(self.results._results, [
            'Hello john #0',
            'Hello john #1',
            'Hello john #2',
            'Hello john #3',
            'Hello john #4',
        ])
        self.assertEqual(len(self.results._results), 5)

        # Fake in a last key.
        self.results._last_key_seen = 4
        # Second "page".
        self.results.fetch_more()
        self.assertEqual(self.results._results, [
            'Hello john #0',
            'Hello john #1',
            'Hello john #2',
            'Hello john #3',
            'Hello john #4',
            'Hello john #5',
            'Hello john #6',
            'Hello john #7',
            'Hello john #8',
            'Hello john #9',
        ])
        self.assertEqual(len(self.results._results), 10)

        # Fake in a last key.
        self.results._last_key_seen = 9
        # Last "page".
        self.results.fetch_more()
        self.assertEqual(self.results._results, [
            'Hello john #0',
            'Hello john #1',
            'Hello john #2',
            'Hello john #3',
            'Hello john #4',
            'Hello john #5',
            'Hello john #6',
            'Hello john #7',
            'Hello john #8',
            'Hello john #9',
            'Hello john #10',
            'Hello john #11',
            'Hello john #12',
        ])
        self.assertEqual(len(self.results._results), 13)

        # Fake in a key outside the range.
        self.results._last_key_seen = 15
        # Empty "page". Nothing new gets added
        self.results.fetch_more()
        self.assertEqual(self.results._results, [
            'Hello john #0',
            'Hello john #1',
            'Hello john #2',
            'Hello john #3',
            'Hello john #4',
            'Hello john #5',
            'Hello john #6',
            'Hello john #7',
            'Hello john #8',
            'Hello john #9',
            'Hello john #10',
            'Hello john #11',
            'Hello john #12',
        ])
        self.assertEqual(len(self.results._results), 13)

        # Make sure we won't check for results in the future.
        self.assertFalse(self.results._results_left)

    def test_iteration(self):
        # First page.
        self.assertEqual(self.results.next(), 'Hello john #0')
        self.assertEqual(self.results.next(), 'Hello john #1')
        self.assertEqual(self.results.next(), 'Hello john #2')
        self.assertEqual(self.results.next(), 'Hello john #3')
        self.assertEqual(self.results.next(), 'Hello john #4')
        self.assertEqual(self.results.call_kwargs['limit'], 15)
        # Second page.
        self.assertEqual(self.results.next(), 'Hello john #5')
        self.assertEqual(self.results.next(), 'Hello john #6')
        self.assertEqual(self.results.next(), 'Hello john #7')
        self.assertEqual(self.results.next(), 'Hello john #8')
        self.assertEqual(self.results.next(), 'Hello john #9')
        self.assertEqual(self.results.call_kwargs['limit'], 10)
        # Third page.
        self.assertEqual(self.results.next(), 'Hello john #10')
        self.assertEqual(self.results.next(), 'Hello john #11')
        self.assertEqual(self.results.next(), 'Hello john #12')
        self.assertRaises(StopIteration, self.results.next)
        self.assertEqual(self.results.call_kwargs['limit'], 7)


class TableTestCase(unittest.TestCase):
    def setUp(self):
        super(TableTestCase, self).setUp()
        self.users = Table('users', connection=FakeDynamoDBConnection())

    def test__introspect_schema(self):
        raw_schema_1 = [
            {
                "AttributeName": "username",
                "KeyType": "HASH"
            },
            {
                "AttributeName": "date_joined",
                "KeyType": "RANGE"
            }
        ]
        schema_1 = self.users._introspect_schema(raw_schema_1)
        self.assertEqual(len(schema_1), 2)
        self.assertTrue(isinstance(schema_1[0], HashKey))
        self.assertEqual(schema_1[0].name, 'username')
        self.assertTrue(isinstance(schema_1[1], RangeKey))
        self.assertEqual(schema_1[1].name, 'date_joined')

        raw_schema_2 = [
            {
                "AttributeName": "username",
                "KeyType": "BTREE"
            },
        ]
        self.assertRaises(
            exceptions.UnknownSchemaFieldError,
            self.users._introspect_schema,
            raw_schema_2
        )

    def test__introspect_indexes(self):
        raw_indexes_1 = [
            {
                "IndexName": "MostRecentlyJoinedIndex",
                "KeySchema": [
                    {
                        "AttributeName": "username",
                        "KeyType": "HASH"
                    },
                    {
                        "AttributeName": "date_joined",
                        "KeyType": "RANGE"
                    }
                ],
                "Projection": {
                    "ProjectionType": "KEYS_ONLY"
                }
            },
            {
                "IndexName": "EverybodyIndex",
                "KeySchema": [
                    {
                        "AttributeName": "username",
                        "KeyType": "HASH"
                    },
                ],
                "Projection": {
                    "ProjectionType": "ALL"
                }
            },
            {
                "IndexName": "GenderIndex",
                "KeySchema": [
                    {
                        "AttributeName": "username",
                        "KeyType": "HASH"
                    },
                    {
                        "AttributeName": "date_joined",
                        "KeyType": "RANGE"
                    }
                ],
                "Projection": {
                    "ProjectionType": "INCLUDE",
                    "NonKeyAttributes": [
                        'gender',
                    ]
                }
            }
        ]
        indexes_1 = self.users._introspect_indexes(raw_indexes_1)
        self.assertEqual(len(indexes_1), 3)
        self.assertTrue(isinstance(indexes_1[0], KeysOnlyIndex))
        self.assertEqual(indexes_1[0].name, 'MostRecentlyJoinedIndex')
        self.assertEqual(len(indexes_1[0].parts), 2)
        self.assertTrue(isinstance(indexes_1[1], AllIndex))
        self.assertEqual(indexes_1[1].name, 'EverybodyIndex')
        self.assertEqual(len(indexes_1[1].parts), 1)
        self.assertTrue(isinstance(indexes_1[2], IncludeIndex))
        self.assertEqual(indexes_1[2].name, 'GenderIndex')
        self.assertEqual(len(indexes_1[2].parts), 2)
        self.assertEqual(indexes_1[2].includes_fields, ['gender'])

        raw_indexes_2 = [
            {
                "IndexName": "MostRecentlyJoinedIndex",
                "KeySchema": [
                    {
                        "AttributeName": "username",
                        "KeyType": "HASH"
                    },
                    {
                        "AttributeName": "date_joined",
                        "KeyType": "RANGE"
                    }
                ],
                "Projection": {
                    "ProjectionType": "SOMETHING_CRAZY"
                }
            },
        ]
        self.assertRaises(
            exceptions.UnknownIndexFieldError,
            self.users._introspect_indexes,
            raw_indexes_2
        )

    def test_initialization(self):
        users = Table('users')
        self.assertEqual(users.table_name, 'users')
        self.assertTrue(isinstance(users.connection, DynamoDBConnection))
        self.assertEqual(users.throughput['read'], 5)
        self.assertEqual(users.throughput['write'], 5)
        self.assertEqual(users.schema, None)
        self.assertEqual(users.indexes, None)

        groups = Table('groups', connection=FakeDynamoDBConnection())
        self.assertEqual(groups.table_name, 'groups')
        self.assertTrue(hasattr(groups.connection, 'assert_called_once_with'))

    def test_create_simple(self):
        conn = FakeDynamoDBConnection()

        with mock.patch.object(conn, 'create_table', return_value={}) as mock_create_table:
            retval = Table.create('users', schema=[
                HashKey('username'),
                RangeKey('date_joined', data_type=NUMBER)
            ], connection=conn)
            self.assertTrue(retval)

        self.assertTrue(mock_create_table.called)
        mock_create_table.assert_called_once_with('users', [
            {
                'AttributeName': 'username',
                'AttributeType': 'HASH'
            },
            {
                'AttributeName': 'date_joined',
                'AttributeType': 'RANGE'
            }
        ],
        [
            {
                'KeyType': 'S',
                'AttributeName': 'username'
            },
            {
                'KeyType': 'N',
                'AttributeName': 'date_joined'
            }
        ],
        {
            'WriteCapacityUnits': 5,
            'ReadCapacityUnits': 5
        })

    def test_create_full(self):
        conn = FakeDynamoDBConnection()

        with mock.patch.object(conn, 'create_table', return_value={}) as mock_create_table:
            retval = Table.create('users', schema=[
                HashKey('username'),
                RangeKey('date_joined', data_type=NUMBER)
            ], throughput={
                'read':20,
                'write': 10,
            }, indexes=[
                KeysOnlyIndex('FriendCountIndex', parts=[RangeKey('friend_count')]),
            ], connection=conn)
            self.assertTrue(retval)

        self.assertTrue(mock_create_table.called)
        mock_create_table.assert_called_once_with('users', [
            {
                'AttributeName': 'username',
                'AttributeType': 'HASH'
            },
            {
                'AttributeName': 'date_joined',
                'AttributeType': 'RANGE'
            },
            {
                'AttributeName': 'friend_count',
                'AttributeType': 'RANGE'
            }
        ],
        [
            {
                'KeyType': 'S',
                'AttributeName': 'username'
            },
            {
                'KeyType': 'N',
                'AttributeName': 'date_joined'
            }
        ],
        {
            'WriteCapacityUnits': 10,
            'ReadCapacityUnits': 20
        },
        local_secondary_indexes=[
            {
                'KeySchema': [
                    {
                        'KeyType': 'S',
                        'AttributeName': 'friend_count'
                    }
                ],
                'IndexName': 'FriendCountIndex',
                'Projection': {
                    'ProjectionType': 'KEYS_ONLY'
                }
            }
        ])

    def test_describe(self):
        expected = {
            "users": {
                "AttributeDefinitions": [
                    {
                        "AttributeName": "username",
                        "AttributeType": "S"
                    }
                ],
                "ItemCount": 5,
                "KeySchema": [
                    {
                        "AttributeName": "username",
                        "KeyType": "HASH"
                    }
                ],
                "LocalSecondaryIndexes": [
                    {
                        "IndexName": "UsernameIndex",
                        "KeySchema": [
                            {
                                "AttributeName": "username",
                                "KeyType": "HASH"
                            }
                        ],
                        "Projection": {
                            "ProjectionType": "KEYS_ONLY"
                        }
                    }
                ],
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 20,
                    "WriteCapacityUnits": 6
                },
                "TableName": "Thread",
                "TableStatus": "ACTIVE"
            }
        }

        with mock.patch.object(self.users.connection, 'describe_table', return_value=expected) as mock_describe:
            self.assertEqual(self.users.throughput['read'], 5)
            self.assertEqual(self.users.throughput['write'], 5)
            self.assertEqual(self.users.schema, None)
            self.assertEqual(self.users.indexes, None)

            self.users.describe()

            self.assertEqual(self.users.throughput['read'], 20)
            self.assertEqual(self.users.throughput['write'], 6)
            self.assertEqual(len(self.users.schema), 1)
            self.assertEqual(isinstance(self.users.schema[0], HashKey), 1)
            self.assertEqual(len(self.users.indexes), 1)

        mock_describe.assert_called_once_with('users')

    def test_update(self):
        with mock.patch.object(self.users.connection, 'update_table', return_value={}) as mock_update:
            self.assertEqual(self.users.throughput['read'], 5)
            self.assertEqual(self.users.throughput['write'], 5)
            self.users.update(throughput={
                'read': 7,
                'write': 2,
            })
            self.assertEqual(self.users.throughput['read'], 7)
            self.assertEqual(self.users.throughput['write'], 2)

        mock_update.assert_called_once_with('users', {
            'WriteCapacityUnits': 2,
            'ReadCapacityUnits': 7
        })

    def test_delete(self):
        with mock.patch.object(self.users.connection, 'delete_table', return_value={}) as mock_delete:
            self.assertTrue(self.users.delete())

        mock_delete.assert_called_once_with('users')

    def test_get_item(self):
        expected = {
            'Item': {
                'username': {'S': 'johndoe'},
                'first_name': {'S': 'John'},
                'last_name': {'S': 'Doe'},
                'date_joined': {'N': '1366056668'},
                'friend_count': {'N': '3'},
                'friends': {'SS': ['alice', 'bob', 'jane']},
            }
        }

        with mock.patch.object(self.users.connection, 'get_item', return_value=expected) as mock_get_item:
            item = self.users.get_item(username='johndoe')
            self.assertEqual(item['username'], 'johndoe')
            self.assertEqual(item['first_name'], 'John')

        mock_get_item.assert_called_once_with('users', {'username': {'S': 'johndoe'}})

    def test_put_item(self):
        with mock.patch.object(self.users.connection, 'put_item', return_value={}) as mock_put_item:
            self.users.put_item(data={
                'username': 'johndoe',
                'last_name': 'Doe',
                'date_joined': 2345,
            })

        mock_put_item.assert_called_once_with('users', {
            'username': {'S': 'johndoe'},
            'last_name': {'S': 'Doe'},
            'date_joined': {'N': '2345'}
        })

    def test_private_put_item(self):
        with mock.patch.object(self.users.connection, 'put_item', return_value={}) as mock_put_item:
            self.users._put_item({'some': 'data'})

        mock_put_item.assert_called_once_with('users', {'some': 'data'})

    def test_delete_item(self):
        with mock.patch.object(self.users.connection, 'delete_item', return_value={}) as mock_delete_item:
            self.assertTrue(self.users.delete_item(username='johndoe', date_joined=23456))

        mock_delete_item.assert_called_once_with('users', {'username': {'S': 'johndoe'}, 'date_joined': {'N': '23456'}})

    def test_get_key_fields_no_schema_populated(self):
        expected = {
            "users": {
                "AttributeDefinitions": [
                    {
                        "AttributeName": "username",
                        "AttributeType": "S"
                    },
                    {
                        "AttributeName": "date_joined",
                        "AttributeType": "N"
                    }
                ],
                "ItemCount": 5,
                "KeySchema": [
                    {
                        "AttributeName": "username",
                        "KeyType": "HASH"
                    },
                    {
                        "AttributeName": "date_joined",
                        "KeyType": "RANGE"
                    }
                ],
                "LocalSecondaryIndexes": [
                    {
                        "IndexName": "UsernameIndex",
                        "KeySchema": [
                            {
                                "AttributeName": "username",
                                "KeyType": "HASH"
                            }
                        ],
                        "Projection": {
                            "ProjectionType": "KEYS_ONLY"
                        }
                    }
                ],
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 20,
                    "WriteCapacityUnits": 6
                },
                "TableName": "Thread",
                "TableStatus": "ACTIVE"
            }
        }

        with mock.patch.object(self.users.connection, 'describe_table', return_value=expected) as mock_describe:
            self.assertEqual(self.users.schema, None)

            key_fields = self.users.get_key_fields()
            self.assertEqual(key_fields, ['username', 'date_joined'])

            self.assertEqual(len(self.users.schema), 2)

        mock_describe.assert_called_once_with('users')

    def test_batch_write_no_writes(self):
        with mock.patch.object(self.users.connection, 'batch_write_item', return_value={}) as mock_batch:
            with self.users.batch_write() as batch:
                pass

        self.assertFalse(mock_batch.called)

    def test_batch_write(self):
        with mock.patch.object(self.users.connection, 'batch_write_item', return_value={}) as mock_batch:
            with self.users.batch_write() as batch:
                batch.put_item(data={
                    'username': 'jane',
                    'date_joined': 12342547
                })
                batch.delete_item(username='johndoe')
                batch.put_item(data={
                    'username': 'alice',
                    'date_joined': 12342888
                })

        mock_batch.assert_called_once_with('users', {
            'users': [
                {
                    'PutRequest': {
                        'Item': {
                            'username': {'S': 'jane'},
                            'date_joined': {'N': '12342547'}
                        }
                    }
                },
                {
                    'PutRequest': {
                        'Item': {
                            'username': {'S': 'alice'},
                            'date_joined': {'N': '12342888'}
                        }
                    }
                },
                {
                    'DeleteRequest': {
                        'Key': {
                            'username': {'S': 'johndoe'},
                        }
                    }
                },
            ]
        })

    def test_batch_write_dont_swallow_exceptions(self):
        with mock.patch.object(self.users.connection, 'batch_write_item', return_value={}) as mock_batch:
            try:
                with self.users.batch_write() as batch:
                    raise Exception('OH NOES')
            except Exception, e:
                self.assertEqual(str(e), 'OH NOES')

        self.assertFalse(mock_batch.called)

    def test_batch_write_flushing(self):
        with mock.patch.object(self.users.connection, 'batch_write_item', return_value={}) as mock_batch:
            with self.users.batch_write() as batch:
                batch.put_item(data={
                    'username': 'jane',
                    'date_joined': 12342547
                })
                # This would only be enough for one batch.
                batch.delete_item(username='johndoe1')
                batch.delete_item(username='johndoe2')
                batch.delete_item(username='johndoe3')
                batch.delete_item(username='johndoe4')
                batch.delete_item(username='johndoe5')
                batch.delete_item(username='johndoe6')
                batch.delete_item(username='johndoe7')
                batch.delete_item(username='johndoe8')
                batch.delete_item(username='johndoe9')
                batch.delete_item(username='johndoe10')
                batch.delete_item(username='johndoe11')
                batch.delete_item(username='johndoe12')
                batch.delete_item(username='johndoe13')
                batch.delete_item(username='johndoe14')
                batch.delete_item(username='johndoe15')
                batch.delete_item(username='johndoe16')
                batch.delete_item(username='johndoe17')
                batch.delete_item(username='johndoe18')
                batch.delete_item(username='johndoe19')
                batch.delete_item(username='johndoe20')
                batch.delete_item(username='johndoe21')
                batch.delete_item(username='johndoe22')
                batch.delete_item(username='johndoe23')

                # We're only at 24 items. No flushing yet.
                self.assertEqual(mock_batch.call_count, 0)

                # This pushes it over the edge. A flush happens then we start
                # queuing objects again.
                batch.delete_item(username='johndoe24')
                self.assertEqual(mock_batch.call_count, 1)
                # Since we add another, there's enough for a second call to
                # flush.
                batch.delete_item(username='johndoe25')

        self.assertEqual(mock_batch.call_count, 2)

    def test__build_filters(self):
        filters = self.users._build_filters({
            'username__eq': 'johndoe',
            'date_joined__gte': 1234567,
            'age__in': [30, 31, 32, 33],
            'last_name__between': ['danzig', 'only'],
            'first_name__null': False,
            'gender__null': True,
        })
        self.assertEqual(filters, {
            'username': {
                'AttributeValueList': [
                    {
                        'S': 'johndoe',
                    },
                ],
                'ComparisonOperator': 'EQ',
            },
            'date_joined': {
                'AttributeValueList': [
                    {
                        'N': '1234567',
                    },
                ],
                'ComparisonOperator': 'GE',
            },
            'age': {
                'AttributeValueList': [{'NS': ['32', '33', '30', '31']}],
                'ComparisonOperator': 'IN',
            },
            'last_name': {
                'AttributeValueList': [{'SS': ['only', 'danzig']}],
                'ComparisonOperator': 'BETWEEN',
            },
            'first_name': {
                'ComparisonOperator': 'NOT_NULL'
            },
            'gender': {
                'ComparisonOperator': 'NULL'
            },
        })

        self.assertRaises(exceptions.UnknownFilterTypeError,
            self.users._build_filters,
            {
                'darling__die': True,
            }
        )

    def test_query(self):
        pass

    def test_scan(self):
        pass

    def test_batch_get(self):
        pass

    def test_count(self):
        pass
