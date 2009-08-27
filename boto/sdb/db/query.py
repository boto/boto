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

class Query(object):

    def __init__(self, model_class, manager):
        self.model_class = model_class
        self.manager = manager
        self.filters = []
        self.limit = None
        self.order_by = None
        self.next_token = None

    def __iter__(self):
        return self.run()

    def filter(self, property_operator, value):
        self.filters.append((property_operator, value))
        return self

    def count(self):
        return self.manager.count(self.model_class, self.filters, self.limit)

    def order(self, key):
        self.order_by = key
        return self

    def build_query(self, output_list='*'):
        query = "select %s from `%s`" % (output_list, self.manager.domain_name)
        query += self._build_filter_part()
        if self.limit:
            query += ' limit %d ' % self.limit
        return query
    
    def run(self):
        rs = self.manager.query(self.model_class, self.build_query(), self)
        return rs

    def count(self):
        """
        Get the number of results that would
        be returned in this query
        """
        return self.manager.count(self.model_class,
                                  self.build_query(output_list='count(*)'),
                                  self)

    def _build_filter_part(self):
        """
        Build the filter part
        """
        import types
        query_parts = []
        order_by_filtered = False
        if self.order_by:
            if self.order_by[0] == "-":
                order_by_method = "desc";
                order_by = order_by[1:]
            else:
                order_by_method = "asc";
                order_by = self.order_by

        for filter in self.filters:
            (name, op) = filter[0].strip().split(" ")
            value = filter[1]
            property = self.model_class.find_property(name)
            if not property:
                raise AttributeError("Unknown Property: %s" % name)
            if name == self.order_by:
                order_by_filtered = True
            if types.TypeType(value) == types.ListType:
                filter_parts = []
                for val in value:
                    val = property.to_str(val)
                    if isinstance(val, list):
                        for v in val:
                            filter_parts.append("`%s` %s '%s'" % (name, op, v.replace("'", "''")))
                    else:
                        filter_parts.append("`%s` %s '%s'" % (name, op, val.replace("'", "''")))
                query_parts.append("(%s)" % (" or ".join(filter_parts)))
            else:
                if op == 'is' and value == None:
                    query_parts.append("`%s` is null" % name)
                else:
                    val = property.to_str(value)
                    if isinstance(val, list):
                        for v in val:
                            query_parts.append("`%s` %s '%s'" % (name, op, v.replace("'", "''")))
                    else:
                        query_parts.append("`%s` %s '%s'" % (name, op, val.replace("'", "''")))

        type_query = "(`__type__` = '%s'" % self.model_class.__name__
        for subclass in self.model_class.__sub_classes__:
            type_query += " or `__type__` = '%s'" % subclass.__name__
        type_query +=")"
        query_parts.append(type_query)

        order_by_query = ""
        if self.order_by:
            if not order_by_filtered:
                query_parts.append("`%s` like '%%'" % order_by)
            order_by_query = " order by `%s` %s" % (order_by, order_by_method)

        if len(query_parts) > 0:
            return "where %s %s" % (" and ".join(query_parts), order_by_query)
        else:
            return ""
        
