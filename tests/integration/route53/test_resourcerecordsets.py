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

import unittest
from boto.route53.connection import Route53Connection
from boto.route53.record import ResourceRecordSets
from boto.exception import TooManyRecordsException


class TestRoute53ResourceRecordSets(unittest.TestCase):
    def setUp(self):
        super(TestRoute53ResourceRecordSets, self).setUp()
        self.conn = Route53Connection()
        self.zone = self.conn.create_zone('example.com')

    def tearDown(self):
        self.zone.delete()
        super(TestRoute53ResourceRecordSets, self).tearDown()

    def test_add_change(self):
        rrs = ResourceRecordSets(self.conn, self.zone.id)

        created = rrs.add_change("CREATE", "vpn.example.com.", "A")
        created.add_value('192.168.0.25')
        rrs.commit()

        rrs = ResourceRecordSets(self.conn, self.zone.id)
        deleted = rrs.add_change('DELETE', "vpn.example.com.", "A")
        deleted.add_value('192.168.0.25')
        rrs.commit()


if __name__ == '__main__':
    unittest.main()
