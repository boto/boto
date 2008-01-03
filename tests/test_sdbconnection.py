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
Some unit tests for the SDBConnection
"""

import unittest
import time
from boto.sdb.connection import SDBConnection
from boto.exception import SDBResponseError

class SDBConnectionTest (unittest.TestCase):

    def test_1_basic(self):
        print '--- running SDBConnection tests ---'
        c = SDBConnection()
        rs = c.get_all_domains()
        num_domains = len(rs)
    
        # try illegal name
        try:
            domain = c.create_domain('bad:domain:name')
        except SDBResponseError:
            pass
        
        # now create one that should work and should be unique (i.e. a new one)
        domain_name = 'test%d' % int(time.time())
        domain = c.create_domain(domain_name)
        rs  = c.get_all_domains()
        assert len(rs) == num_domains+1

        # now let's a couple of items and attributes
        item_1 = 'item1'
        same_value = 'same_value'
        attrs_1 = {'name1' : same_value, 'name2' : 'diff_value_1'}
        domain.put_attributes(item_1, attrs_1)
        item_2 = 'item2'
        attrs_2 = {'name1' : same_value, 'name2' : 'diff_value_2'}
        domain.put_attributes(item_2, attrs_2)
        time.sleep(10)

        # try to get the attributes and see if they match
        item = domain.get_attributes(item_1)
        assert len(item.keys()) == len(attrs_1.keys())
        assert item['name1'] == attrs_1['name1']
        assert item['name2'] == attrs_1['name2']

        # try a search or two
        rs = domain.query("['name1'='%s']" % same_value)
        n = 0
        for item in rs:
            n += 1
        assert n == 2
        rs = domain.query("['name2'='diff_value_2']")
        n = 0
        for item in rs:
            n += 1
        assert n == 1

        # delete all attributes associated with item_1
        stat = domain.delete_attributes(item_1)
        assert stat

        # now delete the domain
        stat = c.delete_domain(domain)
        assert stat

        print '--- tests completed ---'
    
