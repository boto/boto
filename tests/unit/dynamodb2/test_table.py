import mock
import unittest
from boto.dynamodb2.constants import (STRING, NUMBER, BINARY,
                                      STRING_SET, NUMBER_SET, BINARY_SET)
from boto.dynamodb2.layer1 import DynamoDBConnection
from boto.dynamodb2.table import (BaseSchemaField, HashKey, RangeKey,
                                  BaseIndexField, AllIndex, KeysOnlyIndex,
                                  IncludeIndex, Item, Table)


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


class TableTestCase(unittest.TestCase):
    def setUp(self):
        super(TableTestCase, self).setUp()
        self.table = Table('users', connection=FakeDynamoDBConnection())

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
        schema_1 = self.table._introspect_schema(raw_schema_1)
        self.assertEqual(len(schema_1), 2)
        self.assertTrue(isinstance(schema_1[0], HashKey))
        self.assertEqual(schema_1[0].name, 'username')
        self.assertTrue(isinstance(schema_1[1], RangeKey))
        self.assertEqual(schema_1[1].name, 'date_joined')

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
        indexes_1 = self.table._introspect_indexes(raw_indexes_1)
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
