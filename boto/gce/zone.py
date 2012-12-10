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


class Zone():
    """
    Represents a GCE Zone.
    """
    def __init__(self, zone):
        self.status = zone['status']
        self.kind = zone['kind']
        self.creation_timestamp = zone['creationTimestamp']
        self.id = zone['id']
        self.self_link = zone['selfLink']
        self.name = zone['name']

    def __repr__(self):
        return 'Zone:%s' % self.id
