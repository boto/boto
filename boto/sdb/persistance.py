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

import boto
from datetime import datetime
from boto.exception import SDBPersistanceError
from boto.s3.key import Key
from boto.utils import find_class
import uuid

ISO8601 = '%Y-%m-%dT%H:%M:%SZ'

class Persistance:

    __sdb = boto.connect_sdb()
    __domain = None
    __s3_conn = None
        
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
    def get_s3_connection(cls):
        if cls.__s3_conn == None:
            cls.__s3_conn = boto.connect_s3()
        return cls.__s3_conn

def revive_object_from_id(id):
    domain = Persistance.get_domain()
    attrs = domain.get_attributes(id, ['__module__', '__type__'])
    cls = find_class(attrs['__module__'], attrs['__type__'])
    return cls(id)

def object_lister(cls, query_lister):
    for item in query_lister:
        if cls:
            yield cls(item.name)
        else:
            yield revive_object_from_id(item.name)

class SDBBase(type):
    "Metaclass for all SDBObjects"
    def __init__(cls, name, bases, dict):
        super(SDBBase, cls).__init__(name, bases, dict)
        # Make sure this is a subclass of SDBObject - mainly copied from django ModelBase (thanks!)
        try:
            if filter(lambda b: issubclass(b, SDBObject), bases):
                # look for all of the Properties and set their names
                for key in dict.keys():
                    if isinstance(dict[key], Property):
                        property = dict[key]
                        property.set_name(key)
        except NameError:
            # 'SDBObject' isn't defined yet, meaning we're looking at our own
            # SDBObject class, defined below.
            pass
        
class SDBObject(object):
    __metaclass__ = SDBBase

    @classmethod
    def get(cls, id=None, **params):
        domain = Persistance.get_domain()
        if id:
            a = domain.get_attributes(id, ['__type__'])
            if a.has_key('__type__'):
                return cls(id)
            else:
                raise SDBPersistanceError('%s object with id=%s does not exist' % (cls.__name__, id))
        else:
            rs = cls.find(**params)
            try:
                obj = rs.next()
            except StopIteration:
                raise SDBPersistanceError('%s object matching query does not exist' % cls.__name__)
            try:
                rs.next()
            except StopIteration:
                return obj
            raise SDBPersistanceError('Query matched more than 1 item')

    @classmethod
    def find(cls, **params):
        keys = params.keys()
        if len(keys) > 4:
            raise SDBPersistanceError('Too many fields, max is 4')
        parts = ["['__type__' = '%s']" % cls.__name__]
        for key in keys:
            if cls.__dict__.has_key(key):
                if isinstance(cls.__dict__[key], ScalarProperty):
                    checker = cls.__dict__[key].checker
                    parts.append("['%s' = '%s']" % (key, checker.to_string(params[key])))
                else:
                    raise SDBPersistanceError('%s is not a searchable field' % key)
            else:
                raise SDBPersistanceError('%s is not a valid field' % key)
        query = ' intersection '.join(parts)
        domain = Persistance.get_domain()
        rs = domain.query(query)
        return object_lister(cls, rs)

    @classmethod
    def list(cls):
        domain = Persistance.get_domain()
        rs = domain.query("['__type__' = '%s']" % cls.__name__)
        return object_lister(cls, rs)

    def __init__(self, id=None, name=None):
        self.id = id
        self.name = name
        if self.id:
            self.auto_update = True
            domain = Persistance.get_domain()
            attrs = domain.get_attributes(self.id, ['__name__'])
            if attrs.has_key('__name__'):
                self.name = attrs['__name__']
        else:
            self.id = str(uuid.uuid4())
            self.auto_update = False

    def __repr__(self):
        return '%s<%s>' % (self.__class__.__name__, self.id)

    def save(self):
        keys = self.__class__.__dict__.keys()
        attrs = {'__type__' : self.__class__.__name__,
                 '__module__' : self.__class__.__module__}
        if self.name:
            attrs['__name__'] = self.name
        for key in keys:
            if isinstance(self.__class__.__dict__[key], ScalarProperty):
                property = self.__class__.__dict__[key]
                attrs[property.name] = property.to_string(self)
        domain = Persistance.get_domain()
        domain.put_attributes(self.id, attrs, replace=True)
        self.auto_update = True
        
    def delete(self):
        domain = Persistance.get_domain()
        domain.delete_attributes(self.id)

    def get_related_objects(self, ref_name, ref_cls=None):
        domain = Persistance.get_domain()
        query = "['%s' = '%s']" % (ref_name, self.id)
        if ref_cls:
            query += " intersection ['__type__'='%s']" % ref_cls.__name__
        rs = domain.query(query)
        return object_lister(ref_cls, rs)

class ValueChecker:

    def check(self, value):
        """
        Checks a value to see if it is of the right type.

        Should raise a TypeError exception if an in appropriate value is passed in.
        """
        raise TypeError

    def from_string(self, str_value):
        """
        Takes a string as input and returns the type-specific value represented by that string.

        Should raise a ValueError if the value cannot be converted to the appropriate type.
        """
        raise ValueError

    def to_string(self, value):
        """
        Convert a value to it's string representation.

        Should raise a ValueError if the value cannot be converted to a string representation.
        """
        raise ValueError
    
class StringChecker(ValueChecker):

    def __init__(self, **params):
        if params.has_key('maxlength'):
            self.maxlength = params['maxlength']
        else:
            self.maxlength = 1024
        if params.has_key('default'):
            self.check(params['default'])
            self.default = params['default']
        else:
            self.default = ''

    def check(self, value):
        if isinstance(value, str) or isinstance(value, unicode):
            if len(value) > self.maxlength:
                raise ValueError
        else:
            raise TypeError

    def from_string(self, str_value):
        return str_value

    def to_string(self, value):
        self.check(value)
        return value

class PositiveIntegerChecker(ValueChecker):

    def __init__(self, **params):
        if params.has_key('maxlength'):
            self.maxlength = params['maxlength']
        else:
            self.maxlength = 10
        if params.has_key('default'):
            self.check(params['default'])
            self.default = params['default']
        else:
            self.default = 0
        self.format_string = '%%0%dd' % self.maxlength

    def check(self, value):
        if not isinstance(value, int):
            raise TypeError

    def from_string(self, str_value):
        return int(str_value)

    def to_string(self, value):
        self.check(value)
        return self.format_string % value
    
class BooleanChecker(ValueChecker):

    def __init__(self, **params):
        if params.has_key('default'):
            self.set(params['default'])
        else:
            self.set(False)

    def check(self, value):
        if not isinstance(value, bool):
            raise TypeError

    def from_string(self, str_value):
        if str_value.lower() == 'true':
            return True
        else:
            return False
        
    def to_string(self, value):
        self.check(value)
        if value == True:
            return 'true'
        else:
            return 'false'
    
class DateTimeChecker(ValueChecker):

    def __init__(self, **params):
        if params.has_key('maxlength'):
            self.maxlength = params['maxlength']
        else:
            self.maxlength = 1024
        if params.has_key('default'):
            self.set(params['default'])
        else:
            self.set(datetime.now())

    def check(self, value):
        if not isinstance(value, datetime):
            raise TypeError

    def from_string(self, str_value):
        try:
            return datetime.strptime(str_value, ISO8601)
        except:
            raise ValueError

    def to_string(self, value):
        self.check(value)
        return value.strftime(ISO8601)
    
class ObjectChecker(ValueChecker):

    def __init__(self, **params):
        self.default = None
        self.ref_class = params.get('ref_class', SDBObject)

    def check(self, value):
        if value == None:
            return
        if not isinstance(value, SDBObject):
            raise TypeError
        if not isinstance(value, self.ref_class):
            raise TypeError

    def from_string(self, str_value):
        try:
            return revive_object_from_id(str_value)
        except:
            raise ValueError

    def to_string(self, value):
        self.check(value)
        return value.id

class S3KeyChecker(ValueChecker):

    def __init__(self, **params):
        self.default = None

    def check(self, value):
        if value == None:
            return
        if not isinstance(value, Key):
            raise TypeError

    def from_string(self, str_value):
        try:
            bucket_name, key_name = str_value.split('/')
            s3 = Persistance.get_s3_connection()
            bucket = s3.get_bucket(bucket_name)
            key = bucket.get_key(key_name)
            if not key:
                key = bucket.new_key(key_name)
            return key
        except:
            raise ValueError

    def to_string(self, value):
        self.check(value)
        return '%s/%s' % (value.bucket.name, value.name)

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
        domain = Persistance.get_domain()
        domain.put_attributes(obj.id, {self.name : self.to_string(obj)}, replace=True)

    def to_string(self, obj):
        return self.checker.to_string(getattr(obj, self.name))

    def load(self, obj):
        domain = Persistance.get_domain()
        a = domain.get_attributes(obj.id, [self.name])
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
        
class MultiValueProperty(Property):

    def __repr__(self):
        if self._list == None:
            return '[]'
        else:
            return repr(self._list)

    def append(self, value):
        self.checker.check(value)
        self._list.append(value)
        domain = Persistance.get_domain()
        try:
            domain.put_attributes(self.object.id, {self.name : self.checker.to_string(value)}, replace=False)
        except:
            print 'problem appending %s' % value

    def __get__(self, obj, objtype):
        if obj != None:
            self.object = obj
            if self._list == None:
                self._list = []
                domain = Persistance.get_domain()
                a = domain.get_attributes(obj.id, [self.name])
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
        domain = Persistance.get_domain()
        try:
            domain.put_attributes(obj.id, {self.name : str_list}, replace=True)
        except:
            print 'problem setting value: %s' % value

    def __getitem__(self, key):
        if self._list != None:
            return self._list[key]

class StringListProperty(MultiValueProperty):

    def __init__(self, name, **params):
        MultiValueProperty.__init__(self, name, StringChecker, **params)

class PositiveIntegerListProperty(MultiValueProperty):

    def __init__(self, name, **params):
        MultiValueProperty.__init__(self, name, PositiveIntegerChecker, **params)

class BooleanListProperty(MultiValueProperty):

    def __init__(self, name, **params):
        MultiValueProperty.__init__(self, name, BooleanChecker, **params)

class ObjectListProperty(MultiValueProperty):

    def __init__(self, name, **params):
        MultiValueProperty.__init__(self, name, ObjectChecker, **params)
        
