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

    def tearDown(self):
        """ Deletes all load balancers after every test. """
        for lb in ELBConnection().get_all_load_balancers():
            lb.delete()

    def test_build_list_params(self):
        c = ELBConnection()
        params = {}
        c.build_list_params(
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
        c = ELBConnection()
        name = 'elb-boto-unit-test'
        availability_zones = ['us-east-1a']
        listeners = [(80, 8000, 'HTTP')]
        balancer = c.create_load_balancer(name, availability_zones, listeners)
        self.assertEqual(balancer.name, name)
        self.assertEqual(balancer.availability_zones, availability_zones)
        self.assertEqual(balancer.listeners, listeners)

        balancers = c.get_all_load_balancers()
        self.assertEqual([lb.name for lb in balancers], [name])

    def test_create_load_balancer_listeners(self):
        c = ELBConnection()
        name = 'elb-boto-unit-test'
        availability_zones = ['us-east-1a']
        listeners = [(80, 8000, 'HTTP')]
        balancer = c.create_load_balancer(name, availability_zones, listeners)

        more_listeners = [(443, 8001, 'HTTP')]
        c.create_load_balancer_listeners(name, more_listeners)
        balancers = c.get_all_load_balancers()
        self.assertEqual([lb.name for lb in balancers], [name])
        self.assertEqual(
            sorted(l.get_tuple() for l in balancers[0].listeners),
            sorted(listeners + more_listeners)
            )

    def test_delete_load_balancer_listeners(self):
        c = ELBConnection()
        name = 'elb-boto-unit-test'
        availability_zones = ['us-east-1a']
        listeners = [(80, 8000, 'HTTP'), (443, 8001, 'HTTP')]
        balancer = c.create_load_balancer(name, availability_zones, listeners)

        balancers = c.get_all_load_balancers()
        self.assertEqual([lb.name for lb in balancers], [name])
        self.assertEqual(
            sorted([l.get_tuple() for l in balancers[0].listeners]),
            sorted(listeners))

        c.delete_load_balancer_listeners(name, [443])
        balancers = c.get_all_load_balancers()
        self.assertEqual([lb.name for lb in balancers], [name])
        self.assertEqual([l.get_tuple() for l in balancers[0].listeners],
                         listeners[:1])

    def test_create_load_balancer_listeners_with_policies(self):
        c = ELBConnection()
        name = 'elb-boto-unit-test-policy'
        availability_zones = ['us-east-1a']
        listeners = [(80, 8000, 'HTTP')]
        balancer = c.create_load_balancer(name, availability_zones, listeners)

        more_listeners = [(443, 8001, 'HTTP')]
        c.create_load_balancer_listeners(name, more_listeners)

        lb_policy_name = 'lb-policy'
        c.create_lb_cookie_stickiness_policy(1000, name, lb_policy_name)
        c.set_lb_policies_of_listener(name, listeners[0][0], lb_policy_name)

        app_policy_name = 'app-policy'
        c.create_app_cookie_stickiness_policy('appcookie', name, app_policy_name)
        c.set_lb_policies_of_listener(name, more_listeners[0][0], app_policy_name)

        balancers = c.get_all_load_balancers()
        self.assertEqual([lb.name for lb in balancers], [name])
        self.assertEqual(
            sorted(l.get_tuple() for l in balancers[0].listeners),
            sorted(listeners + more_listeners)
            )
        # Policy names should be checked here once they are supported
        # in the Listener object.

if __name__ == '__main__':
    unittest.main()
