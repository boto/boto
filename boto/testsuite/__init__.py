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
Test suites!
"""
import unittest

from sqs.test_connection import SQSConnectionTest
from s3.test_connection import S3ConnectionTest
from s3.test_versioning import S3VersionTest
from s3.test_gsconnection import GSConnectionTest
from s3.test_https_cert_validation import CertValidationTest
from ec2.test_connection import EC2ConnectionTest
from autoscale.test_connection import AutoscaleConnectionTest
from sdb.test_connection import SDBConnectionTest

def suite(testsuite="all"):
    tests = unittest.TestSuite()
    if testsuite == "all":
        tests.addTest(unittest.makeSuite(SQSConnectionTest))
        tests.addTest(unittest.makeSuite(S3ConnectionTest))
        tests.addTest(unittest.makeSuite(EC2ConnectionTest))
        tests.addTest(unittest.makeSuite(SDBConnectionTest))
        tests.addTest(unittest.makeSuite(AutoscaleConnectionTest))
    elif testsuite == "s3":
        tests.addTest(unittest.makeSuite(S3ConnectionTest))
        tests.addTest(unittest.makeSuite(S3VersionTest))
    elif testsuite == "ssl":
        tests.addTest(unittest.makeSuite(CertValidationTest))
    elif testsuite == "s3ver":
        tests.addTest(unittest.makeSuite(S3VersionTest))
    elif testsuite == "s3nover":
        tests.addTest(unittest.makeSuite(S3ConnectionTest))
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
    else:
        raise ValueError("Invalid choice.")
    return tests
