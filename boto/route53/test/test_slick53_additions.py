import unittest
from boto.route53.connection import Route53Connection

class TestRoute53(unittest.TestCase):
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
        self.zone.add_mx(['10 mx1.example.com', '20 mx2.example.com'], 1000)
        record = self.zone.get_mx()
        self.assertEquals(set(record.resource_records),
                          set([u'10 mx1.example.com.', u'20 mx2.example.com.']))
        self.assertEquals(record.ttl, u'1000')
        self.zone.update_mx(['10 mail1.example.com', '20 mail2.example.com'], 50)
        record = self.zone.get_mx()
        self.assertEquals(set(record.resource_records),
                          set([u'10 mail1.example.com.', '20 mail2.example.com.']))
        self.assertEquals(record.ttl, u'50')

    def test_get_records(self):
        self.zone.get_records()

    def test_get_zones(self):
        route53 = Route53Connection()
        route53.get_zones()

    @classmethod
    def tearDownClass(self):
        self.zone.delete_a('example.com')
        self.zone.delete_cname('www.example.com')
        self.zone.delete_mx()
        self.zone.delete()

if __name__ == '__main__':
    unittest.main(verbosity=3)
