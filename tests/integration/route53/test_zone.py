# Copyright (c) 2011 Blue Pines Technologies LLC, Brad Carleton
# www.bluepines.org
# Copyright (c) 2012 42 Lines Inc., Jim Browne
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
from boto.exception import TooManyRecordsException


class TestRoute53Zone(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        route53 = Route53Connection()
        zone = route53.get_zone('example.com')
        if zone is not None:
            zone.delete()
        self.zone = route53.create_zone('example.com')

    def test_nameservers(self):
        self.zone.get_nameservers()

    def test_a(self):
        self.zone.add_a('example.com', '102.11.23.1', 80)
        record = self.zone.get_a('example.com')
        self.assertEquals(record.name, u'example.com.')
        self.assertEquals(record.resource_records, [u'102.11.23.1'])
        self.assertEquals(record.ttl, u'80')
        self.zone.update_a('example.com', '186.143.32.2', '800')
        record = self.zone.get_a('example.com')
        self.assertEquals(record.name, u'example.com.')
        self.assertEquals(record.resource_records, [u'186.143.32.2'])
        self.assertEquals(record.ttl, u'800')

    def test_cname(self):
        self.zone.add_cname('www.example.com', 'webserver.example.com', 200)
        record = self.zone.get_cname('www.example.com')
        self.assertEquals(record.name, u'www.example.com.')
        self.assertEquals(record.resource_records, [u'webserver.example.com.'])
        self.assertEquals(record.ttl, u'200')
        self.zone.update_cname('www.example.com', 'web.example.com', 45)
        record = self.zone.get_cname('www.example.com')
        self.assertEquals(record.name, u'www.example.com.')
        self.assertEquals(record.resource_records, [u'web.example.com.'])
        self.assertEquals(record.ttl, u'45')

    def test_mx(self):
        self.zone.add_mx('example.com',
                         ['10 mx1.example.com', '20 mx2.example.com'],
                         1000)
        record = self.zone.get_mx('example.com')
        self.assertEquals(set(record.resource_records),
                          set([u'10 mx1.example.com.',
                               u'20 mx2.example.com.']))
        self.assertEquals(record.ttl, u'1000')
        self.zone.update_mx('example.com',
                            ['10 mail1.example.com', '20 mail2.example.com'],
                            50)
        record = self.zone.get_mx('example.com')
        self.assertEquals(set(record.resource_records),
                          set([u'10 mail1.example.com.',
                               '20 mail2.example.com.']))
        self.assertEquals(record.ttl, u'50')

    def test_get_records(self):
        self.zone.get_records()

    def test_get_nameservers(self):
        self.zone.get_nameservers()

    def test_get_zones(self):
        route53 = Route53Connection()
        route53.get_zones()

    def test_identifiers_wrrs(self):
        self.zone.add_a('wrr.example.com', '1.2.3.4',
                        identifier=('foo', '20'))
        self.zone.add_a('wrr.example.com', '5.6.7.8',
                        identifier=('bar', '10'))
        wrrs = self.zone.find_records('wrr.example.com', 'A', all=True)
        self.assertEquals(len(wrrs), 2)
        self.zone.delete_a('wrr.example.com', all=True)

    def test_identifiers_lbrs(self):
        self.zone.add_a('lbr.example.com', '4.3.2.1',
                        identifier=('baz', 'us-east-1'))
        self.zone.add_a('lbr.example.com', '8.7.6.5',
                        identifier=('bam', 'us-west-1'))
        lbrs = self.zone.find_records('lbr.example.com', 'A', all=True)
        self.assertEquals(len(lbrs), 2)
        self.zone.delete_a('lbr.example.com',
                      identifier=('bam', 'us-west-1'))
        self.zone.delete_a('lbr.example.com',
                           identifier=('baz', 'us-east-1'))

    def test_toomany_exception(self):
        self.zone.add_a('exception.example.com', '4.3.2.1',
                        identifier=('baz', 'us-east-1'))
        self.zone.add_a('exception.example.com', '8.7.6.5',
                        identifier=('bam', 'us-west-1'))
        with self.assertRaises(TooManyRecordsException):
            lbrs = self.zone.get_a('exception.example.com')
        self.zone.delete_a('exception.example.com', all=True)

    @classmethod
    def tearDownClass(self):
        self.zone.delete_a('example.com')
        self.zone.delete_cname('www.example.com')
        self.zone.delete_mx('example.com')
        self.zone.delete()

if __name__ == '__main__':
    unittest.main(verbosity=3)
