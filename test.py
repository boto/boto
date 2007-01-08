#!/usr/bin/env python
# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
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

import sys, os, unittest
from optparse import OptionParser
import boto

sys.path.append('tests/')

from test_sqsconnection import SQSConnectionTest
from test_s3connection import S3ConnectionTest
from test_ec2connection import EC2ConnectionTest

suite = unittest.TestSuite()
suite.addTest(unittest.makeSuite(SQSConnectionTest))
suite.addTest(unittest.makeSuite(S3ConnectionTest))
suite.addTest(unittest.makeSuite(EC2ConnectionTest))
verbosity = 1
unittest.TextTestRunner(verbosity=verbosity).run(suite)
