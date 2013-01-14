# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
#
from tests.unit import unittest
from boto.connection import AWSQueryConnection


class TestListParamsSerialization(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.connection = AWSQueryConnection('access_key', 'secret_key')

    def test_complex_list_serialization(self):
        # This example is taken from the doc string of
        # build_complex_list_params.
        params = {}
        self.connection.build_complex_list_params(
            params, [('foo', 'bar', 'baz'), ('foo2', 'bar2', 'baz2')],
            'ParamName.member', ('One', 'Two', 'Three'))
        self.assertDictEqual({
            'ParamName.member.1.One': 'foo',
            'ParamName.member.1.Two': 'bar',
            'ParamName.member.1.Three': 'baz',
            'ParamName.member.2.One': 'foo2',
            'ParamName.member.2.Two': 'bar2',
            'ParamName.member.2.Three': 'baz2',
        }, params)

    def test_simple_list_serialization(self):
        params = {}
        self.connection.build_list_params(
            params, ['foo', 'bar', 'baz'], 'ParamName.member')
        self.assertDictEqual({
            'ParamName.member.1': 'foo',
            'ParamName.member.2': 'bar',
            'ParamName.member.3': 'baz',
        }, params)


if __name__ == '__main__':
    unittest.main()
