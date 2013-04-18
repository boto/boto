
"""
tests for the EncryptedKey S3 class
"""

from tests.unit import unittest
import time
import StringIO
from boto.s3.connection import S3Connection
from boto.s3.key import EncryptedKey
from boto.exception import S3ResponseError

class S3EncryptedKeyTest(S3KeyTest):
    
    encryptionkey = "p@ssword123"

    def setUp(self):
        self.conn = S3Connection()
        self.bucket_name = 'encryptedkeytest-%d' % int(time.time())
        #set the keytype for the bucket, to EncryptedKey.
        self.bucket = self.conn.create_bucket(self.bucket_name, boto.s3.encryptedkey.EncryptedKey)


    def tearDown(self):
        for key in self.bucket:
            key.delete()
        self.bucket.delete()

    def test_contents_from_string(self):
        #put a string, and attempt to recover
        #string value should be identical
        content = "12345678"
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.set_contents_from_string(content)
        contentReturned = k.get_contents_as_string()
        self.assertEqual(content,contentReturned)

    def test_contents_from_file(self):
        #create a file pointer, read the contents,
        #put to S3, retrieve it back, and ensure files are identical
        content = "12345678"
        sfp = StringIO.StringIO()
        sfp.write(content)
        sfp.seek(0)

        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.set_contents_from_string(content)
        contentReturned = k.get_contents_to_file()
        self.assertEqual(content,contentReturned)




    def test_contents_from_filename(self):
        #create a random file, read the contents,
        #put to S3, retrieve it back, and ensure files are identical


    def test_nonzero_file_offset(self):
        #test with filepointer that is not at the start of the file

    def test_null_content(self);
        #test that an empty string and file don't cause errors.


    def 
