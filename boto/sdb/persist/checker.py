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

from datetime import datetime
from boto.s3.key import Key
from boto.sdb.persist import revive_object_from_id, get_s3_connection
from boto.exception import SDBPersistanceError

ISO8601 = '%Y-%m-%dT%H:%M:%SZ'

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
                raise ValueError, 'Length of value greater than maxlength'
        else:
            raise TypeError, 'Expecting String, got %s' % type(value)

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
            raise TypeError, 'Expecting int, got %s' % type(value)

    def from_string(self, str_value):
        return int(str_value)

    def to_string(self, value):
        self.check(value)
        return self.format_string % value
    
class BooleanChecker(ValueChecker):

    def __init__(self, **params):
        if params.has_key('default'):
            self.default = params['default']
        else:
            self.default = False

    def check(self, value):
        if not isinstance(value, bool):
            raise TypeError, 'Expecting bool, got %s' % type(value)

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
            self.default = params['default']
        else:
            self.default = datetime.now()

    def check(self, value):
        if not isinstance(value, datetime):
            raise TypeError, 'Expecting datetime, got %s' % type(value)

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
        self.ref_class = params.get('ref_class', None)
        if self.ref_class == None:
            raise SDBPersistanceError('ref_class parameter is required')

    def check(self, value):
        if value == None:
            return
        if not isinstance(value, self.ref_class):
            raise TypeError, 'Expecting %s, got %s' % (self.ref_class, type(value))

    def from_string(self, str_value):
        if not str_value:
            return None
        try:
            return revive_object_from_id(str_value)
        except:
            raise ValueError

    def to_string(self, value):
        self.check(value)
        if value == None:
            return ''
        else:
            return value.id

class S3KeyChecker(ValueChecker):

    def __init__(self, **params):
        self.default = None

    def check(self, value):
        if value == None:
            return
        if isinstance(value, str) or isinstance(value, unicode):
            try:
                bucket_name, key_name = value.split('/')
            except:
                raise ValueError
        elif not isinstance(value, Key):
            raise TypeError, 'Expecting Key, got %s' % type(value)

    def from_string(self, str_value):
        if not str_value:
            return
        try:
            bucket_name, key_name = str_value.split('/')
            s3 = get_s3_connection()
            bucket = s3.get_bucket(bucket_name)
            key = bucket.get_key(key_name)
            if not key:
                key = bucket.new_key(key_name)
            return key
        except:
            raise ValueError

    def to_string(self, value):
        self.check(value)
        if isinstance(value, str) or isinstance(value, unicode):
            return value
        if value == None:
            return None
        else:
            return '%s/%s' % (value.bucket.name, value.name)

class S3BucketChecker(ValueChecker):

    def __init__(self, **params):
        self.default = None

    def check(self, value):
        if value == None:
            return
        if not isinstance(value, str):
            raise TypeError

    def from_string(self, str_value):
        if not str_value:
            return
        try:
            s3 = get_s3_connection()
            bucket = s3.get_bucket(str_value)
            return bucket
        except:
            raise ValueError

    def to_string(self, value):
        self.check(value)
        if value == None:
            return None
        else:
            return '%s' % value.bucket.name

