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


class Instance():
    """
    Represents a GCE Instance.
    """
    def __init__(self, instance):
        self.id = instance['id']
        self.status = instance['status']
        self.kind = instance['kind']
        self.name = instance['name']
        self.self_link = instance['selfLink']
        self.image = instance['image']
        self.machine_type = instance['machineType']

    def __repr__(self):
        return 'Instance:%s' % self.id
