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
from boto.sdb.db.key import Key
from boto.sdb.db.model import Model
import psycopg2
import psycopg2.extensions
import uuid
import os
import string
from boto.exception import SDBPersistenceError

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

class PGConverter:
    
    def __init__(self, manager):
        self.manager = manager
        self.type_map = {Key : (self.encode_reference, self.decode_reference),
                         Model : (self.encode_reference, self.decode_reference)}

    def encode(self, type, value):
        if type in self.type_map:
            encode = self.type_map[type][0]
            return encode(value)
        return value

    def decode(self, type, value):
        if type in self.type_map:
            decode = self.type_map[type][1]
            return decode(value)
        return value

    def encode_prop(self, prop, value):
        if isinstance(value, list):
            if hasattr(prop, 'item_type'):
                s = "{"
                new_value = []
                for v in value:
                    item_type = getattr(prop, 'item_type')
                    if Model in item_type.mro():
                        item_type = Model
                    new_value.append('%s' % self.encode(item_type, v))
                s += ','.join(new_value)
                s += "}"
                return s
            else:
                return value
        return self.encode(prop.data_type, value)

    def decode_prop(self, prop, value):
        if prop.data_type == list:
            if value != None:
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
            return value
        elif hasattr(prop, 'reference_class'):
            ref_class = getattr(prop, 'reference_class')
            if ref_class != self.manager.cls:
                return ref_class._manager.decode_value(prop, value)
            else:
                return self.decode(prop.data_type, value)
        elif hasattr(prop, 'calculated_type'):
            calc_type = getattr(prop, 'calculated_type')
            return self.decode(calc_type, value)
        else:
            return self.decode(prop.data_type, value)

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
            raise ValueError, 'Unable to convert %s to Object' % value

class PGManager(object):

    def __init__(self, cls, db_name, db_user, db_passwd,
                 db_host, db_port, db_table, sql_dir, enable_ssl):
        self.cls = cls
        self.db_name = db_name
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_host = db_host
        self.db_port = db_port
        self.db_table = db_table
        self.sql_dir = sql_dir
        self.in_transaction = False
        self.converter = PGConverter(self)
        self._connect()

    def _build_connect_string(self):
        cs = 'dbname=%s user=%s password=%s host=%s port=%d'
        return cs % (self.db_name, self.db_user, self.db_passwd,
                     self.db_host, self.db_port)

    def _connect(self):
        self.connection = psycopg2.connect(self._build_connect_string())
        self.connection.set_client_encoding('UTF8')
        self.cursor = self.connection.cursor()

    def _object_lister(self, cursor):
        try:
            for row in cursor:
                yield self._object_from_row(row, cursor.description)
        except StopIteration:
            cursor.close()
            raise StopIteration
                
    def _dict_from_row(self, row, description):
        d = {}
        for i in range(0, len(row)):
            d[description[i][0]] = row[i]
        return d

    def _object_from_row(self, row, description=None):
        if not description:
            description = self.cursor.description
        d = self._dict_from_row(row, description)
        obj = self.cls(d['id'])
        obj._manager = self
        obj._auto_update = False
        for prop in obj.properties(hidden=False):
            if prop.data_type != Key:
                v = self.decode_value(prop, d[prop.name])
                v = prop.make_value_from_datastore(v)
                if hasattr(prop, 'calculated_type'):
                    prop._set_direct(obj, v)
                elif not prop.empty(v):
                    setattr(obj, prop.name, v)
                else:
                    setattr(obj, prop.name, prop.default_value())
        return obj

    def _build_insert_qs(self, obj, calculated):
        fields = []
        values = []
        templs = []
        id_calculated = [p for p in calculated if p.name == 'id']
        for prop in obj.properties(hidden=False):
            if prop not in calculated:
                value = prop.get_value_for_datastore(obj)
                if value != prop.default_value() or prop.required:
                    value = self.encode_value(prop, value)
                    values.append(value)
                    fields.append('"%s"' % prop.name)
                    templs.append('%s')
        qs = 'INSERT INTO "%s" (' % self.db_table
        if len(id_calculated) == 0:
            qs += '"id",'
        qs += ','.join(fields)
        qs += ") VALUES ("
        if len(id_calculated) == 0:
            qs += "'%s'," % obj.id
        qs += ','.join(templs)
        qs += ')'
        if calculated:
            qs += ' RETURNING '
            calc_values = ['"%s"' % p.name for p in calculated]
            qs += ','.join(calc_values)
        qs += ';'
        return qs, values

    def _build_update_qs(self, obj, calculated):
        fields = []
        values = []
        for prop in obj.properties(hidden=False):
            if prop not in calculated:
                value = prop.get_value_for_datastore(obj)
                if value != prop.default_value() or prop.required:
                    value = self.encode_value(prop, value)
                    values.append(value)
                    field = '"%s"=' % prop.name
                    field += '%s'
                    fields.append(field)
        qs = 'UPDATE "%s" SET ' % self.db_table
        qs += ','.join(fields)
        qs += """ WHERE "id" = '%s'""" % obj.id
        if calculated:
            qs += ' RETURNING '
            calc_values = ['"%s"' % p.name for p in calculated]
            qs += ','.join(calc_values)
        qs += ';'
        return qs, values

    def _get_sql(self, mapping=None):
        print '_get_sql'
        sql = None
        if self.sql_dir:
            path = os.path.join(self.sql_dir, self.cls.__name__ + '.sql')
            print path
            if os.path.isfile(path):
                fp = open(path)
                sql = fp.read()
                fp.close()
                t = string.Template(sql)
                sql = t.safe_substitute(mapping)
        return sql

    def start_transaction(self):
        print 'start_transaction'
        self.in_transaction = True

    def end_transaction(self):
        print 'end_transaction'
        self.in_transaction = False
        self.commit()

    def commit(self):
        if not self.in_transaction:
            print '!!commit on %s' % self.db_table
            try:
                self.connection.commit()
                
            except psycopg2.ProgrammingError, err:
                self.connection.rollback()
                raise err

    def rollback(self):
        print '!!rollback on %s' % self.db_table
        self.connection.rollback()

    def delete_table(self):
        self.cursor.execute('DROP TABLE "%s";' % self.db_table)
        self.commit()

    def create_table(self, mapping=None):
        self.cursor.execute(self._get_sql(mapping))
        self.commit()

    def encode_value(self, prop, value):
        return self.converter.encode_prop(prop, value)

    def decode_value(self, prop, value):
        return self.converter.decode_prop(prop, value)

    def execute_sql(self, query):
        self.cursor.execute(query, None)
        self.commit()

    def query_sql(self, query, vars=None):
        self.cursor.execute(query, vars)
        return self.cursor.fetchall()

    def lookup(self, cls, name, value):
        values = []
        qs = 'SELECT * FROM "%s" WHERE ' % self.db_table
        found = False
        for property in cls.properties(hidden=False):
            if property.name == name:
                found = True
                value = self.encode_value(property, value)
                values.append(value)
                qs += "%s=" % name
                qs += "%s"
        if not found:
            raise SDBPersistenceError('%s is not a valid field' % name)
        qs += ';'
        print qs
        self.cursor.execute(qs, values)
        if self.cursor.rowcount == 1:
            row = self.cursor.fetchone()
            return self._object_from_row(row, self.cursor.description)
        elif self.cursor.rowcount == 0:
            raise KeyError, 'Object not found'
        else:
            raise LookupError, 'Multiple Objects Found'

    def query(self, cls, filters, limit=None, order_by=None):
        parts = []
        qs = 'SELECT * FROM "%s"' % self.db_table
        if filters:
            qs += ' WHERE '
            properties = cls.properties(hidden=False)
            for filter, value in filters:
                name, op = filter.strip().split()
                found = False
                for property in properties:
                    if property.name == name:
                        found = True
                        value = self.encode_value(property, value)
                        parts.append(""""%s"%s'%s'""" % (name, op, value))
                if not found:
                    raise SDBPersistenceError('%s is not a valid field' % name)
            qs += ','.join(parts)
        qs += ';'
        print qs
        cursor = self.connection.cursor()
        cursor.execute(qs)
        return self._object_lister(cursor)

    def get_property(self, prop, obj, name):
        qs = """SELECT "%s" FROM "%s" WHERE id='%s';""" % (name, self.db_table, obj.id)
        print qs
        self.cursor.execute(qs, None)
        if self.cursor.rowcount == 1:
            rs = self.cursor.fetchone()
            for prop in obj.properties(hidden=False):
                if prop.name == name:
                    v = self.decode_value(prop, rs[0])
                    return v
        raise AttributeError, '%s not found' % name

    def set_property(self, prop, obj, name, value):
        pass
        value = self.encode_value(prop, value)
        qs = 'UPDATE "%s" SET ' % self.db_table
        qs += "%s='%s'" % (name, self.encode_value(prop, value))
        qs += " WHERE id='%s'" % obj.id
        qs += ';'
        print qs
        self.cursor.execute(qs)
        self.commit()

    def get_object(self, cls, id):
        qs = """SELECT * FROM "%s" WHERE id='%s';""" % (self.db_table, id)
        self.cursor.execute(qs, None)
        if self.cursor.rowcount == 1:
            row = self.cursor.fetchone()
            return self._object_from_row(row, self.cursor.description)
        else:
            raise SDBPersistenceError('%s object with id=%s does not exist' % (cls.__name__, id))
        
    def get_object_from_id(self, id):
        return self.get_object(self.cls, id)

    def _find_calculated_props(self, obj):
        return [p for p in obj.properties() if hasattr(p, 'calculated_type')]

    def save_object(self, obj, expected_value=None):
        obj._auto_update = False
        calculated = self._find_calculated_props(obj)
        if not obj.id:
            obj.id = str(uuid.uuid4())
            qs, values = self._build_insert_qs(obj, calculated)
        else:
            qs, values = self._build_update_qs(obj, calculated)
        print qs
        self.cursor.execute(qs, values)
        if calculated:
            calc_values = self.cursor.fetchone()
            print calculated
            print calc_values
            for i in range(0, len(calculated)):
                prop = calculated[i]
                prop._set_direct(obj, calc_values[i])
        self.commit()

    def delete_object(self, obj):
        qs = """DELETE FROM "%s" WHERE id='%s';""" % (self.db_table, obj.id)
        print qs
        self.cursor.execute(qs)
        self.commit()

            
