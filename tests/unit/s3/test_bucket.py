from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.s3.connection import S3Connection
from boto.s3.bucket import Bucket

class TestS3Bucket(AWSMockServiceTestCase):
    connection_class = S3Connection

    def setUp(self):
        super(TestS3Bucket, self).setUp()

    def test_bucket_create_bucket(self):
        self.set_http_response(status_code=200)
        bucket = self.service_connection.create_bucket('mybucket_create')
        self.assertEqual(bucket.name, 'mybucket_create')

    def test_bucket_constructor(self):
        self.set_http_response(status_code=200)
        bucket = Bucket(self.service_connection, 'mybucket_constructor')
        self.assertEqual(bucket.name, 'mybucket_constructor')

    def test_bucket_basics(self):
        self.set_http_response(status_code=200)
        bucket = self.service_connection.create_bucket('mybucket')
        self.assertEqual(bucket.__repr__(), '<Bucket: mybucket>')

    def test_bucket_new_key(self):
        self.set_http_response(status_code=200)
        bucket = self.service_connection.create_bucket('mybucket')
        key = bucket.new_key('mykey')

        self.assertEqual(key.bucket, bucket)
        self.assertEqual(key.key, 'mykey')

    def test_bucket_new_key_missing_name(self):
        self.set_http_response(status_code=200)
        bucket = self.service_connection.create_bucket('mybucket')

        with self.assertRaises(ValueError):
            key = bucket.new_key('')

    def test_bucket_delete_key_missing_name(self):
        self.set_http_response(status_code=200)
        bucket = self.service_connection.create_bucket('mybucket')

        with self.assertRaises(ValueError):
            key = bucket.delete_key('')
