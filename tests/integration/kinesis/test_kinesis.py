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

import boto
import time

from unittest import TestCase


class TimeoutError(Exception):
    pass


class TestKinesis(TestCase):
    def setUp(self):
        self.kinesis = boto.connect_kinesis()

    def tearDown(self):
        # Delete the stream even if there is a failure
        self.kinesis.delete_stream('test')

    def test_kinesis(self):
        kinesis = self.kinesis

        # Create a new stream
        kinesis.create_stream('test', 1)

        # Wait for the stream to be ready
        tries = 0
        while tries < 10:
            tries += 1
            time.sleep(15)
            response = kinesis.describe_stream('test')

            if response['StreamDescription']['StreamStatus'] == 'ACTIVE':
                break
        else:
            raise TimeoutError('Stream is still not active, aborting...')

        # Write some data to the stream
        data = 'Some data ...'
        response = kinesis.put_record('test', data, data)
        shard_id = response['ShardId']

        # Process some data from the stream
        response = kinesis.get_shard_iterator('test', shard_id, 'TRIM_HORIZON')
        shard_iterator = response['ShardIterator']

        # Wait for the data to show up
        tries = 0
        while tries < 20:
            tries += 1
            time.sleep(5)

            response = kinesis.get_next_records(shard_iterator, limit=5)
            shard_iterator = response['NextShardIterator']

            if len(response['Records']):
                break
        else:
            raise TimeoutError('No records found, aborting...')

        # Read the data, which should be the same as what we wrote
        self.assertEqual(1, len(response['Records']))
        self.assertEqual(data, response['Records'][0]['Data'])
