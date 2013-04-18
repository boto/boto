#! /usr/bin/env python

from boto.s3.connection import S3Connection
from boto.s3.encryptedkey import EncryptedKey
from boto.s3.key import Key
from boto.exception import S3ResponseError

conn = S3Connection()
bucket = conn.get_bucket("testingboto2")

if (bucket == None):
    print "no bucket"

string = "this is a test string2"

ekey = EncryptedKey("password",bucket,"cipherString2.txt")

ekey.set_contents_from_string(string)

print "done putting, now getting."

ekey = EncryptedKey("password",bucket,"cipherString2.txt")
print ekey.get_contents_as_string()

