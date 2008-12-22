# Copyright (c) 2006-2008 Mitch Garnaat http://garnaat.org/
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
from xml.dom.minidom import getDOMImplementation, parse, parseString

ISO8601 = '%Y-%m-%dT%H:%M:%SZ'

class XMLConverter:
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
        return '%d' % value

    def decode_int(self, value):
        return int(value)

    def encode_long(self, value):
        value = long(value)
        return '%d' % value

    def decode_long(self, value):
        return long(value)

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

class XMLManager(object):
    
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
        self.converter = XMLConverter(self)
        self._connect()

    def _connect(self):
        self.impl = getDOMImplementation()
        self.doc = self.impl.createDocument(None, 'objects', None)

    def new_doc(self):
        return self.impl.createDocument(None, 'objects', None)

    def _object_lister(self, cls, query_lister):
        pass

    def reset(self):
        self._connect()

    def get_doc(self):
        return self.doc
            
    def encode_value(self, prop, value):
        return self.converter.encode_prop(prop, value)

    def decode_value(self, prop, value):
        return self.converter.decode_prop(prop, value)

    def get_s3_connection(self):
        if not self.s3:
            self.s3 = boto.connect_s3(self.aws_access_key_id, self.aws_secret_access_key)
        return self.s3

    def get_text_value(self, parent_node):
        value = ''
        for node in parent_node.childNodes:
            if node.nodeType == node.TEXT_NODE:
                value += node.data
        return value

    def get_list(self, prop_node, item_type):
        values = []
        items_node = prop_node.getElementsByTagName('items')[0]
        for item_node in items_node.getElementsByTagName('item'):
            item_value = self.get_text_value(item_node)
            value = self.converter.decode(item_type, item_value)
            values.append(value)
        return values

    def get_object(self, cls, id, doc):
        obj_node = doc.getElementsByTagName('object')[0]
        if not cls:
            class_name = obj_node.getAttribute('class')
            cls = find_class(class_name)
        if not id:
            id = obj_node.getAttribute('id')
        obj = cls(id)
        obj._auto_update = False
        for prop_node in obj_node.getElementsByTagName('property'):
            prop_name = prop_node.getAttribute('name')
            prop = obj.find_property(prop_name)
            if prop.data_type != Key:
                if hasattr(prop, 'item_type'):
                    value = self.get_list(prop_node, prop.item_type)
                else:
                    prop_value = self.get_text_value(prop_node)
                    value = self.decode_value(prop, prop_value)
                    value = prop.make_value_from_datastore(value)
                setattr(obj, prop.name, value)
        obj._auto_update = True
        return obj
        
    def get_object_from_id(self, id):
        return self.get_object(None, id)

    def query(self, cls, filters, limit=None, order_by=None):
        raise NotImplementedError, "queries not supported in XML"

    def query_gql(self, query_string, *args, **kwds):
        raise NotImplementedError, "GQL queries not supported in XML"

    def save_list(self, doc, items, prop_node):
        items_node = doc.createElement('items')
        prop_node.appendChild(items_node)
        for item in items:
            item_node = doc.createElement('item')
            items_node.appendChild(item_node)
            text_node = doc.createTextNode(item)
            item_node.appendChild(text_node)

    def save_object(self, obj, doc=None):
        if not obj.id:
            obj.id = str(uuid.uuid4())
        if not doc:
            doc = self.doc
        obj_node = doc.createElement('object')
        obj_node.setAttribute('id', obj.id)
        obj_node.setAttribute('class', '%s.%s' % (obj.__class__.__module__,
                                                  obj.__class__.__name__))
        root = doc.documentElement
        root.appendChild(obj_node)
        for property in obj.properties(hidden=False):
            prop_node = doc.createElement('property')
            prop_node.setAttribute('name', property.name)
            prop_node.setAttribute('type', property.type_name)
            value = property.get_value_for_datastore(obj)
            if value is not None:
                value = self.encode_value(property, value)
                if isinstance(value, list):
                    self.save_list(doc, value, prop_node)
                else:
                    text_node = doc.createTextNode(value)
                    prop_node.appendChild(text_node)
            obj_node.appendChild(prop_node)

    def marshal_object(self, obj, doc=None):
        if not doc:
            doc = self.new_doc()
        self.save_object(obj, doc)
        return doc

    def unmarshal_object(self, fp):
        if isinstance(fp, str) or isinstance(fp, unicode):
            doc = parseString(fp)
        else:
            doc = parse(fp)
        return self.get_object(None, None, doc)

    def delete_object(self, obj):
        raise NotImplementedError, "delete not supported in XML"

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
        
