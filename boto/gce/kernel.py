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


class Kernel():
    """
    Represents a GCE Kernel.
    """
    def __init__(self, kernel):
        self.id = kernel['id']
        self.name = kernel['name']
        self.kind = kernel['kind']
        self.description = kernel['description']
        self.creation_timestamp = kernel['creationTimestamp']
        self.self_link = kernel['selfLink']

    def __repr__(self):
        return 'Kernel:%s' % self.id
