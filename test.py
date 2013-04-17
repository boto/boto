#! /usr/bin/env python

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.exception import S3ResponseError

import sys

conn = S3Connection()

if (conn == None):
    print "no connection"
    sys.exit(1)
bucket = conn.get_bucket("testingboto")

if (bucket == None):
    print "no bucket"

print bucket

string = "this is a test string"

print "creating encryptedKey"
key = Key(bucket,"cipherString2","password")

print "setting contents"
key.set_contents_from_string(string)
print "done"
