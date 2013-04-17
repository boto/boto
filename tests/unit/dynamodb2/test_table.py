import mock
import unittest
from boto.dynamodb2.constants import (STRING, NUMBER, BINARY,
                                      STRING_SET, NUMBER_SET, BINARY_SET)
from boto.dynamodb2.table import (BaseSchemaField, HashKey, RangeKey,
                                  BaseIndexField, AllIndex, KeysOnlyIndex,
                                  IncludeIndex, Item, Table)


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
        self.table = Table('whatever')
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
        pass

    def test_prepare(self):
        pass

    def test_save(self):
        pass

    def test_delete(self):
        pass
