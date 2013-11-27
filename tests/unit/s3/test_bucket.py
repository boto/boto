# -*- coding: utf-8 -*-
from mock import patch

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

    def test_bucket_kwargs_misspelling(self):
        self.set_http_response(status_code=200)
        bucket = self.service_connection.create_bucket('mybucket')

        with self.assertRaises(TypeError):
            bucket.get_all_keys(delimeter='foo')

    def test__get_all_query_args(self):
        bukket = Bucket()

        # Default.
        qa = bukket._get_all_query_args({})
        self.assertEqual(qa, '')

        # Default with initial.
        qa = bukket._get_all_query_args({}, 'initial=1')
        self.assertEqual(qa, 'initial=1')

        # Single param.
        qa = bukket._get_all_query_args({
            'foo': 'true'
        })
        self.assertEqual(qa, 'foo=true')

        # Single param with initial.
        qa = bukket._get_all_query_args({
            'foo': 'true'
        }, 'initial=1')
        self.assertEqual(qa, 'initial=1&foo=true')

        # Multiple params with all the weird cases.
        multiple_params = {
            'foo': 'true',
            # Ensure Unicode chars get encoded.
            'bar': '☃',
            # Underscores are bad, m'kay?
            'some_other': 'thing',
            # Change the variant of ``max-keys``.
            'maxkeys': 0,
            # ``None`` values get excluded.
            'notthere': None,
            # Empty values also get excluded.
            'notpresenteither': '',
        }
        qa = bukket._get_all_query_args(multiple_params)
        self.assertEqual(
            qa,
            'bar=%E2%98%83&max-keys=0&foo=true&some-other=thing'
        )

        # Multiple params with initial.
        qa = bukket._get_all_query_args(multiple_params, 'initial=1')
        self.assertEqual(
            qa,
            'initial=1&bar=%E2%98%83&max-keys=0&foo=true&some-other=thing'
        )

    @patch.object(Bucket, 'get_all_keys')
    def test_bucket_copy_key_no_validate(self, mock_get_all_keys):
        self.set_http_response(status_code=200)
        bucket = self.service_connection.create_bucket('mybucket')

        self.assertFalse(mock_get_all_keys.called)
        self.service_connection.get_bucket('mybucket', validate=True)
        self.assertTrue(mock_get_all_keys.called)

        mock_get_all_keys.reset_mock()
        self.assertFalse(mock_get_all_keys.called)
        try:
            bucket.copy_key('newkey', 'srcbucket', 'srckey', preserve_acl=True)
        except:
            # Will throw because of empty response.
            pass
        self.assertFalse(mock_get_all_keys.called)
