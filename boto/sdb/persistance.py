# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
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

import boto
from datetime import datetime
from boto.exception import SDBPersistanceError
from boto.utils import find_class

ISO8601 = '%Y-%m-%dT%H:%M:%SZ'

class Persistance:

    __sdb = boto.connect_sdb()
    __domain = None
        
    @classmethod
    def set_domain(cls, domain_name):
        """
        Set the domain in which persisted objects will be stored
        """
        cls.__domain = cls.__sdb.lookup(domain_name)
        if not cls.__domain:
            cls.__domain = cls.__sdb.create_domain(domain_name)

    @classmethod
    def get_domain(cls):
        return cls.__domain

    @classmethod
    def delete(key):
        cls.__domain.delete_attributes(key)

def object_lister(cls, query_lister):
    for item in query_lister:
        class_name, item_name = SDBObject.split_name(item.name)
        yield cls(item_name)
                  
class SDBObject(object):

    @classmethod
    def join_name(cls, name):
        return '%s:%s' % (cls.__name__, name)

    @classmethod
    def split_name(cls, name):
        return name.split(':')

    @classmethod
    def __exists(cls, name):
        domain = Persistance.get_domain()
        a = domain.get_attributes(cls.join_name(name), ['__name__'])
        if a.has_key('__name__'):
            return True
        else:
            return False

    @classmethod
    def find(cls, name):
        if cls.__exists(name):
            return cls(name, check=False)
        else:
            return None

    @classmethod
    def list(cls):
        domain = Persistance.get_domain()
        rs = domain.query("['__type__' = '%s']" % cls.__name__)
        return object_lister(cls, rs)

    def __init__(self, name, check=True):
        self.name = name
        if check and not self.__exists(name):
            domain = Persistance.get_domain()
            domain.put_attributes(self, {'__type__' : self.__class__.__name__,
                                         '__name__' : self.name})

    def __repr__(self):
        return self.join_name(self.name)

    def get_handle(self):
        return '%s:%s' % (self.__class__.__module__, self)

class StringValue:

    def __init__(self, **params):
        if params.has_key('max_length'):
            self.max_length = params['max_length']
        else:
            self.max_length = 1024
        if params.has_key('default'):
            self.set(params['default'])
        else:
            self.set('')

    def set(self, value):
        if isinstance(value, str) or isinstance(value, unicode):
            if len(value) > self.max_length:
                raise SDBPersistanceError('Max size of %d characters exceeded' % self.max_length)
            self.value = value
        else:
            raise SDBPersistanceError('Value must be of type str or unicode')

    def set_from_string(self, str_value):
        self.set(str_value)

    def get(self):
        return self.value

    def get_as_string(self):
        return self.get()
    
class UnsignedIntValue:

    def __init__(self, **params):
        if params.has_key('max_length'):
            self.max_length = params['max_length']
        else:
            self.max_length = 10
        if params.has_key('default'):
            self.set(params['default'])
        else:
            self.set(0)
        self.format_string = '%%0%dd' % self.max_length

    def set(self, value):
        if not isinstance(value, int):
            raise SDBPersistanceError('Value must be of type int')
        self.value = value

    def set_from_string(self, str_value):
        self.set(int(str_value))

    def get(self):
        return self.value

    def get_as_string(self):
        return self.format_string % self.get()
    
class DateTimeValue:

    def __init__(self, **params):
        if params.has_key('max_length'):
            self.max_length = params['max_length']
        else:
            self.max_length = 1024
        if params.has_key('default'):
            self.set(params['default'])
        else:
            self.set(datetime.now())

    def set(self, value):
        if not isinstance(value, datetime):
            raise SDBPersistanceError('Value must be of type datetime')
        self.value = value

    def set_from_string(self, str_value):
        try:
            ts = datetime.strptime(str_value, ISO8601)
            self.set(ts)
        except:
            raise SDBPersistanceError('Date String is not in ISO8601 format')

    def get(self):
        return self.value

    def get_as_string(self):
        return self.value.strftime(ISO8601)
    
class ObjectValue:

    def __init__(self, **params):
        if params.has_key('max_length'):
            self.max_length = params['max_length']
        else:
            self.max_length = 1024
        if params.has_key('default'):
            self.set(params['default'])
        else:
            self.set(None)

    def set(self, value):
        if value == None:
            return
        if not isinstance(value, SDBObject):
            raise SDBPersistanceError('Value must be subclass of SDBObject')
        self.value = value

    def set_from_string(self, str_value):
        try:
            module_name, class_name, obj_name = str_value.split(':')
            cls = find_class(module_name, class_name)
            self.set(cls(obj_name))
        except:
            raise SDBPersistanceError('Object Reference is not in correct format')

    def get(self):
        return self.value

    def get_as_string(self):
        return self.value.get_handle()

class ScalarProperty(object):

    def __init__(self, name, value_class, **params):
        self.name = name
        self.value = value_class(**params)
        self.slot_name = '__' + name

    def __get__(self, obj, objtype):
        if obj:
            try:
                value = getattr(obj, self.slot_name)
            except AttributeError:
                domain = Persistance.get_domain()
                a = domain.get_attributes(obj, [self.name])
                if a.has_key(self.name):
                    self.value.set_from_string(a[self.name])
                    value = self.value.get()
                    setattr(obj, self.slot_name, value)
                else:
                    self.__set__(obj, self.value.get())
        return value

    def __set__(self, obj, value):
        domain = Persistance.get_domain()
        self.value.set(value)
        setattr(obj, self.slot_name, self.value.get())
        domain.put_attributes(obj, {self.name : self.value.get_as_string()}, replace=True)

class StringProperty(ScalarProperty):

    def __init__(self, name, **params):
        ScalarProperty.__init__(self, name, StringValue, **params)

class UnsignedIntProperty(ScalarProperty):

    def __init__(self, name, **params):
        ScalarProperty.__init__(self, name, UnsignedIntValue, **params)

class DateTimeProperty(ScalarProperty):

    def __init__(self, name, **params):
        ScalarProperty.__init__(self, name, DateTimeValue, **params)

class ObjectProperty(ScalarProperty):

    def __init__(self, name, **params):
        ScalarProperty.__init__(self, name, ObjectValue, **params)
        
class MultiValueProperty(object):

    def __init__(self, name, value_class, **params):
        self.name = name
        self.value = value_class(**params)
        self._list = None

    def __repr__(self):
        if self._list == None:
            return '[]'
        else:
            return repr(self._list)

    def append(self, value):
        self.value.set(value)
        self._list.append(self.value.get())
        domain = Persistance.get_domain()
        domain.put_attributes(self.object, {self.name : self.value.get_as_string()}, replace=False)

    def __get__(self, obj, objtype):
        if obj != None:
            self.object = obj
            if self._list == None:
                self._list = []
                domain = Persistance.get_domain()
                a = domain.get_attributes(obj, [self.name])
                if a.has_key(self.name):
                    lst = a[self.name]
                    if not isinstance(lst, list):
                        lst = [lst]
                    for value in lst:
                        self.value.set_from_string(value)
                        self._list.append(self.value.get())
        return self

    def __set__(self, obj, value):
        if not isinstance(value, list):
            raise SDBPersistanceError('Value must be a list')
        self._list = value
        str_list = []
        for value in self._list:
            self.value.set(value)
            str_list.append(self.value.get_as_string())
        domain = Persistance.get_domain()
        domain.put_attributes(obj, {self.name : str_list}, replace=True)

class StringListProperty(MultiValueProperty):

    def __init__(self, name, **params):
        MultiValueProperty.__init__(self, name, StringValue, **params)

class UnsignedIntListProperty(MultiValueProperty):

    def __init__(self, name, **params):
        MultiValueProperty.__init__(self, name, UnsignedIntValue, **params)

class ObjectListProperty(MultiValueProperty):

    def __init__(self, name, **params):
        MultiValueProperty.__init__(self, name, ObjectValue, **params)
        
