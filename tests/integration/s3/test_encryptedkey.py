
"""
tests for the EncryptedKey S3 class
"""

from tests.unit import unittest
import time
import math
import os
import StringIO
from boto.s3.connection import S3Connection
from boto.s3.encryptedkey import EncryptedKey
from boto.exception import S3ResponseError

encryptionkey = "p@ssword123"

def compute_encrypted_size(content,blocksize):
    contentlen = len(content)
    print 'contentlen:' , contentlen
    contentlen = float(contentlen)
    paddedcontentlen = blocksize * (int(math.ceil(contentlen/blocksize)))
    paddedcontentlen = paddedcontentlen + blocksize #add the IV
    print 'paddedlen:' , paddedcontentlen
    base64len = 4 * int(math.ceil( paddedcontentlen / 3.0))
    print 'b64:' , base64len
    return base64len


class S3EncryptedKeyTest (unittest.TestCase):
    s3 = True
    s3key2 = True

    def setUp(self):
        self.conn = S3Connection()
        self.bucket_name = 'keytest-%d' % int(time.time())
        self.bucket = self.conn.create_bucket(self.bucket_name)
        self.bucket.set_key_class(EncryptedKey)

    def tearDown(self):
        for key in self.bucket:
            key.delete()
        self.bucket.delete()

    def test_set_contents_from_file_dataloss(self):
        # Create an empty stringio and write to it.
        content = "abcde"
        sfp = StringIO.StringIO()
        sfp.write(content)
        # Try set_contents_from_file() without rewinding sfp
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        try:
            k.set_contents_from_file(sfp)
            self.fail("forgot to rewind so should fail.")
        except AttributeError:
            pass
        # call with rewind and check if we wrote 5 bytes
        k.set_contents_from_file(sfp, rewind=True)
        self.assertEqual(k.size, 5)
        # check actual contents by getting it.
        kn = self.bucket.new_key("k")
        kn.set_encryption_key(encryptionkey)
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, content)

        # finally, try with a 0 length string
        sfp = StringIO.StringIO()
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.set_contents_from_file(sfp)
        self.assertEqual(k.size, 0)
        # check actual contents by getting it.
        kn = self.bucket.new_key("k")
        kn.set_encryption_key(encryptionkey)
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, "")

    def test_set_contents_as_file(self):
        content="01234567890123456789"

        sfp = StringIO.StringIO(content)

        # fp is set at 0 for just opened (for read) files.
        # set_contents should write full content to key.
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)

        #to account for block padding up to 128 bits (16 bytes)
        #and the IV (which is one 16 byte block)
        #and Base64 encoding which has some overhead.
        blocksize = k.aes.BS

        encryptedsize = compute_encrypted_size(content,blocksize)
        print "enc size:", encryptedsize

        k.set_contents_from_file(sfp)
        print "k size:",k.size
        self.assertEqual(k.size, encryptedsize)
        kn = self.bucket.new_key("k")
        kn.set_encryption_key(encryptionkey)
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, content)

        # set fp to 5 and set contents. this should
        # set "567890123456789" to the key
        sfp = StringIO.StringIO(content)
        sfp.seek(5,os.SEEK_SET)
        print sfp.tell()
        k = None
        k = self.bucket.new_key("k2")
        k.set_encryption_key(encryptionkey)

        encryptedsize = compute_encrypted_size(content[5:],blocksize)
        print "enc size:", encryptedsize
        k.set_contents_from_file(sfp)
        print "k size:",k.size
        self.assertEqual(k.size, encryptedsize)

        kn = self.bucket.new_key("k2")
        kn.set_encryption_key(encryptionkey)
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, content[5:])

        # set fp to 5 and only set 5 bytes. this should
        # write the value "56789" to the key.
        sfp = StringIO.StringIO(content)
        sfp.seek(5)
        k = self.bucket.new_key("k3")
        k.set_encryption_key(encryptionkey)
        k.set_contents_from_file(sfp, size=5)

        encryptedsize = compute_encrypted_size(content[5:10],blocksize)

        print "enc size:", encryptedsize
        print "k size:",k.size
        self.assertEqual(k.size, encryptedsize)
        self.assertEqual(sfp.tell(), 10)
        kn = self.bucket.new_key("k3")
        kn.set_encryption_key(encryptionkey)
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, content[5:10])

    def test_set_contents_with_md5(self):
        content="01234567890123456789"
        sfp = StringIO.StringIO(content)

        # fp is set at 0 for just opened (for read) files.
        # set_contents should write full content to key.
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        good_md5 = k.compute_md5(sfp)
        k.set_contents_from_file(sfp, md5=good_md5)
        kn = self.bucket.new_key("k")
        kn.set_encryption_key(encryptionkey)
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, content)

        # set fp to 5 and only set 5 bytes. this should
        # write the value "56789" to the key.
        sfp.seek(5)
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        good_md5 = k.compute_md5(sfp, size=5)
        k.set_contents_from_file(sfp, size=5, md5=good_md5)
        self.assertEqual(sfp.tell(), 10)
        kn = self.bucket.new_key("k")
        kn.set_encryption_key(encryptionkey)
        ks = kn.get_contents_as_string()
        self.assertEqual(ks, content[5:10])

        # let's try a wrong md5 by just altering it.
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        sfp.seek(0)
        hexdig, base64 = k.compute_md5(sfp)
        bad_md5 = (hexdig, base64[3:])
        try:
            k.set_contents_from_file(sfp, md5=bad_md5)
            self.fail("should fail with bad md5")
        except S3ResponseError:
            pass

    def test_get_contents_with_md5(self):
        content="01234567890123456789"
        sfp = StringIO.StringIO(content)

        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.set_contents_from_file(sfp)
        kn = self.bucket.new_key("k")
        kn.set_encryption_key(encryptionkey)
        s = kn.get_contents_as_string()
        self.assertEqual(kn.md5, k.md5)
        self.assertEqual(s, content)

    def test_file_callback(self):
        def callback(wrote, total):
            self.my_cb_cnt += 1
            self.assertNotEqual(wrote, self.my_cb_last, "called twice with same value")
            self.my_cb_last = wrote

        # Zero bytes written => 1 call
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.BufferSize = 2
        sfp = StringIO.StringIO("")
        k.set_contents_from_file(sfp, cb=callback, num_cb=10)
        self.assertEqual(self.my_cb_cnt, 1)
        self.assertEqual(self.my_cb_last, 0)
        sfp.close()

        # Read back zero bytes => 1 call
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback)
        self.assertEqual(self.my_cb_cnt, 1)
        self.assertEqual(self.my_cb_last, 0)

        content="01234567890123456789"
        sfp = StringIO.StringIO(content)

        # expect 2 calls due start/finish
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.set_contents_from_file(sfp, cb=callback, num_cb=10)
        self.assertEqual(self.my_cb_cnt, 2)
        self.assertEqual(self.my_cb_last, 20)

        # Read back all bytes => 2 calls
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback)
        self.assertEqual(self.my_cb_cnt, 2)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # rewind sfp and try upload again. -1 should call
        # for every read/write so that should make 11 when bs=2
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=-1)
        self.assertEqual(self.my_cb_cnt, 11)
        self.assertEqual(self.my_cb_last, 20)

        # Read back all bytes => 11 calls
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=-1)
        self.assertEqual(self.my_cb_cnt, 11)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 1 times => 2 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=1)
        self.assertTrue(self.my_cb_cnt <= 2)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 1 times => 2 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=1)
        self.assertTrue(self.my_cb_cnt <= 2)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 2 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=2)
        self.assertTrue(self.my_cb_cnt <= 2)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 2 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=2)
        self.assertTrue(self.my_cb_cnt <= 2)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 3 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=3)
        self.assertTrue(self.my_cb_cnt <= 3)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 3 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=3)
        self.assertTrue(self.my_cb_cnt <= 3)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 4 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=4)
        self.assertTrue(self.my_cb_cnt <= 4)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 4 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=4)
        self.assertTrue(self.my_cb_cnt <= 4)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 6 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=6)
        self.assertTrue(self.my_cb_cnt <= 6)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 6 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=6)
        self.assertTrue(self.my_cb_cnt <= 6)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 10 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=10)
        self.assertTrue(self.my_cb_cnt <= 10)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 10 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=10)
        self.assertTrue(self.my_cb_cnt <= 10)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

        # no more than 1000 times
        # last time always 20 bytes
        sfp.seek(0)
        self.my_cb_cnt = 0
        self.my_cb_last = None
        k = self.bucket.new_key("k")
        k.set_encryption_key(encryptionkey)
        k.BufferSize = 2
        k.set_contents_from_file(sfp, cb=callback, num_cb=1000)
        self.assertTrue(self.my_cb_cnt <= 1000)
        self.assertEqual(self.my_cb_last, 20)

        # no more than 1000 times
        self.my_cb_cnt = 0
        self.my_cb_last = None
        s = k.get_contents_as_string(cb=callback, num_cb=1000)
        self.assertTrue(self.my_cb_cnt <= 1000)
        self.assertEqual(self.my_cb_last, 20)
        self.assertEqual(s, content)

    def test_website_redirects(self):
        self.bucket.configure_website('index.html')
        key = self.bucket.new_key('redirect-key')
        key.set_encryption_key(encryptionkey)
        self.assertTrue(key.set_redirect('http://www.amazon.com/'))
        self.assertEqual(key.get_redirect(), 'http://www.amazon.com/')

        self.assertTrue(key.set_redirect('http://aws.amazon.com/'))
        self.assertEqual(key.get_redirect(), 'http://aws.amazon.com/')

    def test_website_redirect_none_configured(self):
        key = self.bucket.new_key('redirect-key')
        key.set_encryption_key(encryptionkey)
        key.set_contents_from_string('')
        self.assertEqual(key.get_redirect(), None)

    def test_website_redirect_with_bad_value(self):
        self.bucket.configure_website('index.html')
        key = self.bucket.new_key('redirect-key')
        key.set_encryption_key(encryptionkey)
        with self.assertRaises(key.provider.storage_response_error):
            # Must start with a / or http
            key.set_redirect('ftp://ftp.example.org')
        with self.assertRaises(key.provider.storage_response_error):
            # Must start with a / or http
            key.set_redirect('')


#class S3EncryptedKeyTest(S3KeyTest):
#    
#    encryptionkey = "p@ssword123"
#
#    def setUp(self):
#        self.conn = S3Connection()
#        self.bucket_name = 'encryptedkeytest-%d' % int(time.time())
#        #set the keytype for the bucket, to EncryptedKey.
#        self.bucket = self.conn.create_bucket(self.bucket_name, boto.s3.encryptedkey.EncryptedKey)
#
#
#    def tearDown(self):
#        for key in self.bucket:
#            key.delete()
#        self.bucket.delete()
#
#    def test_contents_from_string(self):
#        #put a string, and attempt to recover
#        #string value should be identical
#        content = "12345678"
#        k = self.bucket.new_key("k")
#        k.set_encryption_key(encryptionkey)
#        k.set_contents_from_string(content)
#        contentReturned = k.get_contents_as_string()
#        self.assertEqual(content,contentReturned)
#
#    def test_contents_from_file(self):
#        #create a file pointer, read the contents,
#        #put to S3, retrieve it back, and ensure files are identical
#        content = "12345678"
#        sfp = StringIO.StringIO()
#        sfp.write(content)
#        sfp.seek(0)
#
#        k = self.bucket.new_key("k")
#        k.set_encryption_key(encryptionkey)
#        k.set_contents_from_string(content)
#        contentReturned = k.get_contents_to_file()
#        self.assertEqual(content,contentReturned)
#
#
#
#
#    def test_contents_from_filename(self):
#        #create a random file, read the contents,
#        #put to S3, retrieve it back, and ensure files are identical
#
#
#    def test_nonzero_file_offset(self):
#        #test with filepointer that is not at the start of the file
#
#    def test_null_content(self);
#        #test that an empty string and file don't cause errors.
#
#
#    def 
