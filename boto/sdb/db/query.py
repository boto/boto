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

class Query(object):

    def __init__(self, model_class, manager=None):
        self.model_class = model_class
        if manager:
            self.manager = manager
        else:
            self.manager = self.model_class._manager
        self.filters = []
        self.limit = None
        self.sort_by = None

    def __iter__(self):
        return iter(self.manager.query(self.model_class, self.filters, self.limit, self.sort_by))

    def next(self):
        return self.__iter__().next()

    def filter(self, property_operator, value):
        self.filters.append((property_operator, value))
        return self

    def fetch(self, limit, offset=0):
        raise NotImplementedError, "fetch mode is not currently supported"

    def count(self, limit):
        raise NotImplementedError, "count is not currently supported"

    def order(self, key):
        self.sort_by = key
        return self
