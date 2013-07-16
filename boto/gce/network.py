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

from boto.utils import pythonize_name

from boto.gce.resource import Resource, register_kind


def _pythonize_network(name):
    """
    A pythonize_name() that special cases 'IPv4'.
    """
    return pythonize_name(name.replace('IPv4', 'Ip'))


@register_kind
class Network(Resource):
    """
    Represents a GCE Network.
    """
    def __init__(self, items, transform=_pythonize_network):
        super(Network, self).__init__(items, transform)
