
"""
tests for the EncryptedKey S3 class
"""

from tests.unit import unittest
import time
import StringIO
from boto.s3.connection import S3Connection
from boto.s3.key import EncryptedKey
from boto.exception import S3ResponseError

class S3EncryptedKeyTest(unittest.TestCase):
    s3 = True

    def setUp(self):
        self.conn = S3Connection()
        self.bucket_name = 'encryptedkeytest-%d' % int(time.time())
        self.bucket = self.conn.create_bucket(self.bucket_name)

    def tearDown(self):
        for key in self.bucket:
            key.delete()
        self.bucket.delete()

    def test_contents_from_string(self):
        #put a string, and attempt to recover
        #string value should be identical


    def test_contents_from_file(self):
        #create a random file, read the contents,
        #put to S3, retrieve it back, and endure files are identical


    def 
