#!/usr/bin/env python
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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

from mock import Mock

from tests.unit import unittest

from boto.rds import RDSConnection
from boto.rds.dbinstance import DBInstance


class TestDBInstance(unittest.TestCase):
    def setUp(self):
        self.mock_conn = Mock(RDSConnection)()
        self.mock_conn.region.name = 'region-name'
        self.mock_conn.account_id = '1234567890'
        self.dbi = DBInstance(self.mock_conn, 'dbid')

    def test_dbinstance_arn(self):
        self.assertEqual(self.dbi.arn, 'arn:aws:rds:region-name:1234567890:db:dbid')

    def test_dbinstance_tags(self):
        self.mock_conn.list_tags_for_resource.return_value = {'key1': 'value1', 'key2': 'value2'}
        self.assertEqual(len(self.dbi.tags), 2)
        self.assertTrue('key1' in self.dbi.tags)
        self.assertTrue('key2' in self.dbi.tags)
        self.assertEqual(self.dbi.tags['key1'], 'value1')
        self.assertEqual(self.dbi.tags['key2'], 'value2')

    def test_dbinstance_add_tags(self):
        self.mock_conn.list_tags_for_resource.return_value = {'key1': 'value1', 'key2': 'value2'}
        self.mock_conn.add_tags_to_resource.return_value = True
        self.dbi.add_tags({'key2': 'value22', 'key3': 'value3'})
        self.assertEqual(len(self.dbi.tags), 3)
        self.assertTrue('key2' in self.dbi.tags)
        self.assertTrue('key3' in self.dbi.tags)
        self.assertEqual(self.dbi.tags['key2'], 'value22')
        self.assertEqual(self.dbi.tags['key3'], 'value3')

    def test_dbinstance_add_tag(self):
        self.mock_conn.list_tags_for_resource.return_value = {'key1': 'value1', 'key2': 'value2'}
        self.mock_conn.add_tags_to_resource.return_value = True
        self.dbi.add_tag('key3', 'value3')
        self.assertEqual(len(self.dbi.tags), 3)
        self.assertTrue('key3' in self.dbi.tags)
        self.assertEqual(self.dbi.tags['key3'], 'value3')

    def test_dbinstance_remove_tags(self):
        self.mock_conn.list_tags_for_resource.return_value = {
            'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        self.mock_conn.remove_tags_from_resource.return_value = True
        self.dbi.remove_tags(['key1', 'key3'])
        self.assertEqual(len(self.dbi.tags), 1)
        self.assertTrue('key1' not in self.dbi.tags)
        self.assertTrue('key3' not in self.dbi.tags)

    def test_dbinstance_remove_tag(self):
        self.mock_conn.list_tags_for_resource.return_value = {
            'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        self.mock_conn.remove_tags_from_resource.return_value = True
        self.dbi.remove_tag('key2')
        self.assertEqual(len(self.dbi.tags), 2)
        self.assertTrue('key2' not in self.dbi.tags)


if __name__ == '__main__':
    unittest.main()

