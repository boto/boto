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
import unittest
import time

import boto
from boto.ec2.networkinterface import NetworkInterfaceCollection
from boto.ec2.networkinterface import NetworkInterfaceSpecification
from boto.ec2.networkinterface import PrivateIPAddress


class TestVPCConnection(unittest.TestCase):
    def setUp(self):
        self.api = boto.connect_vpc()
        vpc = self.api.create_vpc('10.0.0.0/16')
        self.addCleanup(self.api.delete_vpc, vpc.id)

        self.subnet = self.api.create_subnet(vpc.id, '10.0.0.0/24')
        self.addCleanup(self.api.delete_subnet, self.subnet.id)

    def terminate_instance(self, instance):
        instance.terminate()
        for i in xrange(300):
            instance.update()
            if instance.state == 'terminated':
                # Give it a litle more time to settle.
                time.sleep(10)
                return
            else:
                time.sleep(10)

    def test_multi_ip_create(self):
        interface = NetworkInterfaceSpecification(
            device_index=0, subnet_id=self.subnet.id,
            private_ip_address='10.0.0.21',
            description="This is a test interface using boto.",
            delete_on_termination=True, private_ip_addresses=[
                PrivateIPAddress(private_ip_address='10.0.0.22',
                                 primary=False),
                PrivateIPAddress(private_ip_address='10.0.0.23',
                                 primary=False),
                PrivateIPAddress(private_ip_address='10.0.0.24',
                                 primary=False)])
        interfaces = NetworkInterfaceCollection(interface)

        reservation = self.api.run_instances(image_id='ami-a0cd60c9', instance_type='m1.small',
                                             network_interfaces=interfaces)
        # Give it a few seconds to start up.
        time.sleep(10)
        instance = reservation.instances[0]
        self.addCleanup(self.terminate_instance, instance)
        retrieved = self.api.get_all_instances(instance_ids=[instance.id])
        self.assertEqual(len(retrieved), 1)
        retrieved_instances = retrieved[0].instances
        self.assertEqual(len(retrieved_instances), 1)
        retrieved_instance = retrieved_instances[0]

        self.assertEqual(len(retrieved_instance.interfaces), 1)
        interface = retrieved_instance.interfaces[0]
        
        private_ip_addresses = interface.private_ip_addresses
        self.assertEqual(len(private_ip_addresses), 4)
        self.assertEqual(private_ip_addresses[0].private_ip_address,
                         '10.0.0.21')
        self.assertEqual(private_ip_addresses[0].primary, True)
        self.assertEqual(private_ip_addresses[1].private_ip_address,
                         '10.0.0.22')
        self.assertEqual(private_ip_addresses[2].private_ip_address,
                         '10.0.0.23')
        self.assertEqual(private_ip_addresses[3].private_ip_address,
                         '10.0.0.24')


if __name__ == '__main__':
    unittest.main()
