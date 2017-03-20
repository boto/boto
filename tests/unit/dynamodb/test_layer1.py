# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.
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
Tests for Layer1 of DynamoDB
"""
from tests.unit import unittest
from boto.dynamodb.layer1 import Layer1


class TestDynamoDBLayer1(unittest.TestCase):

    def test_dynamodb_local_settings(self):
        host, port, is_secure = 'localhost', 8000, False
        layer1 = Layer1('access_key', 'secret_key',
                        host=host, port=port, is_secure=is_secure)

        self.assertEqual(layer1.host, host)
        self.assertEqual(layer1.port, port)
        self.assertEqual(layer1.is_secure, is_secure)
