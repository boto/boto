#! /usr/bin/env python

from boto.s3.connection import S3Connection
from boto.s3.encryptedkey import EncryptedKey
from boto.exception import S3ResponseError

conn = S3Connection()
bucket = conn.get_bucket("testingboto")

if (bucket == None):
    print "no bucket"

string = "this is a test string"

ekey = EncryptedKey("password",bucket,"cipherString")

ekey.set_contents_from_string(string)
print "done"
