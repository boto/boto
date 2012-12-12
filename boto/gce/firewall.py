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


class Firewall():
    """
    Represents a GCE Firewall.
    """
    def __init__(self, firewall):
        self.id = firewall['id']
        self.kind = firewall['kind']
        self.description = firewall['description']
        self.source_ranges = firewall['sourceRanges']
        self.network = firewall['network']
        self.allowed = firewall['allowed']
        self.creation_timestamp = firewall['creationTimestamp']
        self.self_link = firewall['selfLink']
        self.name = firewall['name']

    def __repr__(self):
        return 'Firewall:%s' % self.id
