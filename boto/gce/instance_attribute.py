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


class InstanceAttribute(object):
    """
    Represents the value of an attribute from a Google Compute Engine instance.
    Supported attributes are:
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
    """
    def __init__(self, instance_attribute_value):
        self.value = instance_attribute_value

    def __repr__(self):
        return 'InstanceAttribute:%s' % self.value
