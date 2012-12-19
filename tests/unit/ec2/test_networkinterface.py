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

from tests.unit import unittest


from boto.ec2.networkinterface import NetworkInterfaceCollection
from boto.ec2.networkinterface import NetworkInterfaceSpecification
from boto.ec2.networkinterface import PrivateIPAddress


class TestNetworkInterfaceCollection(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.private_ip_address1 = PrivateIPAddress(
            private_ip_address='10.0.0.10', primary=False)
        self.private_ip_address2 = PrivateIPAddress(
            private_ip_address='10.0.0.11', primary=False)
        self.network_interfaces_spec1 = NetworkInterfaceSpecification(
            device_index=1, subnet_id='subnet_id',
            description='description1',
            private_ip_address='10.0.0.54', delete_on_termination=False,
            private_ip_addresses=[self.private_ip_address1,
                                  self.private_ip_address2])

        self.private_ip_address3 = PrivateIPAddress(
            private_ip_address='10.0.1.10', primary=False)
        self.private_ip_address4 = PrivateIPAddress(
            private_ip_address='10.0.1.11', primary=False)
        self.network_interfaces_spec2 = NetworkInterfaceSpecification(
            device_index=2, subnet_id='subnet_id2',
            description='description2',
            groups=['group_id1', 'group_id2'],
            private_ip_address='10.0.1.54', delete_on_termination=False,
            private_ip_addresses=[self.private_ip_address3,
                                  self.private_ip_address4])

    def test_param_serialization(self):
        collection = NetworkInterfaceCollection(self.network_interfaces_spec1,
                                                self.network_interfaces_spec2)
        params = {}
        collection.build_list_params(params)
        self.assertDictEqual(params, {
            'NetworkInterface.1.DeviceIndex': '1',
            'NetworkInterface.1.DeleteOnTermination': 'false',
            'NetworkInterface.1.Description': 'description1',
            'NetworkInterface.1.PrivateIpAddress': '10.0.0.54',
            'NetworkInterface.1.SubnetId': 'subnet_id',
            'NetworkInterface.1.PrivateIpAddresses.1.Primary': 'false',
            'NetworkInterface.1.PrivateIpAddresses.1.PrivateIpAddress':
                '10.0.0.10',
            'NetworkInterface.1.PrivateIpAddresses.2.Primary': 'false',
            'NetworkInterface.1.PrivateIpAddresses.2.PrivateIpAddress':
                '10.0.0.11',
            'NetworkInterface.2.DeviceIndex': '2',
            'NetworkInterface.2.Description': 'description2',
            'NetworkInterface.2.DeleteOnTermination': 'false',
            'NetworkInterface.2.PrivateIpAddress': '10.0.1.54',
            'NetworkInterface.2.SubnetId': 'subnet_id2',
            'NetworkInterface.2.SecurityGroupId.1': 'group_id1',
            'NetworkInterface.2.SecurityGroupId.2': 'group_id2',
            'NetworkInterface.2.PrivateIpAddresses.1.Primary': 'false',
            'NetworkInterface.2.PrivateIpAddresses.1.PrivateIpAddress':
                '10.0.1.10',
            'NetworkInterface.2.PrivateIpAddresses.2.Primary': 'false',
            'NetworkInterface.2.PrivateIpAddresses.2.PrivateIpAddress':
                '10.0.1.11',
        })

    def test_add_prefix_to_serialization(self):
        return
        collection = NetworkInterfaceCollection(self.network_interfaces_spec1,
                                                self.network_interfaces_spec2)
        params = {}
        collection.build_list_params(params, prefix='LaunchSpecification.')
        # We already tested the actual serialization previously, so
        # we're just checking a few keys to make sure we get the proper
        # prefix.
        self.assertDictEqual(params, {
            'LaunchSpecification.NetworkInterface.1.DeviceIndex': '1',
            'LaunchSpecification.NetworkInterface.1.DeleteOnTermination':
                'false',
            'LaunchSpecification.NetworkInterface.1.Description':
                'description1',
            'LaunchSpecification.NetworkInterface.1.PrivateIpAddress':
                '10.0.0.54',
            'LaunchSpecification.NetworkInterface.1.SubnetId': 'subnet_id',
            'LaunchSpecification.NetworkInterface.1.PrivateIpAddresses.1.Primary':
                'false',
            'LaunchSpecification.NetworkInterface.1.PrivateIpAddresses.1.PrivateIpAddress':
                '10.0.0.10',
            'LaunchSpecification.NetworkInterface.1.PrivateIpAddresses.2.Primary': 'false',
            'LaunchSpecification.NetworkInterface.1.PrivateIpAddresses.2.PrivateIpAddress':
                '10.0.0.11',
            'LaunchSpecification.NetworkInterface.2.DeviceIndex': '2',
            'LaunchSpecification.NetworkInterface.2.Description':
                'description2',
            'LaunchSpecification.NetworkInterface.2.DeleteOnTermination':
                'false',
            'LaunchSpecification.NetworkInterface.2.PrivateIpAddress':
                '10.0.1.54',
            'LaunchSpecification.NetworkInterface.2.SubnetId': 'subnet_id2',
            'LaunchSpecification.NetworkInterface.2.SecurityGroupId.1':
                'group_id1',
            'LaunchSpecification.NetworkInterface.2.SecurityGroupId.2':
                'group_id2',
            'LaunchSpecification.NetworkInterface.2.PrivateIpAddresses.1.Primary':
                'false',
            'LaunchSpecification.NetworkInterface.2.PrivateIpAddresses.1.PrivateIpAddress':
                '10.0.1.10',
            'LaunchSpecification.NetworkInterface.2.PrivateIpAddresses.2.Primary':
                'false',
            'LaunchSpecification.NetworkInterface.2.PrivateIpAddresses.2.PrivateIpAddress':
                '10.0.1.11',
        })


if __name__ == '__main__':
    unittest.main()
