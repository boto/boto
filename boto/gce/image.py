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


class Image(object):
    """
    Represents a GCE Image.
    """
    def __init__(self, image):
        self.id = image['id']
        self.name = image['name']
        self.kind = image['kind']
        self.self_link = image['selfLink']
        self.creation_timestamp = image['creationTimestamp']
        self.description = image['description']
        self.raw_disk = image['rawDisk']
        self.preferred_kernel = image['preferredKernel']
        self.source_type = image['sourceType']

    def __repr__(self):
        return 'Image:%s' % self.id
