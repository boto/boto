#
# Copyright (C) 2013 Google Inc.
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


_KIND_MAP = {}
_DEFAULT_PREFIX = 'compute#'


def register_kind(kind=None):
    """
    Class decorator for registering a resource subclass to handle a kind.
    """
    def decorate(klass, kind=kind):
        if kind is None:
            # GCE kind's are camelCase by default,
            # class names are usually TitleCase.
            kind = klass.__name__[0].lower() + klass.__name__[1:]
        if '#' not in kind:
            kind = _DEFAULT_PREFIX + kind

        _KIND_MAP[kind] = klass
        return klass

    if isinstance(kind, type):
        return decorate(kind, None)
    return decorate


class Resource(object):
    """
    Generic Python representation of a Google REST API JSON resource.
    """

    @staticmethod
    def from_dict(values):
        """
        Lookup the registered class by 'kind' to instantiate a resource.
        """
        cls = _KIND_MAP.get(values.get('kind'), Resource)
        return cls(values)

    def __init__(self, items, transform=pythonize_name):
        """
        Initialize a resource from a given JSON resource dictionary.
        """
        for key, value in _iteritems(items):
            attr = transform(key)
            if isinstance(value, dict):
                # Recursively turn dictionaries into into resources.
                value = self.from_dict(value)
            elif _is_resource_list(value):
                value = [self.from_dict(v) for v in value]
            setattr(self, attr, value)

    def __repr__(self):
        try:
            return '%s:%s' % (self.kind[self.kind.rfind('#')].title(), self.id)
        except AttributeError:
            return 'Resource(%s)' % vars(self)

    def __eq__(self, other):
      if type(other) is not type(self):
        return NotImplemented
      return vars(self) == vars(other)

    def __ne__(self, other):
      result = self.__eq__(other)
      if result is NotImplemented:
        return result
      return not result


def _iteritems(possible_dict):
    """
    Return an iterator over dictionary items.
    """
    try:
        iteritems = possible_dict.iteritems
    except AttributeError:
        return possible_dict
    else:
        return iteritems()


def _is_resource_list(values):
    """
    Return true if 'values' is a list of dicts.
    """
    return isinstance(values, list) and values and isinstance(values[0], dict)
