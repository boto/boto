#!/usr/bin/env python
# Copyright (c) 2006-2011 Mitch Garnaat http://garnaat.org/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
do the unit tests!
"""

import logging
import sys
import unittest
import getopt

from sqs.test_connection import SQSConnectionTest
from s3.test_connection import S3ConnectionTest
from s3.test_versioning import S3VersionTest
from s3.test_mfa import S3MFATest
from s3.test_encryption import S3EncryptionTest
from s3.test_bucket import S3BucketTest
from s3.test_key import S3KeyTest
from s3.test_multidelete import S3MultiDeleteTest
from s3.test_multipart import S3MultiPartUploadTest
from s3.test_gsconnection import GSConnectionTest
from s3.test_https_cert_validation import CertValidationTest
from ec2.test_connection import EC2ConnectionTest
from autoscale.test_connection import AutoscaleConnectionTest
from sdb.test_connection import SDBConnectionTest
from cloudfront.test_signed_urls import CloudfrontSignedUrlsTest
from dynamodb.test_layer1 import DynamoDBLayer1Test
from dynamodb.test_layer2 import DynamoDBLayer2Test
from sts.test_session_token import SessionTokenTest

def usage():
    print "test.py  [-t testsuite] [-v verbosity]"
    print "    -t   run specific testsuite (s3|ssl|s3mfa|gs|sqs|ec2|sdb|dynamodb|dynamodbL1|dynamodbL2|sts|all)"
    print "    -v   verbosity (0|1|2)"

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ht:v:",
                                   ["help", "testsuite", "verbosity"])
    except:
        usage()
        sys.exit(2)
    testsuite = "all"
    verbosity = 1
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-t", "--testsuite"):
            testsuite = a
        if o in ("-v", "--verbosity"):
            verbosity = int(a)
    if len(args) != 0:
        usage()
        sys.exit()
    try:
        tests = suite(testsuite)
    except ValueError:
        usage()
        sys.exit()
    if verbosity > 1:
        logging.basicConfig(level=logging.DEBUG)
    unittest.TextTestRunner(verbosity=verbosity).run(tests)

def suite(testsuite="all"):
    tests = unittest.TestSuite()
    if testsuite == "all":
        tests.addTest(unittest.makeSuite(SQSConnectionTest))
        tests.addTest(unittest.makeSuite(S3ConnectionTest))
        tests.addTest(unittest.makeSuite(EC2ConnectionTest))
        tests.addTest(unittest.makeSuite(SDBConnectionTest))
        tests.addTest(unittest.makeSuite(AutoscaleConnectionTest))
        tests.addTest(unittest.makeSuite(CloudfrontSignedUrlsTest))
        tests.addTest(unittest.makeSuite(DynamoDBLayer1Test))
        tests.addTest(unittest.makeSuite(DynamoDBLayer2Test))
    elif testsuite == "s3":
        tests.addTest(unittest.makeSuite(S3ConnectionTest))
        tests.addTest(unittest.makeSuite(S3BucketTest))
        tests.addTest(unittest.makeSuite(S3KeyTest))
        tests.addTest(unittest.makeSuite(S3MultiPartUploadTest))
        tests.addTest(unittest.makeSuite(S3VersionTest))
        tests.addTest(unittest.makeSuite(S3EncryptionTest))
        tests.addTest(unittest.makeSuite(S3MultiDeleteTest))
    elif testsuite == "ssl":
        tests.addTest(unittest.makeSuite(CertValidationTest))
    elif testsuite == "s3mfa":
        tests.addTest(unittest.makeSuite(S3MFATest))
    elif testsuite == "gs":
        tests.addTest(unittest.makeSuite(GSConnectionTest))
    elif testsuite == "sqs":
        tests.addTest(unittest.makeSuite(SQSConnectionTest))
    elif testsuite == "ec2":
        tests.addTest(unittest.makeSuite(EC2ConnectionTest))
    elif testsuite == "autoscale":
        tests.addTest(unittest.makeSuite(AutoscaleConnectionTest))
    elif testsuite == "sdb":
        tests.addTest(unittest.makeSuite(SDBConnectionTest))
    elif testsuite == "cloudfront":
        tests.addTest(unittest.makeSuite(CloudfrontSignedUrlsTest))
    elif testsuite == "dynamodb":
        tests.addTest(unittest.makeSuite(DynamoDBLayer1Test))
        tests.addTest(unittest.makeSuite(DynamoDBLayer2Test))
    elif testsuite == "dynamodbL1":
        tests.addTest(unittest.makeSuite(DynamoDBLayer1Test))
    elif testsuite == "dynamodbL2":
        tests.addTest(unittest.makeSuite(DynamoDBLayer2Test))
    elif testsuite == "sts":
        tests.addTest(unittest.makeSuite(SessionTokenTest))
    else:
        raise ValueError("Invalid choice.")
    return tests

if __name__ == "__main__":
    main()
