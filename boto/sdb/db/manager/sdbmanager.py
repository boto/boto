# Copyright (c) 2006-2009 Mitch Garnaat http://garnaat.org/
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
import re
from boto.utils import find_class
import uuid
from boto.exception import SDBPersistenceError

class SDBManager(object):
    
    def __init__(self, domain_name=None, **kwargs):
        self.domain_name = domain_name
        self.kwargs = kwargs
        self.s3 = None
        self.sdb = None
        self.domain = None

    def __getitem__(self, key):
        obj = self.load_object(key)
        if not obj:
            raise KeyError
        return obj

    def __setitem__(self, key, value):
        self.save_object(value, key)

    def get_domain(self):
        if not self.domain:
            self.sdb = boto.connect_sdb(**self.kwargs)
            self.domain = self.sdb.lookup(self.domain_name, validate=False)
        return self.domain

    def get_s3_connection(self):
        if not self.s3:
            self.s3 = boto.connect_s3(**self.kwargs)
        return self.s3

    def _object_lister(self, cls, query_lister):
        for item in query_lister:
            obj = self.load_object(item.name, cls, item)
            if obj:
                yield obj
            
    def load_object(self, id, cls=None, attr=None):
        domain = self.get_domain()
        if not attr:
            attr = domain.get_attributes(id)
        if not cls or attr['__type__'] != cls.__name__:
            cls = find_class(attr['__module__'], attr['__type__'])
        if cls:
            params = {'manager' : self}
            for prop in cls.properties(hidden=False):
                if attr.has_key(prop.name):
                    value = prop.from_str(attr[prop.name])
                    params[prop.name] = value
            return cls(id, **params)
        else:
            return None

    def save_object(self, obj, id=None):
        if not obj.id:
            if not id:
                id = str(uuid.uuid4())
            obj.id = id

        attrs = {'__type__' : obj.__class__.__name__,
                 '__module__' : obj.__class__.__module__,
                 '__lineage__' : obj.get_lineage()}
        for property in obj.properties(hidden=False):
            value = property.to_str(getattr(obj, property.name))
            if value is not None:
                attrs[property.name] = value
            if property.unique:
                try:
                    args = {property.name: value}
                    obj2 = obj.find(**args).next()
                    if obj2.id != obj.id:
                        raise SDBPersistenceError("Error: %s must be unique!" % property.name)
                except(StopIteration):
                    pass
        domain = self.get_domain()
        domain.put_attributes(obj.id, attrs, replace=True)
        obj.manager = self
        return obj.id

    def delete_object(self, obj):
        domain = self.get_domain()
        domain.delete_attributes(obj.id)

    def get_raw_item(self, obj):
        domain = self.get_domain()
        return domain.get_item(obj.id)

    def query(self, cls, query, query_obj):
        domain = self.get_domain()
        rs = domain.connection.select(domain, query, query_obj.next_token)
        query_obj.next_token = rs.next_token
        return self._object_lister(cls, rs)
        
    def count(self, cls, query, query_obj):
        """
        Get the number of results that would
        be returned in this query
        """
        domain = self.get_domain()
        count =  int(domain.select(query).next()["Count"])
        return count


