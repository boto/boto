#!/usr/bin/env python

# Copyright (c) 2006-2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2009, Eucalyptus Systems, Inc.
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
Some unit tests for the Route53Connection
"""

import unittest
import time
from boto.route53 import Route53Connection
from boto.route53.change_batch import ChangeBatch

class Route53ConnectionTest(unittest.TestCase):
    def test_1_basic(self):
        connection = Route53Connection()
        zones = connection.get_all_hosted_zones()
        assert len(zones) > 0

        # Make a new zone
        print 'Creating zone...'
        zone = connection.create_hosted_zone("fake.me.")
        assert zone.name == "fake.me."
        assert zone.change_info
        self.wait_for_ready(zone.change_info)

        # Create a new record
        print 'Creating a new record...'
        change = ChangeBatch(connection, zone.id)
        change.add_change("CREATE", "test.fake.me.", "CNAME", 60, "google.com.")
        self.wait_for_ready(change.commit())

        # Destroy the new record
        for r in zone.records():
            if r.name == "test.fake.me.":
                print "Deleting record..."
                change = ChangeBatch(connection, zone.id)
                change.add_change("DELETE", r.name, r.type, r.ttl, r.value)
                self.wait_for_ready(change.commit())
                break
        else:
            print "Couldn't find record to delete!"

        # Destroy the zone
        print 'Deleting zone...'
        change = connection.delete_hosted_zone(zone.id)
        self.wait_for_ready(change)

    def wait_for_ready(self, change):
        while change.status == 'PENDING':
            time.sleep(5)
            change.update()
