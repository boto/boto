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
from boto.sdb.db.model import Model
from datetime import datetime
from boto.exception import SDBPersistenceError

ISO8601 = '%Y-%m-%dT%H:%M:%SZ'

class SDBConverter:
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
    def __init__(self, manager):
        self.manager = manager
        self.type_map = { bool : (self.encode_bool, self.decode_bool),
                          int : (self.encode_int, self.decode_int),
                          long : (self.encode_long, self.decode_long),
                          Model : (self.encode_reference, self.decode_reference),
                          Key : (self.encode_reference, self.decode_reference),
                          datetime : (self.encode_datetime, self.decode_datetime)}

    def encode(self, item_type, value):
        if item_type in self.type_map:
            encode = self.type_map[item_type][0]
            return encode(value)
        return value

    def decode(self, item_type, value):
        if item_type in self.type_map:
            decode = self.type_map[item_type][1]
            return decode(value)
        return value

    def encode_prop(self, prop, value):
        if isinstance(value, list):
            if hasattr(prop, 'item_type'):
                new_value = []
                for v in value:
                    item_type = getattr(prop, "item_type")
                    if Model in item_type.mro():
                        item_type = Model
                    new_value.append(self.encode(item_type, v))
                return new_value
            else:
                return value
        else:
            return self.encode(prop.data_type, value)

    def decode_prop(self, prop, value):
        if prop.data_type == list:
            if not isinstance(value, list):
                value = [value]
            if hasattr(prop, 'item_type'):
                item_type = getattr(prop, "item_type")
                if Model in item_type.mro():
                    if item_type != self.manager.cls:
                        return item_type._manager.decode_value(prop, value)
                    else:
                        item_type = Model
                return [self.decode(item_type, v) for v in value]
            else:
                return value
        elif hasattr(prop, 'reference_class'):
            ref_class = getattr(prop, 'reference_class')
            if ref_class != self.manager.cls:
                return ref_class._manager.decode_value(prop, value)
            else:
                return self.decode(prop.data_type, value)
        else:
            return self.decode(prop.data_type, value)

    def encode_int(self, value):
        value = int(value)
        value += 2147483648
        return '%010d' % value

    def decode_int(self, value):
        value = int(value)
        value -= 2147483648
        return int(value)

    def encode_long(self, value):
        value = long(value)
        value += 9223372036854775808
        return '%020d' % value

    def decode_long(self, value):
        value = long(value)
        value -= 9223372036854775808
        return value

    def encode_bool(self, value):
        if value == True:
            return 'true'
        else:
            return 'false'

    def decode_bool(self, value):
        if value.lower() == 'true':
            return True
        else:
            return False

    def encode_datetime(self, value):
        return value.strftime(ISO8601)

    def decode_datetime(self, value):
        try:
            return datetime.strptime(value, ISO8601)
        except:
            return None

    def encode_reference(self, value):
        if isinstance(value, str) or isinstance(value, unicode):
            return value
        if value == None:
            return ''
        else:
            return value.id

    def decode_reference(self, value):
        if not value:
            return None
        try:
            return self.manager.get_object_from_id(value)
        except:
            return None

class SDBManager(object):
    
    def __init__(self, cls, db_name, db_user, db_passwd,
                 db_host, db_port, db_table, ddl_dir):
        self.cls = cls
        self.db_name = db_name
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_host = db_host
        self.db_port = db_port
        self.db_table = db_table
        self.ddl_dir = ddl_dir
        self.s3 = None
        self.converter = SDBConverter(self)
        self._connect()

    def _connect(self):
        self.sdb = boto.connect_sdb(aws_access_key_id=self.db_user,
                                    aws_secret_access_key=self.db_passwd)
        self.domain = self.sdb.lookup(self.db_name)
        if not self.domain:
            self.domain = self.sdb.create_domain(self.db_name)

    def _object_lister(self, cls, query_lister):
        for item in query_lister:
            yield self.get_object(None, item.name, item)
            
    def encode_value(self, prop, value):
        return self.converter.encode_prop(prop, value)

    def decode_value(self, prop, value):
        return self.converter.decode_prop(prop, value)

    def get_s3_connection(self):
        if not self.s3:
            self.s3 = boto.connect_s3(self.aws_access_key_id, self.aws_secret_access_key)
        return self.s3

    def get_object(self, cls, id, a=None):
        if not a:
            a = self.domain.get_attributes(id)
        if not a.has_key('__type__'):
            raise SDBPersistenceError('object %s does not exist' % id)
        if not cls:
            cls = find_class(a['__module__'], a['__type__'])
        obj = cls(id)
        obj._auto_update = False
        for prop in obj.properties(hidden=False):
            if prop.data_type != Key:
                if a.has_key(prop.name):
                    value = self.decode_value(prop, a[prop.name])
                    value = prop.make_value_from_datastore(value)
                    setattr(obj, prop.name, value)
        obj._auto_update = True
        return obj
        
    def get_object_from_id(self, id):
        return self.get_object(None, id)

    def query(self, cls, filters, limit=None, order_by=None):
        import types
        if len(filters) > 4:
            raise SDBPersistenceError('Too many filters, max is 4')
        s = "['__type__'='%s'" % cls.__name__
        for subclass in cls.__sub_classes__:
            s += " OR '__type__'='%s'" % subclass.__name__
        s += "]"
        parts = [s]
        properties = cls.properties(hidden=False)
        for filter, value in filters:
            name, op = filter.strip().split()
            found = False
            for property in properties:
                if property.name == name:
                    found = True
                    if types.TypeType(value) == types.ListType:
                        filter_parts = []
                        for val in value:
                            val = self.encode_value(property, val)
                            filter_parts.append("'%s' %s '%s'" % (name, op, val))
                        parts.append("[%s]" % " OR ".join(filter_parts))
                    else:
                        value = self.encode_value(property, value)
                        parts.append("['%s' %s '%s']" % (name, op, value))
            if not found:
                raise SDBPersistenceError('%s is not a valid field' % name)
        if order_by:
            if order_by.startswith("-"):
                key = order_by[1:]
                type = "desc"
            else:
                key = order_by
                type = "asc"
            parts.append("['%s' starts-with ''] sort '%s' %s" % (key, key, type))
        query = ' intersection '.join(parts)
        rs = self.domain.query(query, max_items=limit)
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
            if value is not None:
                value = self.encode_value(property, value)
                attrs[property.name] = value
            if property.unique:
                try:
                    args = {property.name: value}
                    obj2 = obj.find(**args).next()
                    if obj2.id != obj.id:
                        raise SDBPersistenceError("Error: %s must be unique!" % property.name)
                except(StopIteration):
                    pass
        self.domain.put_attributes(obj.id, attrs, replace=True)
        obj._auto_update = True

    def delete_object(self, obj):
        self.domain.delete_attributes(obj.id)

    def set_property(self, prop, obj, name, value):
        value = prop.get_value_for_datastore(obj)
        value = self.encode_value(prop, value)
        if prop.unique:
            try:
                args = {prop.name: value}
                obj2 = obj.find(**args).next()
                if obj2.id != obj.id:
                    raise SDBPersistenceError("Error: %s must be unique!" % prop.name)
            except(StopIteration):
                pass
        self.domain.put_attributes(obj.id, {name : value}, replace=True)

    def get_property(self, prop, obj, name):
        a = self.domain.get_attributes(obj.id, name)
        # try to get the attribute value from SDB
        if name in a:
            value = self.decode_value(prop, a[name])
            return prop.make_value_from_datastore(value)
        raise AttributeError, '%s not found' % name

    def set_key_value(self, obj, name, value):
        self.domain.put_attributes(obj.id, {name : value}, replace=True)

    def delete_key_value(self, obj, name):
        self.domain.delete_attributes(obj.id, name)

    def get_key_value(self, obj, name):
        a = self.domain.get_attributes(obj.id, name)
        if a.has_key(name):
            return a[name]
        else:
            return None
    
    def get_raw_item(self, obj):
        return self.domain.get_item(obj.id)
        
