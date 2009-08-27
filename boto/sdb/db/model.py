# Copyright (c) 2006,2007,2008 Mitch Garnaat http://garnaat.org/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from boto.sdb.db.manager import get_manager
from boto.sdb.db.property import *
from boto.sdb.db.query import Query
import boto

class ModelMeta(type):
    "Metaclass for all Models"

    def __init__(cls, name, bases, dict):
        super(ModelMeta, cls).__init__(name, bases, dict)
        # Make sure this is a subclass of Model - mainly copied from django ModelBase (thanks!)
        cls.__sub_classes__ = []
        try:
            if filter(lambda b: issubclass(b, Model), bases):
                for base in bases:
                    base.__sub_classes__.append(cls)
                # look for all of the Properties and set their names
                for key in dict.keys():
                    if isinstance(dict[key], Property):
                        property = dict[key]
                        property.__property_config__(cls, key)
                prop_names = []
                props = cls.properties()
                for prop in props:
                    if not prop.__class__.__name__.startswith('_'):
                        prop_names.append(prop.name)
                setattr(cls, '_prop_names', prop_names)
        except NameError:
            # 'Model' isn't defined yet, meaning we're looking at our own
            # Model class, defined below.
            pass
        
class Model(object):
    __metaclass__ = ModelMeta

    @classmethod
    def get_lineage(cls):
        l = [c.__name__ for c in cls.mro()]
        l.reverse()
        return '.'.join(l)

    @classmethod
    def get_by_id(cls, manager, id):
        return manager.load_object(id, cls)

    @classmethod
    def find(cls, manager, **params):
        q = Query(cls, manager)
        for key, value in params.items():
            q.filter('%s =' % key, value)
        return q

    @classmethod
    def all(cls, manager, max_items=None):
        return cls.find(manager, max_items=max_items)

    @classmethod
    def properties(cls, hidden=True):
        properties = []
        while cls:
            for key in cls.__dict__.keys():
                prop = cls.__dict__[key]
                if isinstance(prop, Property):
                    if hidden or not prop.__class__.__name__.startswith('_'):
                        properties.append(prop)
            if len(cls.__bases__) > 0:
                cls = cls.__bases__[0]
            else:
                cls = None
        return properties

    @classmethod
    def find_property(cls, prop_name):
        property = None
        while cls:
            for key in cls.__dict__.keys():
                prop = cls.__dict__[key]
                if isinstance(prop, Property):
                    if not prop.__class__.__name__.startswith('_') and prop_name == prop.name:
                        property = prop
            if len(cls.__bases__) > 0:
                cls = cls.__bases__[0]
            else:
                cls = None
        return property

    def __init__(self, id=None, **kwargs):
        self.id = id
        self.manager = None
        for prop in self.properties(hidden=False):
            setattr(self, prop.name, prop.default_value())
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __repr__(self):
        return '%s<%s>' % (self.__class__.__name__, self.id)

    def __str__(self):
        return str(self.id)
    
    def __eq__(self, other):
        return other and isinstance(other, Model) and self.id == other.id

    def _get_raw_item(self, manager=None):
        manager = manager or self.manager
        if manager:
            return manager.get_raw_item(self)

    def put(self, manager=None):
        manager = manager or self.manager
        if manager:
            manager.save_object(self)

    save = put
        
    def delete(self, manager=None):
        manager = manager or self.manager
        if manager:
            manager.delete_object(self)

    def to_dict(self):
        props = {}
        for prop in self.properties(hidden=False):
            props[prop.name] = getattr(self, prop.name)
        obj = {'properties' : props,
               'id' : self.id}
        return {self.__class__.__name__ : obj}

class Expando(Model):

    def __setattr__(self, name, value):
        if name in self._prop_names:
            object.__setattr__(self, name, value)
        elif name.startswith('_'):
            object.__setattr__(self, name, value)
        elif name == 'id':
            object.__setattr__(self, name, value)
        else:
            self.manager.set_key_value(self, name, value)
            object.__setattr__(self, name, value)

    def __getattr__(self, name):
        if not name.startswith('_'):
            value = self.manager.get_key_value(self, name)
            if value:
                object.__setattr__(self, name, value)
                return value
        raise AttributeError

    
