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
from boto.utils import find_class
import uuid
from boto.sdb.db.key import Key
from datetime import datetime

ISO8601 = '%Y-%m-%dT%H:%M:%SZ'

class SDBManager(object):
    
    def __init__(self, cls, db_name, db_user, db_passwd, db_host, db_port, db_table):
        self.cls = cls
        self.db_name = db_name
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_host = db_host
        self.db_port = db_port
        self.db_table = db_table
        self.s3 = None
        self._connect()

    class Converter:
        """
        Responsible for converting base Python types to format compatible with underlying
        database.  For SimpleDB, that means everything needs to be converted to a string
        when stored in SimpleDB and from a string when retrieved.

        To convert a value, pass it to the encode or decode method.  The encode method
        will take a Python native value and convert to DB format.  The decode method will
        take a DB format value and convert it to Python native format.  To find the appropriate
        method to call, the generic encode/decode methods will look for the type-specific
        method by searching for a method called "encode_<type name>" or "decode_<type name>".
        """
        @classmethod
        def encode(cls, manager, prop, value):
            if hasattr(prop, 'reference_class'):
                return cls.encode_reference(manager, value)
            elif isinstance(value, str) or isinstance(value, unicode):
                return value
            # make sure the check for bool comes before the check for int because
            # a bool is actually considered an instance of int!!
            elif isinstance(value, bool):
                return cls.encode_bool(manager, value)
            elif isinstance(value, int) or isinstance(value, long):
                return cls.encode_int(manager, value)
            elif isinstance(value, datetime):
                return cls.encode_datetime(manager, value)
            elif isinstance(value, list):
                return value
            else:
                return str(value)

        @classmethod
        def decode(cls, manager, prop, value):
            if prop.data_type == str or prop.data_type == unicode:
                return value
            # make sure the check for bool comes before the check for int because
            # a bool is actually considered an instance of int!!
            elif prop.data_type == bool:
                return cls.decode_bool(manager, value)
            elif prop.data_type == int or prop.data_type == long:
                return cls.decode_int(manager, value)
            elif prop.data_type == datetime:
                return cls.decode_datetime(manager, value)
            elif prop.data_type == Key:
                return cls.decode_reference(manager, value)
            else:
                return value

        @classmethod
        def encode_int(cls, manager, value):
            value = long(value)
            value += 9223372036854775808
            return '%020d' % value

        @classmethod
        def decode_int(cls, manager, value):
            value = long(value)
            value -= 9223372036854775808
            return value

        @classmethod
        def encode_bool(cls, manager, value):
            if value == True:
                return 'true'
            else:
                return 'false'

        @classmethod
        def decode_bool(cls, manager, value):
            if value.lower() == 'true':
                return True
            else:
                return False

        @classmethod
        def encode_datetime(cls, manager, value):
            return value.strftime(ISO8601)

        @classmethod
        def decode_datetime(cls, manager, value):
            try:
                return datetime.strptime(value, ISO8601)
            except:
                return None

        @classmethod
        def encode_reference(cls, manager, value):
            if isinstance(value, str) or isinstance(value, unicode):
                return value
            if value == None:
                return ''
            else:
                return value.id

        @classmethod
        def decode_reference(cls, manager, value):
            if not value:
                return None
            try:
                return manager.get_object_from_id(value)
            except:
                raise ValueError, 'Unable to convert %s to Object' % value

    def _connect(self):
        self.sdb = boto.connect_sdb(aws_access_key_id=self.db_user,
                                    aws_secret_access_key=self.db_passwd)
        self.domain = self.sdb.lookup(self.db_name)
        if not self.domain:
            self.domain = self.sdb.create_domain(self.db_name)

    def _object_lister(self, cls, query_lister):
        for item in query_lister:
            yield self.get_object_from_id(item.name)
            
    def encode_value(self, prop, value):
        return self.Converter.encode(self, prop, value)

    def decode_value(self, prop, value):
        return self.Converter.decode(self, prop, value)

    def get_s3_connection(self):
        if not self.s3:
            self.s3 = boto.connect_s3(self.aws_access_key_id, self.aws_secret_access_key)
        return self.s3

    def get_object(self, cls, id):
        a = self.domain.get_attributes(id)
        if not a.has_key('__type__'):
            raise SDBPersistenceError('%s object with id=%s does not exist' % (cls.__name__, id))
        obj = cls(id)
        obj.auto_update = False
        for prop in obj.properties(hidden=False):
            if a.has_key(prop.name):
                v = self.decode_value(prop, a[prop.name])
                setattr(obj, prop.name, v)
        obj.auto_update = True
        return obj
        
    def get_object_from_id(self, id):
        return self.get_object(self.cls, id)

    def query(self, cls, filters):
        if len(filters) > 4:
            raise SDBPersistenceError('Too many filters, max is 4')
        parts = ["['__type__'='%s'] union ['__lineage__'starts-with'%s']" % (cls.__name__, cls.get_lineage())]
        properties = cls.properties()
        for filter, value in filters:
            name, op = filter.strip().split()
            found = False
            for property in properties:
                if property.name == name:
                    found = True
                    value = self.encode_value(property, value)
                    parts.append("['%s' %s '%s']" % (name, op, value))
            if not found:
                raise SDBPersistenceError('%s is not a valid field' % key)
        query = ' intersection '.join(parts)
        rs = self.domain.query(query)
        return self._object_lister(cls, rs)

    def query_gql(self, query_string, *args, **kwds):
        raise NotImplementedError, "GQL queries not supported in SimpleDB"

    def save_object(self, obj):
        obj._auto_update = False
        if not obj.id:
            obj.id = str(uuid.uuid4())
        attrs = {'__type__' : obj.__class__.__name__,
                 '__module__' : obj.__class__.__module__,
                 '__lineage__' : obj.get_lineage()}
        for property in obj.properties(hidden=False):
            value = property.get_value_for_datastore(obj)
            if value:
                attrs[property.name] = value
        self.domain.put_attributes(obj.id, attrs, replace=True)
        obj._uto_update = True

    def delete_object(self, obj):
        self.domain.delete_attributes(obj.id)

    def set_property(self, prop, obj, name, value):
        value = self.encode_value(prop, value)
        self.domain.put_attributes(obj.id, {name : value}, replace=True)

    def get_property(self, prop, obj, name):
        a = self.domain.get_attributes(obj.id, name)
        # try to get the attribute value from SDB
        if name in a:
            return self.decode_value(prop, a[name])
        raise AttributeError, '%s not found' % name

    def set_key_value(self, obj, name, value):
        self.domain.put_attributes(obj.id, {name : value}, replace=True)

    def get_key_value(self, obj, name):
        a = self.domain.get_attributes(obj.id, name)
        if a.has_key(name):
            return a[name]
        else:
            return None
    
    def get_raw_item(self, obj):
        return self.domain.get_item(obj.id)
        
