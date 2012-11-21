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


class Ramdisk():
    """
    Represents a GCE Ramdisk.
    """
    def __init__(self, ramdisk):
        self.id = ramdisk['id']
        self.name = ramdisk['name']
        self.kind = ramdisk['kind']
        self.description = ramdisk['description']
        self.creation_timestamp = ramdisk['creationTimestamp']
        self.self_link = ramdisk['selfLink']

    def __repr__(self):
        return 'Ramdisk:%s' % self.id
