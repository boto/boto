# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.
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
Tests for DynamoDB v2 high-level abstractions.
"""
from __future__ import with_statement

import os
import time

from tests.unit import unittest
from boto.dynamodb2 import exceptions
from boto.dynamodb2.fields import (HashKey, RangeKey, KeysOnlyIndex,
                                   GlobalKeysOnlyIndex)
from boto.dynamodb2.items import Item
from boto.dynamodb2.table import Table
from boto.dynamodb2.types import NUMBER

try:
    import json
except ImportError:
    import simplejson as json


class DynamoDBv2Test(unittest.TestCase):
    dynamodb = True

    def test_integration(self):
        # Test creating a full table with all options specified.
        users = Table.create('users', schema=[
            HashKey('username'),
            RangeKey('friend_count', data_type=NUMBER)
        ], throughput={
            'read': 5,
            'write': 5,
        }, indexes=[
            KeysOnlyIndex('LastNameIndex', parts=[
                HashKey('username'),
                RangeKey('last_name')
            ]),
        ])
        self.addCleanup(users.delete)

        self.assertEqual(len(users.schema), 2)
        self.assertEqual(users.throughput['read'], 5)

        # Wait for it.
        time.sleep(60)

        # Make sure things line up if we're introspecting the table.
        users_hit_api = Table('users')
        users_hit_api.describe()
        self.assertEqual(len(users.schema), len(users_hit_api.schema))
        self.assertEqual(users.throughput, users_hit_api.throughput)
        self.assertEqual(len(users.indexes), len(users_hit_api.indexes))

        # Test putting some items individually.
        users.put_item(data={
            'username': 'johndoe',
            'first_name': 'John',
            'last_name': 'Doe',
            'friend_count': 4
        })

        users.put_item(data={
            'username': 'alice',
            'first_name': 'Alice',
            'last_name': 'Expert',
            'friend_count': 2
        })

        time.sleep(5)

        # Test batch writing.
        with users.batch_write() as batch:
            batch.put_item({
                'username': 'jane',
                'first_name': 'Jane',
                'last_name': 'Doe',
                'friend_count': 3
            })
            batch.delete_item(username='alice', friend_count=2)
            batch.put_item({
                'username': 'bob',
                'first_name': 'Bob',
                'last_name': 'Smith',
                'friend_count': 1
            })

        time.sleep(5)

        # Test getting an item & updating it.
        # This is the "safe" variant (only write if there have been no
        # changes).
        jane = users.get_item(username='jane', friend_count=3)
        self.assertEqual(jane['first_name'], 'Jane')
        jane['last_name'] = 'Doh'
        self.assertTrue(jane.save())

        # Test strongly consistent getting of an item.
        # Additionally, test the overwrite behavior.
        client_1_jane = users.get_item(
            username='jane',
            friend_count=3,
            consistent=True
        )
        self.assertEqual(jane['first_name'], 'Jane')
        client_2_jane = users.get_item(
            username='jane',
            friend_count=3,
            consistent=True
        )
        self.assertEqual(jane['first_name'], 'Jane')

        # Write & assert the ``first_name`` is gone, then...
        del client_1_jane['first_name']
        self.assertTrue(client_1_jane.save())
        check_name = users.get_item(
            username='jane',
            friend_count=3,
            consistent=True
        )
        self.assertEqual(check_name['first_name'], None)

        # ...overwrite the data with what's in memory.
        client_2_jane['first_name'] = 'Joan'
        # Now a write that fails due to default expectations...
        self.assertRaises(exceptions.JSONResponseError, client_2_jane.save)
        # ... so we force an overwrite.
        self.assertTrue(client_2_jane.save(overwrite=True))
        check_name_again = users.get_item(
            username='jane',
            friend_count=3,
            consistent=True
        )
        self.assertEqual(check_name_again['first_name'], 'Joan')

        # Reset it.
        jane['username'] = 'jane'
        jane['first_name'] = 'Jane'
        jane['last_name'] = 'Doe'
        jane['friend_count'] = 3
        self.assertTrue(jane.save(overwrite=True))

        # Test the partial update behavior.
        client_3_jane = users.get_item(
            username='jane',
            friend_count=3,
            consistent=True
        )
        client_4_jane = users.get_item(
            username='jane',
            friend_count=3,
            consistent=True
        )
        client_3_jane['favorite_band'] = 'Feed Me'
        # No ``overwrite`` needed due to new data.
        self.assertTrue(client_3_jane.save())
        # Expectations are only checked on the ``first_name``, so what wouldn't
        # have succeeded by default does succeed here.
        client_4_jane['first_name'] = 'Jacqueline'
        self.assertTrue(client_4_jane.partial_save())
        partial_jane = users.get_item(
            username='jane',
            friend_count=3,
            consistent=True
        )
        self.assertEqual(partial_jane['favorite_band'], 'Feed Me')
        self.assertEqual(partial_jane['first_name'], 'Jacqueline')

        # Reset it.
        jane['username'] = 'jane'
        jane['first_name'] = 'Jane'
        jane['last_name'] = 'Doe'
        jane['friend_count'] = 3
        self.assertTrue(jane.save(overwrite=True))

        # Ensure that partial saves of a brand-new object work.
        sadie = Item(users, data={
            'username': 'sadie',
            'first_name': 'Sadie',
            'favorite_band': 'Zedd',
            'friend_count': 7
        })
        self.assertTrue(sadie.partial_save())
        serverside_sadie = users.get_item(
            username='sadie',
            friend_count=7,
            consistent=True
        )
        self.assertEqual(serverside_sadie['first_name'], 'Sadie')

        # Test the eventually consistent query.
        results = users.query(
            username__eq='johndoe',
            last_name__eq='Doe',
            index='LastNameIndex',
            attributes=('username',),
            reverse=True
        )

        for res in results:
            self.assertTrue(res['username'] in ['johndoe',])
            self.assertEqual(res.keys(), ['username'])


        # Test the strongly consistent query.
        c_results = users.query(
            username__eq='johndoe',
            last_name__eq='Doe',
            index='LastNameIndex',
            reverse=True,
            consistent=True
        )

        for res in c_results:
            self.assertTrue(res['username'] in ['johndoe',])

        # Test scans without filters.
        all_users = users.scan(limit=7)
        self.assertEqual(all_users.next()['username'], 'bob')
        self.assertEqual(all_users.next()['username'], 'jane')
        self.assertEqual(all_users.next()['username'], 'johndoe')

        # Test scans with a filter.
        filtered_users = users.scan(limit=2, username__beginswith='j')
        self.assertEqual(filtered_users.next()['username'], 'jane')
        self.assertEqual(filtered_users.next()['username'], 'johndoe')

        # Test deleting a single item.
        johndoe = users.get_item(username='johndoe', friend_count=4)
        johndoe.delete()

        # Test the eventually consistent batch get.
        results = users.batch_get(keys=[
            {'username': 'bob', 'friend_count': 1},
            {'username': 'jane', 'friend_count': 3}
        ])
        batch_users = []

        for res in results:
            batch_users.append(res)
            self.assertTrue(res['first_name'] in ['Bob', 'Jane'])

        self.assertEqual(len(batch_users), 2)

        # Test the strongly consistent batch get.
        c_results = users.batch_get(keys=[
            {'username': 'bob', 'friend_count': 1},
            {'username': 'jane', 'friend_count': 3}
        ], consistent=True)
        c_batch_users = []

        for res in c_results:
            c_batch_users.append(res)
            self.assertTrue(res['first_name'] in ['Bob', 'Jane'])

        self.assertEqual(len(c_batch_users), 2)

        # Test count, but in a weak fashion. Because lag time.
        self.assertTrue(users.count() > -1)

        # Test query count
        count = users.query_count(
            username__eq='bob',
        )

        self.assertEqual(count, 1)

        # Test without LSIs (describe calls shouldn't fail).
        admins = Table.create('admins', schema=[
            HashKey('username')
        ])
        self.addCleanup(admins.delete)
        time.sleep(60)
        admins.describe()
        self.assertEqual(admins.throughput['read'], 5)
        self.assertEqual(admins.indexes, [])

        # A single query term should fail on a table with *ONLY* a HashKey.
        self.assertRaises(
            exceptions.QueryError,
            admins.query,
            username__eq='johndoe'
        )
        # But it shouldn't break on more complex tables.
        res = users.query(username__eq='johndoe')

        # Test putting with/without sets.
        mau5_created = users.put_item(data={
            'username': 'mau5',
            'first_name': 'dead',
            'last_name': 'mau5',
            'friend_count': 2,
            'friends': set(['skrill', 'penny']),
        })
        self.assertTrue(mau5_created)

        penny_created = users.put_item(data={
            'username': 'penny',
            'first_name': 'Penny',
            'friend_count': 0,
            'friends': set([]),
        })
        self.assertTrue(penny_created)

        # Test attributes.
        mau5 = users.get_item(
            username='mau5',
            friend_count=2,
            attributes=['username', 'first_name']
        )
        self.assertEqual(mau5['username'], 'mau5')
        self.assertEqual(mau5['first_name'], 'dead')
        self.assertTrue('last_name' not in mau5)

    def test_unprocessed_batch_writes(self):
        # Create a very limited table w/ low throughput.
        users = Table.create('slow_users', schema=[
            HashKey('user_id'),
        ], throughput={
            'read': 1,
            'write': 1,
        })
        self.addCleanup(users.delete)

        # Wait for it.
        time.sleep(60)

        with users.batch_write() as batch:
            for i in range(500):
                batch.put_item(data={
                    'user_id': str(i),
                    'name': 'Droid #{0}'.format(i),
                })

            # Before ``__exit__`` runs, we should have a bunch of unprocessed
            # items.
            self.assertTrue(len(batch._unprocessed) > 0)

        # Post-__exit__, they should all be gone.
        self.assertEqual(len(batch._unprocessed), 0)

    def test_gsi(self):
        users = Table.create('gsi_users', schema=[
            HashKey('user_id'),
        ], throughput={
            'read': 5,
            'write': 3,
        },
        global_indexes=[
            GlobalKeysOnlyIndex('StuffIndex', parts=[
                HashKey('user_id')
            ], throughput={
                'read': 2,
                'write': 1,
            }),
        ])
        self.addCleanup(users.delete)

        # Wait for it.
        time.sleep(60)

        users.update(
            throughput={
                'read': 3,
                'write': 4
            },
            global_indexes={
                'StuffIndex': {
                    'read': 1,
                    'write': 2
                }
            }
        )

        # Wait again for the changes to finish propagating.
        time.sleep(120)

    def test_query_with_limits(self):
        # Per the DDB team, it's recommended to do many smaller gets with a
        # reduced page size.
        # Clamp down the page size while ensuring that the correct number of
        # results are still returned.
        posts = Table.create('posts', schema=[
            HashKey('thread'),
            RangeKey('posted_on')
        ], throughput={
            'read': 5,
            'write': 5,
        })
        self.addCleanup(posts.delete)

        # Wait for it.
        time.sleep(60)

        # Add some data.
        test_data_path = os.path.join(
            os.path.dirname(__file__),
            'forum_test_data.json'
        )
        with open(test_data_path, 'r') as test_data:
            data = json.load(test_data)

            with posts.batch_write() as batch:
                for post in data:
                    batch.put_item(post)

        time.sleep(5)

        # Test the reduced page size.
        results = posts.query(
            thread__eq='Favorite chiptune band?',
            posted_on__gte='2013-12-24T00:00:00',
            max_page_size=2
        )

        all_posts = list(results)
        self.assertEqual(
            [post['posted_by'] for post in all_posts],
            ['joe', 'jane', 'joe', 'joe', 'jane', 'joe']
        )
        self.assertEqual(results._fetches, 3)
