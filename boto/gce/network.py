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


class Network():
    """
    Represents a GCE Network.
    """
    def __init__(self, network):
        self.id = network['id']
        self.kind = network['kind']
        self.description = network['description']
        self.ip_range = network['IPv4Range']
        self.self_link = network['selfLink']
        self.name = network['name']
        self.creation_timestamp = network['creationTimestamp']
        self.gateway_ip = network['gatewayIPv4']

    def __repr__(self):
        return 'Network:%s' % self.id
