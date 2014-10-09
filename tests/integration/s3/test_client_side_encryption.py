"""
Some unit tests for the S3 Client Side Encryption
"""
import os
import shutil
import subprocess
import unittest
import time
import urllib
import binascii
import urllib2

from boto.s3.connection import S3Connection


class S3ClientSideEncryptionTest(unittest.TestCase):
    s3 = True

    def setUp(self):
        super(S3ClientSideEncryptionTest, self).setUp()
        self.conn = S3Connection()
        self.bucket_name = 'client-side-encryption-%d' % int(time.time())
        self.bucket = self.conn.create_bucket(self.bucket_name)

    def tearDown(self):
        for key in self.bucket:
            key.delete()
        self.bucket.delete()
        super(S3ClientSideEncryptionTest, self).tearDown()

    def test_client_side_encryption(self):
        print('--- running {} tests ---'.format(self.__class__.__name__))

        client_side_encryption_keys = [
            ''.join([chr(0)] * (128 / 8)),  # Zero-key, AES 128
            ''.join([chr(0)] * (192 / 8)),  # Zero-key, AES 192
            ''.join([chr(0)] * (256 / 8)),  # Zero-key, AES 256
            os.urandom(128 / 8),  # Random-key, AES 128
            os.urandom(192 / 8),  # Random-key, AES 192
            os.urandom(256 / 8),  # Random-key, AES 256
        ]
        for encryption_key_index, encryption_key in enumerate(client_side_encryption_keys):
            encryption_key_hex = binascii.b2a_hex(encryption_key)
            encryption_key_base64 = binascii.b2a_base64(encryption_key)
            print 'Key of size {}, hex={}, base64={}'.format(
                8 * len(encryption_key),
                encryption_key_hex,
                encryption_key_base64
            )

            encrypted_connection = S3Connection(client_side_encryption_key=encryption_key)
            encrypted_bucket = encrypted_connection.get_bucket(self.bucket_name)

            unencrypted_connection = S3Connection()
            unencrypted_bucket = unencrypted_connection.get_bucket(self.bucket_name)

            key_name_base = 'foo-{key_content_index}-encrypted-using-key-{encryption_key_index}-method-{method_index}'
            key_contents = [
                '0123456701234567',   # Small content, multiple of the block size (16)
                '0123456701234567' + '0',  # Small content, needs padding
                '0123456701234567' * 2**6,        # 1Kb content, multiple of the block size (16)
                '0123456801234567' * 2**6 + '0',  # 1Kb content, needs padding
            ]
            for key_content_index, key_content in enumerate(key_contents):
                print '\tTest using content {}'.format(key_content_index)

                methods = [
                    lambda key, content, filename, fp: key.set_contents_from_string(content),
                    lambda key, content, filename, fp: key.set_contents_from_filename(filename),
                    lambda key, content, filename, fp: key.set_contents_from_file(fp),
                    # BotoClientError: s3 does not support chunked transfer
                    # lambda key, content, filename, fp: key.set_contents_from_stream(fp),
                ]
                for method_index, method in enumerate(methods):
                    print '\t\tTest using method {}'.format(method_index)

                    key_size = len(key_content)
                    key_name = key_name_base.format(key_content_index=key_content_index,
                                                    encryption_key_index=encryption_key_index,
                                                    method_index=method_index)

                    key_content_filename = '/tmp/{}'.format(key_name)
                    with open(key_content_filename, 'w') as key_content_fp:
                        key_content_fp.write(key_content)

                    # Encrypted content shouldn't be readable
                    with open(key_content_filename, 'r') as key_content_fp:
                        encrypted_key = encrypted_bucket.new_key(key_name)
                        unencrypted_key = unencrypted_bucket.new_key(key_name)
                        method(encrypted_key, key_content, key_content_filename, key_content_fp)
                        raw_content = unencrypted_key.get_contents_as_string()
                        decrypted_content = encrypted_key.get_contents_as_string()
                        self.assertNotEqual(key_content, raw_content)
                        self.assertEqual(key_content, decrypted_content)

                    # Unencrypted content should still be readable
                    # (files stored in clear can still be read)
                    with open(key_content_filename, 'r') as key_content_fp:
                        encrypted_key = encrypted_bucket.new_key(key_name)
                        unencrypted_key = unencrypted_bucket.new_key(key_name)
                        method(unencrypted_key, key_content, key_content_filename, key_content_fp)
                        raw_content = unencrypted_key.get_contents_as_string()
                        decrypted_content = encrypted_key.get_contents_as_string()
                        self.assertEqual(key_content, raw_content)
                        self.assertEqual(key_content, decrypted_content)

                    # Successive GET should return the same value (checks internal state/caching)
                    with open(key_content_filename, 'r') as key_content_fp:
                        encrypted_key = encrypted_bucket.new_key(key_name)
                        method(encrypted_key, key_content, key_content_filename, key_content_fp)
                        decrypted_content1 = encrypted_key.get_contents_as_string()
                        decrypted_content2 = encrypted_key.get_contents_as_string()
                        self.assertEqual(key_content, decrypted_content1)
                        self.assertEqual(key_content, decrypted_content2)

                    # PUT/GET x2 using the same key object
                    # This checks if the iv and the key are updated properly
                    encrypted_key = encrypted_bucket.new_key(key_name)
                    with open(key_content_filename, 'r') as key_content_fp:
                        method(encrypted_key, key_content, key_content_filename, key_content_fp)
                        decrypted_content1 = encrypted_key.get_contents_as_string()
                    with open(key_content_filename, 'r') as key_content_fp:
                        method(encrypted_key, key_content, key_content_filename, key_content_fp)
                        decrypted_content2 = encrypted_key.get_contents_as_string()
                    self.assertEqual(key_content, decrypted_content1)
                    self.assertEqual(key_content, decrypted_content2)

                    # Check that the size is correct
                    with open(key_content_filename, 'r') as key_content_fp:
                        # The size should be set after an upload
                        encrypted_key1 = encrypted_bucket.new_key(key_name)
                        method(encrypted_key1, key_content, key_content_filename, key_content_fp)
                        self.assertEqual(encrypted_key1.size, key_size)
                        # The size should be set after a download
                        encrypted_key2 = encrypted_bucket.new_key(key_name)
                        decrypted_content2 = encrypted_key2.get_contents_as_string()
                        self.assertEqual(encrypted_key2.size, key_size)

        print('--- {} tests completed ---'.format(self.__class__.__name__))
