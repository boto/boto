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

__author__ = 'ziyadm@google.com (Ziyad Mir)'

import httplib2
import os
import boto

from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run

from boto.gce.image import Image
from boto.gce.kernel import Kernel
from boto.gce.ramdisk import Ramdisk
from boto.gce.instance import Instance
from boto.gce.instance_attribute import InstanceAttribute
from boto.gce.zone import Zone
from boto.gce.network import Network
from boto.gce.firewall import Firewall

# CLIENT_SECRETS, name of a file containing the OAuth 2.0 information for this
# application, including client_id and client_secret, which are found
# on the API Access tab on the Google APIs
# Console <http://code.google.com/apis/console>
CLIENT_SECRETS = 'client_secrets.json'

# Helpful message to display in the browser if the CLIENT_SECRETS file
# is missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the APIs Console <https://code.google.com/apis/console>.

""" % os.path.join(os.path.dirname(__file__), CLIENT_SECRETS)

# Set up a Flow object to be used if we need to authenticate.
FLOW = flow_from_clientsecrets(CLIENT_SECRETS,
                               scope='https://www.googleapis.com/auth/compute',
                               message=MISSING_CLIENT_SECRETS_MESSAGE)

API_VERSION = 'v1beta13'


class GCEConnection():
    def __init__(self, gce_project):
        """
        Init method to create a new connection to Google Compute Engine.
        """
        self.gce_project = gce_project
        self.google_project = 'google'
        self.storage = Storage('creds.dat')
        self.credentials = self.storage.get()
        self.default_network = "https://www.googleapis.com/compute/{0}/projects/google/networks/default".format(API_VERSION)

        if self.credentials is None or self.credentials.invalid:
            self.credentials = run(FLOW, self.storage)

        self.http = self.credentials.authorize(httplib2.Http())
        self.service = build("compute", API_VERSION, http=self.http)

    # Image methods

    def get_all_images(self):
        """
        Retrieve all the Google Compute Engine images available to your project.
        """
        list_gce_images = self.service.images().list(
            project=self.google_project).execute(http=self.http)

        list_images = []
        for image in list_gce_images['items']:
            list_images.append(Image(image))

        return list_images

    def get_all_kernels(self):
        """
        Retrieve all the Google Compute Engine kernels available to your project.
        """
        list_gce_kernels = self.service.kernels().list(
            project=self.google_project).execute(http=self.http)

        list_kernels = []
        for kernel in list_gce_kernels['items']:
            list_kernels.append(Kernel(kernel))

        return list_kernels

    def get_all_ramdisks(self):
        """
        Retrieve all the Google Compute Engine disks available to your project.
        """
        list_gce_ramdisks = self.service.disks().list(
            project=self.gce_project).execute(http=self.http)

        list_ramdisks = []
        for ramdisk in list_gce_ramdisks['items']:
            list_ramdisks.append(Ramdisk(ramdisk))

        return list_ramdisks

    def get_image(self, image_name):
        """
        Shortcut method to retrieve a specific image.

        :type image_name: string
        :param image_name: The name of the Image to retrieve.

        :rtype: :class:`boto.gce.image.Image`
        :return: The Google Compute Engine Image specified, or None if the image
        is not found
        """
        gce_image = self.service.images().get(project=self.google_project,
                                              image=image_name).execute(
                                                  http=self.http)
        return Image(gce_image)

    # Instance methods

    def get_all_instances(self):
        """
        Retrieve all the Google Compute Engine instances available to your
        project.
        """
        list_gce_instances = self.service.instances().list(
            project=self.gce_project).execute(http=self.http)

        list_instances = []
        for instance in list_gce_instances['items']:
            list_instances.append(Instance(instance))

        return list_instances

    def run_instance(self, name=None, image_name=None, machine_type=None,
                     zone_name=None):
        """
        Insert a Google Compute Engine instance into your cluster.

        :type name: string
        :param name: The name of the instance to insert.

        :rtype: :class:`boto.gce.operation.Operation`
        :return: A Google Compute Engine operation.
        """
        body = {
            'name': name,
            'image': image_name,
            'zone': zone_name,
            'machineType': machine_type,
            'networkInterfaces': [{
                'network': self.default_network
             }]
        }

        gce_instance = self.service.instances().insert(project=self.gce_project,
                                                       body=body).execute(
                                                           http=self.http)
        return Instance(gce_instance)

    def terminate_instance(self, name=None):
        """
        Terminate a specific Google Compute Engine instance.

        :type name: string
        :param name: The name of the instance to terminate.

        :rtype: :class:`boto.gce.operation.Operation`
        :return: A Google Compute Engine operation.
        """
        gce_instance = self.service.instances().delete(project=self.gce_project,
                                                       instance=name).execute(
                                                           http=self.http)

        return Instance(gce_instance)

    def get_instance_attribute(self, name=None, attribute=None):
        """
        Get an attribute from a Google Compute Engine instance.

        :type name: string
        :param name: The name of the instance from which to get an attribute.

        :type attribute: string
        :param attribute: The attribute you need information about
            Valid choices are:

            * status
            * kind
            * machine_type
            * name
            * zone
            * image
            * disks
            * self_link
            * network_interfaces
            * creation_timestamp

        :rtype: :class:`boto.gce.image.InstanceAttribute`
        :return: An InstanceAttribute object representing the value of the
        attribute requested.
        """
        attribute_map = {
            "status": "status",
            "kind": "kind",
            "machine_type": "machineType",
            "name": "name",
            "zone": "zone",
            "image": "image",
            "disks": "disks",
            "self_link": "selfLink",
            "network_interfaces": "networkInterfaces",
            "creation_timestamp": "creationTimestamp"
        }

        gce_attribute = self.service.instances().get(
            project=self.gce_project, instance=name).execute(
                http=self.http)[attribute_map[attribute]]

        return InstanceAttribute(gce_attribute)

    # Zone methods

    def get_all_zones(self):
        """
        Retrieve all the Google Compute Engine zones available to your project.
        """
        list_gce_zones = self.service.zones().list(
            project=self.google_project).execute(http=self.http)

        list_zones = []
        for zone in list_gce_zones['items']:
            list_zones.append(Zone(zone))

        return list_zones

    def get_zone(self, zone_name):
        """
        Shortcut method to retrieve a specific zone.

        :type zone_name: string
        :param zone_name: The name of the Zone to retrieve.

        :rtype: :class:`boto.gce.zone.Zone`
        :return: The Google Compute Engine Zone specified, or None if the zone
        is not found
        """
        gce_zone = self.service.zones().get(project=self.google_project,
                                            zone=zone_name).execute(
                                                http=self.http)

        return Zone(gce_zone)

    # Network methods

    def get_all_networks(self):
        """
        Retrieve all the Google Compute Engine networks available to your
        project.
        """
        list_gce_networks = self.service.networks().list(
            project=self.google_project).execute(http=self.http)

        list_networks = []
        for network in list_gce_networks['items']:
            list_networks.append(Network(network))

        return list_networks

    def get_network(self, network_name):
        """
        Shortcut method to retrieve a specific network.

        :type network_name: string
        :param network_name: The name of the Network to retrieve.

        :rtype: :class:`boto.gce.network.Network`
        :return: The Google Compute Engine Network specified, or None if the
        network is not found
        """
        gce_network = self.service.networks().get(project=self.google_project,
                                                  network=network_name).execute(
                                                      http=self.http)

        return Network(gce_network)

    # Firewall methods

    def get_all_firewalls(self):
        """
        Retrieve all the Google Compute Engine firewalls available to your
        project.
        """
        list_gce_firewalls = self.service.firewalls().list(
            project=self.google_project).execute(http=self.http)

        list_firewalls = []
        for firewall in list_gce_firewalls['items']:
            list_firewalls.append(Firewall(firewall))

        return list_firewalls

    def get_firewall(self, firewall_name):
        """
        Shortcut method to retrieve a specific firewall.

        :type firewall_name: string
        :param firewall_name: The name of the Firewall to retrieve.

        :rtype: :class:`boto.gce.firewall.Firewall`
        :return: The Google Compute Engine Firewall specified, or None if the
        firewall is not found
        """
        gce_firewall = self.service.firewalls().get(project=self.google_project,
                                                    firewall=firewall_name).execute(
                                                        http=self.http)

        return Firewall(gce_firewall)
