from boto.sdb.db.key import Key
import psycopg2
import uuid

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
        self.conn = None
        self.connect()

    class Converter:
        """
        Responsible for converting base Python types to format compatible with
        underlying database.
        """

        @classmethod
        def encode(cls, manager, prop, value):
            if hasattr(prop, 'reference_class'):
                return cls.encode_reference(manager, value)
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

    def encode_value(self, prop, value):
        return self.Converter.encode(self, prop, value)

    def decode_value(self, prop, value):
        return self.Converter.decode(self, prop, value)

    def _build_connect_string(self):
        cs = 'dbname=%s user=%s password=%s host=%s port=%d'
        return cs % (self.db_name, self.db_user, self.db_passwd,
                     self.db_host, self.db_port)

    def connect(self):
        self.conn = psycopg2.connect(self._build_connect_string())
        self.cursor = self.conn.cursor()

    def get_object(self, id):
        qs = """SELECT * FROM "%s" WHERE id='%s';""" % (self.db_table, id)
        self.cursor.execute(qs, None)
        if self.cursor.rowcount == 1:
            obj = self.cls(id)
            obj._auto_update = False
            rs = self.cursor.fetchone()
            data = {}
            for i in range(0, len(rs)):
                data[self.cursor.description[i][0]] = rs[i]
            for prop in obj.properties(hidden=False):
                v = self.decode_value(prop, data[prop.name])
                setattr(obj, prop.name, v)
            obj._auto_update = True
            return obj
        else:
            raise SDBPersistenceError('%s object with id=%s does not exist' % (cls.__name__, id))
        
        
    def query(self, query, vars=None):
        self.cursor.execute(query, vars)
        return self.cursor.fetchall()

    def find(self, cls, **params):
        qs = 'SELECT * FROM "%s" WHERE ' % cls.table()
        selectors = ["%s='%s'" % (i[0], i[1]) for i in params.items()]
        qs += ','.join(selectors)
        print qs
        self.cursor.execute(qs)
        results = self.cursor.fetchall()
        objs = []
        for result in results:
            obj = cls()
            self._obj_from_result(obj, result)
            objs.append(obj)
        return objs

    def query(self, cls, filters):
        parts = []
        qs = 'SELECT * FROM "%s" WHERE ' % cls.table()
        properties = cls.properties()
        for filter, value in filters:
            name, op = filter.strip().split()
            found = False
            for property in properties:
                if property.name == name:
                    found = True
                    value = self.encode_value(property, value)
                    parts.append("%s%s'%s'" % (name, op, value))
            if not found:
                raise SDBPersistenceError('%s is not a valid field' % key)
        qs += ','.join(parts)
        results = self.cursor.fetchall()
        objs = []
        for result in results:
            obj = cls()
            self._obj_from_result(obj, result)
            objs.append(obj)
        return objs

    def _build_insert_qs(self, obj):
        fields = [p.name for p in obj.properties(hidden=False)]
        values = ["'%s'" % p.get_value_for_datastore(obj)
                  for p in obj.properties(hidden=False)]
        qs = 'INSERT INTO "%s" (id,' % self.db_table
        qs += ','.join(fields)
        qs += ") VALUES ('%s'," % obj.id
        qs += ','.join(values)
        qs += ')'
        return qs

    def get_property(self, prop, obj, name):
        qs = """SELECT %s FROM "%s" WHERE id='%s';""" % (name, self.db_table, id)
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
        print qs
        self.cursor.execute(qs)
        self.conn.commit()

    def save_object(self, obj):
        obj.id = str(uuid.uuid4())
        qs = self._build_insert_qs(obj)
        print qs
        self.cursor.execute(qs)
        self.conn.commit()

            
