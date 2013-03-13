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

import boto
import httplib2
import os

from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run

from boto.gce.firewall import Firewall
from boto.gce.image import Image
from boto.gce.instance import Instance
from boto.gce.kernel import Kernel
from boto.gce.network import Network
from boto.gce.machine_type import MachineType
from boto.gce.ramdisk import Ramdisk
from boto.gce.zone import Zone
from boto.gce.zone_operation import ZoneOperation


# CLIENT_SECRETS, name of a file containing the OAuth 2.0 information for this
# application, including client_id and client_secret, which are found
# on the API Access tab on the Google APIs
# Console <http://code.google.com/apis/console>

# Helpful message to display if the CLIENT_SECRETS file is missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   {0}

with information from the APIs Console <https://code.google.com/apis/console>.
"""

OAUTH2_SCOPE = 'https://www.googleapis.com/auth/compute'
GOOGLE_PROJECT = 'google'


def get_oauth2_credentials():
    """
    Return oauth2 credentials, running the configured flow if necessary.
    """
    try:
      client_secrets = _get_config('Credentials', 'gce_client_secrets_file')
      credentials_file = _get_config('Credentials', 'gce_credentials_file')
    except ConfigError:
      raise RuntimeError('OAuth2 credentials missing.')

    storage = Storage(credentials_file)
    credentials = storage.get()
    if credentials is None or credentials.invalid:
        message = MISSING_CLIENT_SECRETS_MESSAGE.format(client_secrets)
        flow = flow_from_clientsecrets(client_secrets,
                                       message=message,
                                       scope=OAUTH2_SCOPE)
        return run(flow, storage)
    return credentials


def _get_config(section, key):
    """
    Check boto.config and the environment for the specified key.
    """
    value = boto.config.get(section, key, None)
    if value is not None:
        return value
    return os.environ[key.upper()]


class GCEConnection(object):

    APIVersion = 'v1beta14'

    def __init__(self, gce_project=None, credentials=None):
        """
        Init method to create a new connection to Google Compute Engine.

        :type gce_project: string
        :param gce_project: The GCE Project name to use.

        :type credentials: apiclient.Credentials
        :param credentials: A valid OAuth2 credentials instance.
        """
        if gce_project is None:
            gce_project = _get_config('Boto', 'gce_project')
        if credentials is None:
            credentials = get_oauth2_credentials()

        self.gce_project = gce_project
        self.credentials = credentials

        self.http = self.credentials.authorize(httplib2.Http())
        self.service = build('compute', self.APIVersion, http=self.http)

    # Image methods

    def get_all_images(self, global_images=True):
        """
        Retrieve all the Google Compute Engine images available to your
        project.
        """
        if global_images:
            project = GOOGLE_PROJECT
        else:
            project = self.gce_project

        list_gce_images = self.service.images().list(
            project=project).execute(http=self.http)

        return [Image(i) for i in list_gce_images.get('items', [])]

    def get_all_kernels(self, global_kernels=True):
        """
        Retrieve all the Google Compute Engine kernels available to your project.
        """
        if global_kernels:
            project = GOOGLE_PROJECT
        else:
            project = self.gce_project

        list_gce_kernels = self.service.kernels().list(
            project=project).execute(http=self.http)
        return [Kernel(k) for k in list_gce_kernels.get('items', [])]

    def get_all_ramdisks(self, zones=None):
        """
        Retrieve all the Google Compute Engine disks available to your project.
        """
        if zones is None:
            zones = [zone.name for zone in self.get_all_zones()]

        ramdisks = []
        for zone in zones:
            request = self.service.disks().list(
                    project=self.gce_project, zone=zone)
            response = request.execute(http=self.http)
            ramdisks.extend(Ramdisk(rd) for rd in response.get('items', []))
        return ramdisks

    def get_image(self, name):
        """
        Shortcut method to retrieve a specific image.

        :type name: string
        :param name: The name of the Image to retrieve.

        :rtype: :class:`boto.gce.image.Image`
        :return: The Google Compute Engine Image specified, or None if the image
        is not found
        """
        # TODO: Fix this to work with both global and per-project images.
        request = self.service.images().get(project=GOOGLE_PROJECT,
                                            image=name)
        gce_image = request.execute(http=self.http)
        return Image(gce_image)

    # Instance methods

    def get_all_instances(self, zones=None):
        """
        Retrieve all the Google Compute Engine instances available to your
        project.
        """
        if zones is None:
            zones = [zone.name for zone in self.get_all_zones()]

        instances = []
        for zone in zones:
            request = self.service.instances().list(
                    project=self.gce_project, zone=zone)
            response = request.execute(http=self.http)
            instances.extend(Instance(i) for i in response.get('items', []))
        return instances

    def run_instance(self, name, machine_type, zone, image,
                     disk_types=None):
        """
        Insert a Google Compute Engine instance into your cluster.

        :type name: string
        :param name: The name of the instance to insert.

        :rtype: :class:`boto.gce.operation.Operation`
        :return: A Google Compute Engine operation.
        """
        if disk_types is None:
            disk_types = ['EPHEMERAL']
        network = self.get_network('default').self_link

        body = {
            'name': name,
            'image': image,
            'machineType': machine_type,
            'networkInterfaces': [{
                'network': network
             }],
            'disks': [{'type': t} for t in disk_types]
        }

        request = self.service.instances().insert(project=self.gce_project,
                                                  zone=zone,
                                                  body=body)
        operation = request.execute(http=self.http)
        return ZoneOperation(operation)

    def terminate_instance(self, name, zone):
        """
        Terminate a specific Google Compute Engine instance.

        :type name: string
        :param name: The name of the instance to terminate.

        :type name: string
        :param zone: The zone in which the instance resides.

        :rtype: :class:`boto.gce.operation.Operation`
        :return: A Google Compute Engine operation.
        """
        request = self.service.instances().delete(zone=zone,
                                                  project=self.gce_project,
                                                  instance=name)
        operation = request.execute(http=self.http)
        return ZoneOperation(operation)

    def get_instance(self, name, zone):
        """
        Get an instance from Google Compute Engine.

        :type name: string
        :param name: The name of the instance to get.

        :type zone: string
        :param zone: The name of the zone in which the instance resides.

        :rtype: :class:`boto.gce.resource.Resource`
        :return: A Resource object representing the instance information.
        """
        request = self.service.instances().get(
                project=self.gce_project, instance=name, zone=zone)
        instance = request.execute(http=self.http)
        return Instance(instance)

    # Zone methods

    def get_all_zones(self):
        """
        Retrieve all the Google Compute Engine zones available to your project.
        """
        list_gce_zones = self.service.zones().list(
            project=self.gce_project).execute(http=self.http)
        return [Zone(z) for z in list_gce_zones.get('items', [])]

    def get_zone(self, name):
        """
        Shortcut method to retrieve a specific zone.

        :type name: string
        :param name: The name of the Zone to retrieve.

        :rtype: :class:`boto.gce.zone.Zone`
        :return: The Google Compute Engine Zone specified, or None if the zone
        is not found
        """
        gce_zone = self.service.zones().get(project=self.gce_project,
                                            zone=name).execute(
                                                http=self.http)

        return Zone(gce_zone)

    # Network methods

    def get_all_networks(self):
        """
        Retrieve all the Google Compute Engine networks available to your
        project.
        """
        list_gce_networks = self.service.networks().list(
            project=self.gce_project).execute(http=self.http)
        return [Network(n) for n in list_gce_networks.get('items', [])]

    def get_network(self, name):
        """
        Shortcut method to retrieve a specific network.

        :type name: string
        :param name: The name of the Network to retrieve.

        :rtype: :class:`boto.gce.network.Network`
        :return: The Google Compute Engine Network specified, or None if the
        network is not found
        """
        gce_network = self.service.networks().get(project=self.gce_project,
                                                  network=name).execute(
                                                      http=self.http)
        return Network(gce_network)

    # Firewall methods

    def get_all_firewalls(self):
        """
        Retrieve all the Google Compute Engine firewalls available to your
        project.
        """
        list_gce_firewalls = self.service.firewalls().list(
            project=self.gce_project).execute(http=self.http)
        return [Firewall(fw) for fw in list_gce_firewalls.get('items', [])]

    def get_firewall(self, name):
        """
        Shortcut method to retrieve a specific firewall.

        :type name: string
        :param name: The name of the Firewall to retrieve.

        :rtype: :class:`boto.gce.firewall.Firewall`
        :return: The Google Compute Engine Firewall specified, or None if the
        firewall is not found
        """
        gce_firewall = self.service.firewalls().get(
            project=self.gce_project, firewall=name).execute(
                http=self.http)

        return Firewall(gce_firewall)

    # MachineType methods

    def get_all_machine_types(self):
        """
        Return a list of all known machine types.

        :rtype: :class:`boto.gce.machine_type.MachineType`
        :return: The GCE resource for all know machine types.
        """
        request = self.service.machineTypes().list(project=self.gce_project)
        machine_list = request.execute(http=self.http)
        return [MachineType(m) for m in machine_list.get('items', [])]
