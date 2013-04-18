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
keyname = "cipherString3.txt"

ekey = EncryptedKey("password",bucket,keyname)

ekey.set_contents_from_string(string)

print "original plaintext: " , string
print "done putting, now getting."
key = Key(bucket,keyname)
ekey2 = EncryptedKey("password",bucket,keyname)
print "reg key contents: ",key.get_contents_as_string()
print "enc key contents: ",ekey2.get_contents_as_string()

