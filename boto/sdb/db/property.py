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

import datetime
from key import Key
from boto.utils import Password
from boto.sdb.db.query import Query

class Property(object):

    data_type = str

    def __init__(self, verbose_name=None, name=None, default=None, required=False,
                 validator=None, choices=None):
        self.verbose_name = verbose_name
        self.name = name
        self.default = default
        self.required = required
        self.validator = validator
        self.choices = choices
        self.slot_name = '__'
        
    def __get__(self, obj, objtype):
        if obj:
            try:
                value = getattr(obj, self.slot_name)
            except AttributeError:
                if obj._auto_update:
                    value = obj._manager.get_property(self, obj, self.name)
                else:
                    value = self.default_value()
                setattr(obj, self.slot_name, value)
        return value

    def __set__(self, obj, value):
        self.validate(value)
        try:
            old_value = getattr(obj, self.slot_name)
        except:
            old_value = self.default
        setattr(obj, self.slot_name, value)
        if obj._auto_update:
            try:
                obj._manager.set_property(self, obj, self.name, value)
            except:
                setattr(obj, self.slot_name, old_value)
                raise

    def __property_config__(self, model_class, property_name):
        self.model_class = model_class
        self.name = property_name
        self.slot_name = '__' + self.name

    def default_validator(self, value):
        if value == self.default_value():
            return
        if not isinstance(value, self.data_type):
            raise TypeError, 'Validation Error, expecting %s, got %s' % (self.data_type, type(value))
                                      
    def default_value(self):
        return self.default

    def validate(self, value):
        if self.required and value==None:
            raise ValueError, '%s is a required property' % self.name
        if self.choices and not value in self.choices:
            raise ValueError, '%s not a valid choice for %s' % (value, self.name)
        if self.validator:
            self.validator(value)
        else:
            self.default_validator(value)
        return value

    def empty(self, value):
        return not value

    def get_value_for_datastore(self, model_instance):
        return getattr(model_instance, self.name)

    def make_value_from_datastore(self, value):
        return value

def validate_string(value):
    if isinstance(value, str) or isinstance(value, unicode):
        if len(value) > 1024:
            raise ValueError, 'Length of value greater than maxlength'
    else:
        raise TypeError, 'Expecting String, got %s' % type(value)

class StringProperty(Property):

    def __init__(self, verbose_name=None, name=None, default='', required=False,
                 validator=validate_string, choices=None):
        Property.__init__(self, verbose_name, name, default, required, validator, choices)

class PasswordProperty(StringProperty):
    """
    Hashed property who's original value can not be
    retrieved, but still can be compaired.
    """
    data_type = Password

    def __init__(self, verbose_name=None, name=None, default='', required=False,
                 validator=None, choices=None):
        StringProperty.__init__(self, verbose_name, name, default, required, validator, choices)

    def __set__(self, obj, value):
        p = Password()
        p.set(value)
        Property.__set__(self, obj, p)

    def __get__(self, obj, objtype):
        return Password(StringProperty.__get__(self, obj, objtype))

    def validate(self, value):
        value = Property.validate(self, value)
        if isinstance(value, Password):
            if len(value) > 1024:
                raise ValueError, 'Length of value greater than maxlength'
        else:
            raise TypeError, 'Expecting Password, got %s' % type(value)

class IntegerProperty(Property):

    data_type = int

    def __init__(self, verbose_name=None, name=None, default=0, required=False,
                 validator=None, choices=None):
        Property.__init__(self, verbose_name, name, default, required, validator, choices)

    def default_validator(self, value):
        if not isinstance(value, int) and not isinstance(value, long):
            raise TypeError, 'Expecting int or long, got %s' % type(value)
                                      
    def validate(self, value):
        value = Property.validate(self, value)
        min = -9223372036854775808
        max = 9223372036854775807
        if value > max:
            raise ValueError, 'Maximum value is %d' % max
        if value < min:
            raise ValueError, 'Minimum value is %d' % min
    
        
    def empty(self, value):
        return value is None

class BooleanProperty(Property):

    data_type = bool

    def __init__(self, verbose_name=None, name=None, default=False, required=False,
                 validator=None, choices=None):
        Property.__init__(self, verbose_name, name, default, required, validator, choices)

    def empty(self, value):
        return value is None
    
class DateTimeProperty(Property):

    data_type = datetime.datetime

    def __init__(self, verbose_name=None, auto_now=False, auto_now_add=False, name=None,
                 default=None, required=False, validator=None, choices=None):
        Property.__init__(self, verbose_name, name, default, required, validator, choices)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

    def default_value(self):
        if self.auto_now or self.auto_now_add:
            return self.now()
        return Property.default_value(self)

    def get_value_for_datastore(self, model_instance):
        if self.auto_now:
            save = model_instance._auto_update
            model_instance._auto_update = False
            setattr(model_instance, self.name, self.now())
            model_instance._auto_update = save
        return Property.get_value_for_datastore(self, model_instance)

    def now(self):
        return datetime.datetime.now()

class ReferenceProperty(Property):

    data_type = Key

    def __init__(self, reference_class=None, collection_name=None,
                 verbose_name=None, name=None, default=None, required=False, validator=None, choices=None):
        Property.__init__(self, verbose_name, name, default, required, validator, choices)
        self.reference_class = reference_class
        self.collection_name = collection_name
        
    def __property_config__(self, model_class, property_name):
        Property.__property_config__(self, model_class, property_name)
        if self.collection_name is None:
            self.collection_name = '%s_set' % (model_class.__name__.lower())
        if hasattr(self.reference_class, self.collection_name):
            raise ValueError, 'duplicate property: %s' % self.collection_name
        setattr(self.reference_class, self.collection_name,
                _ReverseReferenceProperty(model_class, property_name))

    def validate(self, value):
        if self.required and value==None:
            raise ValueError, '%s is a required property' % self.name
        if value == None:
            return
        if isinstance(value, str) or isinstance(value, unicode):
            # ugly little hack - sometimes I want to just stick a UUID string
            # in here rather than instantiate an object. 
            # This does a bit of hand waving to "type check" the string
            t = value.split('-')
            if len(t) != 5:
                raise ValueError
        else:
            try:
                obj_lineage = value.get_lineage()
                cls_lineage = self.reference_class.get_lineage()
                if obj_lineage.startswith(cls_lineage):
                    return
                raise TypeError, '%s not instance of %s' % (obj_lineage, cls_lineage)
            except:
                raise ValueError, '%s is not a Model' % value
        
class _ReverseReferenceProperty(Property):

    def __init__(self, model, prop):
        self.__model = model
        self.__property = prop

    def __get__(self, model_instance, model_class):
        """Fetches collection of model instances of this collection property."""
        if model_instance is not None:
            query = Query(self.__model)
            return query.filter(self.__property + ' =', model_instance)
        else:
            return self

    def __set__(self, model_instance, value):
        """Not possible to set a new collection."""
        raise ValueError, 'Virtual property is read-only'

        
class ListProperty(Property):
    
    data_type = list

    def __init__(self, item_type, verbose_name=None, name=None, default=None, **kwds):
        if not isinstance(item_type, type):
            raise TypeError('Item type should be a type object')
        if default is None:
            default = []
        self.item_type = item_type
        Property.__init__(self, verbose_name, name, default=default, required=True, **kwds)

    def validate(self, value):
        value = super(ListProperty, self).validate(value)
        if value is not None:
            if not isinstance(value, list):
                raise ValueError, 'Property %s must be a list' % self.name

        if self.item_type in (int, long):
            item_type = (int, long)
        else:
            item_type = self.item_type

        for item in value:
            if not isinstance(item, item_type):
                if item_type == (int, long):
                    raise ValueError, 'Items in the %s list must all be integers.' % self.name
                else:
                    raise ValueError('Items in the %s list must all be %s instances' %
                                     (self.name, self.item_type.__name__))
        return value

    def empty(self, value):
        return value is None

    def default_value(self):
        return list(super(ListProperty, self).default_value())

