#
# Copyright (C) 2012 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Unit tests for the GCEConnection class.
"""

import os
import time

from boto.gce.connection import GCEConnection
from tests.unit import unittest


class GCEConnectionTest(unittest.TestCase):
    gce = True

    def setUp(self):
      self.connection = GCEConnection(os.environ['GCE_PROJECT'])

    # List integration tests

    def test_get_all_images(self):
        list_images = self.connection.get_all_images()

        for image in list_images:
            assert image.name
            assert image.kind
            assert image.description
            assert image.raw_disk
            assert image.preferred_kernel
            assert image.source_type
            assert image.self_link
            assert image.creation_timestamp
            assert image.id

    def test_get_all_kernels(self):
        list_kernels = self.connection.get_all_kernels()

        for kernel in list_kernels:
            assert kernel.kind
            assert kernel.description
            assert kernel.self_link
            assert kernel.creation_timestamp
            assert kernel.id
            assert kernel.name

    def test_get_all_ramdisks(self):
        list_ramdisks = self.connection.get_all_ramdisks()

        for ramdisk in list_ramdisks:
            assert ramdisk.id

    def test_get_all_instances(self):
        list_instances = self.connection.get_all_instances()

        for instance in list_instances:
            assert instance.status
            assert instance.kind
            assert instance.name
            assert instance.image
            assert instance.machine_type
            assert instance.self_link
            assert instance.id

    def test_get_all_zones(self):
        list_zones = self.connection.get_all_zones()

        for zone in list_zones:
            assert zone.status
            assert zone.kind
            assert zone.name
            assert zone.self_link
            assert zone.id

    def test_get_all_networks(self):
        list_networks = self.connection.get_all_networks()

        for network in list_networks:
            assert network.kind
            assert network.name
            assert network.self_link
            assert network.description
            assert network.id
            assert network.gateway_ip
            assert network.creation_timestamp
            assert network.ip_range

    def test_get_all_firewalls(self):
        list_firewalls = self.connection.get_all_firewalls()

        for firewall in list_firewalls:
            assert firewall.kind
            assert firewall.name
            assert firewall.self_link
            assert firewall.description
            assert firewall.id
            assert firewall.network
            assert firewall.allowed
            assert firewall.creation_timestamp

    # Get integration tests

    def test_get_image(self):
        first_image = self.connection.get_all_images()[0]
        second_image = self.connection.get_image(first_image.name)
        self.assertEqual(first_image, second_image)

    def test_get_instance(self):
        first_instance = self.connection.get_all_instances()[0]
        second_instance = self.connection.get_instance(first_instance.name,
                                                       first_instance.zone)
        self.assertEqual(first_instance, second_instance)

    def test_get_zone(self):
        first_zone = self.connection.get_all_zones()[0]
        second_zone = self.connection.get_zone(first_zone.name)
        self.assertEqual(first_zone, second_zone)

    def test_get_network(self):
        first_network = self.connection.get_all_networks()[0]
        second_network = self.connection.get_network(first_network.name)
        self.assertEqual(first_network, second_network)

    def test_get_firewall(self):
        first_firewall = self.connection.get_all_firewalls()[0]
        second_firewall = self.connection.get_firewall(first_firewall.name)
        self.assertEqual(first_firewall, second_firewall)

    def test_get_all_machine_types(self):
      machine_types = self.connection.get_all_machine_types()
      for machine_type in machine_types:
          assert machine_type.id
          assert machine_type.name

    def test_instance_lifecycle(self):
        name = time.strftime('test-instance-%Y%m%d%H%M%S')
        machine_type = None
        for machine in self.connection.get_all_machine_types():
            if machine.deprecated is None:
                machine_type = machine.self_link
                break
        self.assertIsNotNone(machine_type)
        image_url = None
        for image in self.connection.get_all_images():
            if image.deprecated is None:
                image_url = image.self_link
                break
        self.assertIsNotNone(image_url)
        zone_name = None
        for zone in self.connection.get_all_zones():
            if zone.status == 'UP':
                zone_name = zone.name
                break
        self.assertIsNotNone(zone_name)
        self.connection.run_instance(name, machine_type, zone_name, image_url)
        # TODO: use the returned ZoneOperation to wait for the instance to be up.
        time.sleep(30)
        self.connection.terminate_instance(name, zone_name)
