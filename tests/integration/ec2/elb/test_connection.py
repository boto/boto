# Copyright (c) 2010 Hunter Blanks http://artifex.org/~hblanks/
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
Initial, and very limited, unit tests for ELBConnection.
"""

import unittest
from boto.ec2.elb import ELBConnection

class ELBConnectionTest(unittest.TestCase):
    ec2 = True

    def setUp(self):
        """Creates a named load balancer that can be safely
        deleted at the end of each test"""
        self.conn = ELBConnection()
        self.name = 'elb-boto-unit-test'
        self.availability_zones = ['us-east-1a']
        self.listeners = [(80, 8000, 'HTTP')]
        self.balancer = self.conn.create_load_balancer(self.name, self.availability_zones, self.listeners)

    def tearDown(self):
        """ Deletes the test load balancer after every test.
        It does not delete EVERY load balancer in your account"""
        self.balancer.delete()

    def test_build_list_params(self):
        params = {}
        self.conn.build_list_params(
            params, ['thing1', 'thing2', 'thing3'], 'ThingName%d')
        expected_params = {
            'ThingName1': 'thing1',
            'ThingName2': 'thing2',
            'ThingName3': 'thing3'
            }
        self.assertEqual(params, expected_params)

    # TODO: for these next tests, consider sleeping until our load
    # balancer comes up, then testing for connectivity to
    # balancer.dns_name, along the lines of the existing EC2 unit tests.

    def test_create_load_balancer(self):
        self.assertEqual(self.balancer.name, self.name)
        self.assertEqual(self.balancer.availability_zones,\
            self.availability_zones)
        self.assertEqual(self.balancer.listeners, self.listeners)

        balancers = self.conn.get_all_load_balancers()
        self.assertEqual([lb.name for lb in balancers], [self.name])

    def test_create_load_balancer_listeners(self):
        more_listeners = [(443, 8001, 'HTTP')]
        self.conn.create_load_balancer_listeners(self.name, more_listeners)
        balancers = self.conn.get_all_load_balancers()
        self.assertEqual([lb.name for lb in balancers], [self.name])
        self.assertEqual(
            sorted(l.get_tuple() for l in balancers[0].listeners),
            sorted(self.listeners + more_listeners)
            )

    def test_delete_load_balancer_listeners(self):
        mod_listeners = [(80, 8000, 'HTTP'), (443, 8001, 'HTTP')]
        mod_name = self.name + "-mod"
        self.mod_balancer = self.conn.create_load_balancer(mod_name,\
            self.availability_zones, mod_listeners)

        mod_balancers = self.conn.get_all_load_balancers(load_balancer_names=[mod_name])
        self.assertEqual([lb.name for lb in mod_balancers], [mod_name])
        self.assertEqual(
            sorted([l.get_tuple() for l in mod_balancers[0].listeners]),
            sorted(mod_listeners))

        self.conn.delete_load_balancer_listeners(self.mod_balancer.name, [443])
        mod_balancers = self.conn.get_all_load_balancers(load_balancer_names=[mod_name])
        self.assertEqual([lb.name for lb in mod_balancers], [mod_name])
        self.assertEqual([l.get_tuple() for l in mod_balancers[0].listeners],
                         mod_listeners[:1])
        self.mod_balancer.delete()

    def test_create_load_balancer_listeners_with_policies(self):
        more_listeners = [(443, 8001, 'HTTP')]
        self.conn.create_load_balancer_listeners(self.name, more_listeners)

        lb_policy_name = 'lb-policy'
        self.conn.create_lb_cookie_stickiness_policy(1000, self.name, lb_policy_name)
        self.conn.set_lb_policies_of_listener(self.name, self.listeners[0][0], lb_policy_name)

        app_policy_name = 'app-policy'
        self.conn.create_app_cookie_stickiness_policy('appcookie', self.name, app_policy_name)
        self.conn.set_lb_policies_of_listener(self.name, more_listeners[0][0], app_policy_name)

        balancers = self.conn.get_all_load_balancers(load_balancer_names=[self.name])
        self.assertEqual([lb.name for lb in balancers], [self.name])
        self.assertEqual(
            sorted(l.get_tuple() for l in balancers[0].listeners),
            sorted(self.listeners + more_listeners)
            )
        # Policy names should be checked here once they are supported
        # in the Listener object.

    def test_create_load_balancer_complex_listeners(self):
        complex_listeners = [
            (8080, 80, 'HTTP', 'HTTP'),
            (2525, 25, 'TCP', 'TCP'),
        ]

        self.conn.create_load_balancer_listeners(
            self.name,
            complex_listeners=complex_listeners
        )

        balancers = self.conn.get_all_load_balancers(
            load_balancer_names=[self.name]
        )
        self.assertEqual([lb.name for lb in balancers], [self.name])
        self.assertEqual(
            sorted(l.get_complex_tuple() for l in balancers[0].listeners),
            # We need an extra 'HTTP' here over what ``self.listeners`` uses.
            sorted([(80, 8000, 'HTTP', 'HTTP')] + complex_listeners)
        )

if __name__ == '__main__':
    unittest.main()
