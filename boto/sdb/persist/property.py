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

from boto.exception import SDBPersistanceError
from boto.sdb.persist import get_domain
from boto.sdb.persist.checker import *

class Property(object):

    def __init__(self, checker_class, **params):
        self.name = ''
        self.checker = checker_class(**params)
        self.slot_name = '__'
        
    def set_name(self, name):
        self.name = name
        self.slot_name = '__' + self.name

class ScalarProperty(Property):

    def save(self, obj):
        domain = get_domain()
        domain.put_attributes(obj.id, {self.name : self.to_string(obj)}, replace=True)

    def to_string(self, obj):
        return self.checker.to_string(getattr(obj, self.name))

    def load(self, obj):
        domain = get_domain()
        a = domain.get_attributes(obj.id, self.name)
        # try to get the attribute value from SDB
        if self.name in a:
            value = self.checker.from_string(a[self.name])
            setattr(obj, self.slot_name, value)
        # if it's not there, set the value to the default value
        else:
            self.__set__(obj, self.checker.default)

    def __get__(self, obj, objtype):
        if obj:
            try:
                value = getattr(obj, self.slot_name)
            except AttributeError:
                if obj.auto_update:
                    self.load(obj)
                    value = getattr(obj, self.slot_name)
                else:
                    value = self.checker.default
                    setattr(obj, self.slot_name, self.checker.default)
        return value

    def __set__(self, obj, value):
        self.checker.check(value)
        try:
            old_value = getattr(obj, self.slot_name)
        except:
            old_value = self.checker.default
        setattr(obj, self.slot_name, value)
        if obj.auto_update:
            try:
                self.save(obj)
            except:
                setattr(obj, self.slot_name, old_value)
                raise
                                      
class StringProperty(ScalarProperty):

    def __init__(self, **params):
        ScalarProperty.__init__(self, StringChecker, **params)

class PositiveIntegerProperty(ScalarProperty):

    def __init__(self, **params):
        ScalarProperty.__init__(self, PositiveIntegerChecker, **params)

class BooleanProperty(ScalarProperty):

    def __init__(self, **params):
        ScalarProperty.__init__(self, BooleanChecker, **params)

class DateTimeProperty(ScalarProperty):

    def __init__(self, **params):
        ScalarProperty.__init__(self, DateTimeChecker, **params)

class ObjectProperty(ScalarProperty):

    def __init__(self, **params):
        ScalarProperty.__init__(self, ObjectChecker, **params)

class S3KeyProperty(ScalarProperty):

    def __init__(self, **params):
        ScalarProperty.__init__(self, S3KeyChecker, **params)
        
    def __set__(self, obj, value):
        self.checker.check(value)
        try:
            old_value = getattr(obj, self.slot_name)
        except:
            old_value = self.checker.default
        if isinstance(value, str):
            value = self.checker.from_string(value)
        setattr(obj, self.slot_name, value)
        if obj.auto_update:
            try:
                self.save(obj)
            except:
                setattr(obj, self.slot_name, old_value)
                raise
                                      
class S3BucketProperty(ScalarProperty):

    def __init__(self, **params):
        ScalarProperty.__init__(self, S3BucketChecker, **params)
        
    def __set__(self, obj, value):
        self.checker.check(value)
        try:
            old_value = getattr(obj, self.slot_name)
        except:
            old_value = self.checker.default
        if isinstance(value, str):
            value = self.checker.from_string(value)
        setattr(obj, self.slot_name, value)
        if obj.auto_update:
            try:
                self.save(obj)
            except:
                setattr(obj, self.slot_name, old_value)
                raise

class MultiValueProperty(Property):

    def __init__(self, checker_class, **params):
        Property.__init__(self, checker_class, **params)
        self._list = None

    def __repr__(self):
        if self._list == None:
            return '[]'
        else:
            return repr(self._list)

    def append(self, value):
        self.checker.check(value)
        self._list.append(value)
        domain = get_domain()
        try:
            domain.put_attributes(self.object.id, {self.name : self.checker.to_string(value)}, replace=False)
        except:
            print 'problem appending %s' % value

    def __get__(self, obj, objtype):
        if obj != None:
            self.object = obj
            if self._list == None:
                self._list = []
                domain = get_domain()
                a = domain.get_attributes(obj.id, self.name)
                if self.name in a:
                    lst = a[self.name]
                    if not isinstance(lst, list):
                        lst = [lst]
                    for value in lst:
                        value = self.checker.from_string(value)
                        self._list.append(value)
        return self

    def __set__(self, obj, value):
        if not isinstance(value, list):
            raise SDBPersistanceError('Value must be a list')
        self._list = value
        str_list = []
        for value in self._list:
            str_list.append(self.checker.to_string(value))
        domain = get_domain()
        try:
            domain.put_attributes(obj.id, {self.name : str_list}, replace=True)
        except:
            print 'problem setting value: %s' % value

    def __getitem__(self, key):
        if self._list != None:
            return self._list[key]

class StringListProperty(MultiValueProperty):

    def __init__(self, **params):
        MultiValueProperty.__init__(self, StringChecker, **params)

class PositiveIntegerListProperty(MultiValueProperty):

    def __init__(self, **params):
        MultiValueProperty.__init__(self, PositiveIntegerChecker, **params)

class BooleanListProperty(MultiValueProperty):

    def __init__(self, **params):
        MultiValueProperty.__init__(self, BooleanChecker, **params)

class ObjectListProperty(MultiValueProperty):

    def __init__(self, **params):
        MultiValueProperty.__init__(self, ObjectChecker, **params)
        
class HasManyProperty(Property):

    def set_name(self, name):
        self.name = name
        self.slot_name = '__' + self.name

    def __get__(self, obj, objtype):
        return self


