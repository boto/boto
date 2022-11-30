#!/usr/bin/env python
# Copyright (c) 2014 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
from boto.route53.record import ResourceRecordSets
from tests.compat import mock, unittest


class TestRecord(unittest.TestCase):
    def test_add_change(self):
        resource_record_sets = ResourceRecordSets()
        resource_records = ['some.record.1', 'some.record.2']
        change = resource_record_sets.add_change('DELETE', 'some.zone', 'CNAME', resource_records=resource_records)
        self.assertEqual(len(change.resource_records), 2)
        self.assertEqual(change.resource_records[0], 'some.record.1')
        self.assertEqual(change.resource_records[1], 'some.record.2')
        self.assertEqual(change.name, 'some.zone')
        self.assertEqual(change.type, 'CNAME')
        self.assertEqual(len(resource_record_sets.changes), 1)
        self.assertEqual(resource_record_sets.changes[0][0], 'DELETE')
        self.assertEqual(resource_record_sets.changes[0][1], change)

if __name__ == "__main__":
    unittest.main()
