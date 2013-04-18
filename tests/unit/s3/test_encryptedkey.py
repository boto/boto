

from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.s3.connection import S3Connection
from boto.s3.bucket import Bucket

class TestS3EncryptedKey(AWSMockServiceTestCase):

 connection_class = S3Connection

    def setUp(self):
        super(TestS3Key, self).setUp()

    def default_body(self):
        return "default body"

    def test_with_blank_encryptionkey(self):





if __name__ == '__main__':
    unittest.main()
