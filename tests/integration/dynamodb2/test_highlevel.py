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
import time

from tests.unit import unittest
from boto.dynamodb2 import exceptions
from boto.dynamodb2.fields import HashKey, RangeKey, KeysOnlyIndex
from boto.dynamodb2.table import Table
from boto.dynamodb2.types import NUMBER


class DynamoDBv2Test(unittest.TestCase):
    dynamodb = True

    def test_integration(self):
        users = Table.create('users', schema=[
            HashKey('username'),
            RangeKey('friend_count', data_type=NUMBER)
        ], throughput={
            'read': 5,
            'write': 5,
        }, indexes={
            KeysOnlyIndex('LastNameIndex', parts=[HashKey('username'), RangeKey('last_name')]),
        })
        self.addCleanup(users.delete)

        self.assertEqual(len(users.schema), 2)
        self.assertEqual(users.throughput['read'], 5)

        # Wait for it.
        time.sleep(40)

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

        jane = users.get_item(username='jane', friend_count=3)
        self.assertEqual(jane['first_name'], 'Jane')
        jane['last_name'] = 'Doh'
        self.assertTrue(jane.save())

        results = users.query(
            username__eq='johndoe',
            last_name__eq='Doe',
            index='LastNameIndex',
            reverse=True
        )

        for res in results:
            self.assertTrue(res['username'] in ['johndoe',])

        all_users = users.scan(limit=7)
        self.assertEqual(all_users.next()['username'], 'bob')
        self.assertEqual(all_users.next()['username'], 'jane')
        self.assertEqual(all_users.next()['username'], 'johndoe')

        filtered_users = users.scan(limit=2, username__beginswith='j')
        self.assertEqual(filtered_users.next()['username'], 'jane')
        self.assertEqual(filtered_users.next()['username'], 'johndoe')

        johndoe = users.get_item(username='johndoe', friend_count=4)
        johndoe.delete()

        results = users.batch_get(keys=[
            {'username': 'bob', 'friend_count': 1},
            {'username': 'jane', 'friend_count': 3}
        ])

        batch_users = []

        for res in results:
            batch_users.append(res)
            self.assertTrue(res['first_name'] in ['Bob', 'Jane'])

        self.assertEqual(len(batch_users), 2)

        # Because lag time.
        self.assertTrue(users.count() > -1)
