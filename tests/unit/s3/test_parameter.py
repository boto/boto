# -*- coding: utf-8 -*-

# Copyright (c) 2014 Steven Richards <sbrichards@mit.edu>
# All rights reserved.
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
Unit test for passing in 'host' parameter and overriding the region
See issue: #2522
"""

import os
import unittest
import time
import socket
from boto.compat import StringIO

import mock

import boto
from boto.s3.connection import S3Connection

class S3SpecifyHost(unittest.TestCase):
    s3 = True

    def testWithNonAWSHost(self):
        connect_args = dict({'host':'www.not-a-website.com'})
        connection = boto.s3.connect_to_region('us-east-1', **connect_args)
        self.assertEquals('S3Connection:www.not-a-website.com', str(connection))
        self.assertEquals(boto.s3.connection.S3Connection, type(connection))

    def testSuccessWithHostOverrideRegion(self):
        connect_args = dict({'host':'s3.amazonaws.com'})
        connection = boto.s3.connect_to_region('us-west-2', **connect_args)
        self.assertEquals('S3Connection:s3.amazonaws.com', str(connection))
        self.assertEquals(boto.s3.connection.S3Connection, type(connection))

    def testSuccessWithDefaultUSWest1(self):
        connection = boto.s3.connect_to_region('us-west-2')
        self.assertEquals('S3Connection:s3-us-west-2.amazonaws.com', str(connection))
        self.assertEquals(boto.s3.connection.S3Connection, type(connection))

    def testSuccessWithDefaultUSEast1(self):
        connection = boto.s3.connect_to_region('us-east-1')
        self.assertEquals('S3Connection:s3.amazonaws.com', str(connection))
        self.assertEquals(boto.s3.connection.S3Connection, type(connection))

    def testDefaultWithInvalidHost(self):
        connect_args = dict({'host':''})
        connection = boto.s3.connect_to_region('us-west-2', **connect_args)
        self.assertEquals('S3Connection:s3-us-west-2.amazonaws.com', str(connection))
        self.assertEquals(boto.s3.connection.S3Connection, type(connection))

    def testDefaultWithInvalidHostNone(self):
        connect_args = dict({'host':None})
        connection = boto.s3.connect_to_region('us-east-1', **connect_args)
        self.assertEquals('S3Connection:s3.amazonaws.com', str(connection))
        self.assertEquals(boto.s3.connection.S3Connection, type(connection))

    def tearDown(self):
        self = connection = connect_args = None
