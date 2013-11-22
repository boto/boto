import boto

from time import sleep
from unittest import TestCase

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
            sleep(15)
            response = kinesis.describe_stream('test')

            if response['StreamDescription']['StreamStatus'] == 'ACTIVE':
                break

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
            sleep(5)

            response = kinesis.get_next_records(shard_iterator, limit=5)
            shard_iterator = response['NextShardIterator']

            if len(response['Records']):
                break

        # Read the data, which should be the same as what we wrote
        self.assertEqual(1, len(response['Records']))
        self.assertEqual(data, response['Records'][0]['Data'])
