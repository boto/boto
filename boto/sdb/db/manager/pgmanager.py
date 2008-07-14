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
import psycopg2
import uuid, sys, os

class PGManager(object):

    def __init__(self, cls, db_name, db_user, db_passwd,
                 db_host, db_port, db_table):
        self.cls = cls
        self.db_name = db_name
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_host = db_host
        self.db_port = db_port
        self.db_table = db_table
        self._connect()

    class Converter:
        """
        Responsible for converting base Python types to format compatible with
        underlying database.
        """

        @classmethod
        def encode(cls, manager, prop, value):
            if hasattr(prop, 'reference_class'):
                return cls.encode_reference(manager, value)
            if isinstance(value, list):
                s = "{"
                value = ['"%s"' % v for v in value]
                s += ','.join(value)
                s += "}"
                return s
            return value

        @classmethod
        def decode(cls, manager, prop, value):
            if isinstance(prop.data_type, Key):
                return cls.decode_reference(manager, value)
            return value

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
                raise ValueError, 'Unable to convert %s to Object' % str_value

    def _build_connect_string(self):
        cs = 'dbname=%s user=%s password=%s host=%s port=%d'
        return cs % (self.db_name, self.db_user, self.db_passwd,
                     self.db_host, self.db_port)

    def _connect(self):
        self.connection = psycopg2.connect(self._build_connect_string())
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

    def _object_from_row(self, row, description):
        d = self._dict_from_row(row, description)
        obj = self.cls(d['id'])
        obj._auto_update = False
        for prop in obj.properties(hidden=False):
            v = self.decode_value(prop, d[prop.name])
            setattr(obj, prop.name, v)
        obj._auto_update = True
        return obj

    def _build_insert_qs(self, obj):
        fields = ['"%s"' % p.name for p in obj.properties(hidden=False)]
        values = ["'%s'" % p.get_value_for_datastore(obj)
                  for p in obj.properties(hidden=False)]
        qs = 'INSERT INTO "%s" (id,' % self.db_table
        qs += ','.join(fields)
        qs += ") VALUES ('%s'," % obj.id
        qs += ','.join(values)
        qs += ');'
        return qs

    def _build_update_qs(self, obj):
        fields = [""""%s"='%s'""" % (p.name, p.get_value_for_datastore(obj))
                  for p in obj.properties(hidden=False)]
        qs = 'UPDATE "%s" SET ' % self.db_table
        qs += ','.join(fields)
        qs += """ WHERE "id" = '%s';""" % obj.id
        return qs

    def _get_ddl(self):
        m = sys.modules[self.cls.__module__]
        path = m.__file__
        path = os.path.split(path)[0]
        path = os.path.join(path, 'models')
        path = os.path.join(path, self.cls.__name__ + '.ddl')
        fp = open(path)
        ddl = fp.read()
        fp.close()
        return ddl

    def delete_table(self):
        self.cursor.execute('DROP TABLE "%s";' % self.db_table)
        self.cursor.commit()

    def create_table(self):
        self.cursor.execute(self._get_ddl())
        self.cursor.execute()

    def encode_value(self, prop, value):
        return self.Converter.encode(self, prop, value)

    def decode_value(self, prop, value):
        return self.Converter.decode(self, prop, value)

    def query_sql(self, query, vars=None):
        self.cursor.execute(query, vars)
        return self.cursor.fetchall()

    def lookup(self, cls, name, value):
        parts = []
        qs = 'SELECT * FROM "%s" WHERE ' % self.db_table
        found = False
        for property in cls.properties(hidden=False):
            if property.name == name:
                found = True
                value = self.encode_value(property, value)
                qs += "%s='%s'" % (name, value)
        if not found:
            raise SDBPersistenceError('%s is not a valid field' % key)
        qs += ';'
        print qs
        self.cursor.execute(qs)
        if self.cursor.rowcount == 1:
            row = self.cursor.fetchone()
            return self._object_from_row(row, self.cursor.description)
        elif self.cursor.rowcount == 0:
            raise KeyError, 'Object not found'
        else:
            raise LookupError, 'Multiple Objects Found'

    def query(self, cls, filters=None):
        parts = []
        qs = 'SELECT * FROM "%s"' % self.db_table
        if filters:
            qs += ' WHERE '
            properties = cls.properties()
            for filter, value in filters:
                name, op = filter.strip().split()
                found = False
                for property in properties:
                    if property.name == name:
                        found = True
                        value = self.encode_value(property, value)
                        parts.append(""""%s"%s'%s'""" % (name, op, value))
                if not found:
                    raise SDBPersistenceError('%s is not a valid field' % key)
            qs += ','.join(parts)
        qs += ';'
        print qs
        cursor = self.connection.cursor()
        cursor.execute(qs)
        return self._object_lister(cursor)

    def get_property(self, prop, obj, name):
        qs = """SELECT "%s" FROM "%s" WHERE id='%s';""" % (name, self.db_table, id)
        self.cursor.execute(qs, None)
        if self.cursor.rowcount == 1:
            obj._auto_update = False
            rs = self.cursor.fetchone()
            for prop in obj.properties(hidden=False):
                if prop.name == name:
                    v = self.decode_value(prop, rs[0])
                    setattr(obj, prop.name, v)
            obj._auto_update = True
        else:
            raise SDBPersistenceError('%s object with id=%s does not exist' % (cls.__name__, id))

    def set_property(self, prop, obj, name, value):
        pass
        value = self.encode_value(prop, value)
        qs = 'UPDATE "%s" SET ' % self.db_table
        qs += "%s='%s'" % (name, self.encode_value(prop, value))
        qs += " WHERE id='%s'" % obj.id
        qs += ';'
        print qs
        self.cursor.execute(qs)
        self.connection.commit()

    def get_object(self, cls, id):
        qs = """SELECT * FROM "%s" WHERE id='%s';""" % (self.db_table, id)
        self.cursor.execute(qs, None)
        if self.cursor.rowcount == 1:
            row = self.cursor.fetchone()
            return self._object_from_row(row, self.cursor.description)
        else:
            raise SDBPersistenceError('%s object with id=%s does not exist' % (cls.__name__, id))
        
    def save_object(self, obj):
        obj._auto_update = False
        if not obj.id:
            obj.id = str(uuid.uuid4())
            qs = self._build_insert_qs(obj)
        else:
            qs = self._build_update_qs(obj)
        print qs
        self.cursor.execute(qs)
        self.connection.commit()
        obj._auto_update = True

    def delete_object(self, obj):
        qs = """DELETE FROM "%s" WHERE id='%s';""" % (self.db_table, obj.id)
        print qs
        self.cursor.execute(qs)
        self.connection.commit()

            
