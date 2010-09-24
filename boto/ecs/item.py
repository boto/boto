# Copyright (c) 2010 Chris Moyer http://coredumped.org/
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

class Item(object):
    """A single Item"""

    def __init__(self, connection=None):
        """Initialize this Item"""
        self.connection = connection

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.__dict__)


    #
    # XML Parser functions
    #
    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        setattr(self, name, value)

class ItemSet(object):
    """
    The ItemSet is strongly based off of the ResultSet, but has
    slightly different functionality, specifically for the paging mechanism
    that ECS uses (which is page-based, instead of token-based)
    """

    def __init__(self, connection, action, params, marker_elem=None, page=0):
        self.objs = []
        self.iter = None
        self.page = page
        self.connection = connection
        self.action = action
        self.params = params
        if isinstance(marker_elem, list):
            self.markers = marker_elem
        else:
            self.markers = [marker_elem]

    def startElement(self, name, attrs, connection):
        for t in self.markers:
            if name == t[0]:
                obj = t[1](connection)
                self.objs.append(obj)
                return obj
        return None

    def endElement(self, name, value, connection):
        if name == 'TotalResults':
            self.total_results = value
        elif name == 'TotalPages':
            self.total_pages = value
        else:
            setattr(self, name, value)

    def next(self):
        """Special paging functionality"""
        if self.iter == None:
            self.iter = iter(self.objs)
        try:
            return self.iter.next()
        except StopIteration:
            self.iter = None
            self.objs = []
            if int(self.page) < int(self.total_pages):
                self.page += 1
                self.connection.get_response(self.action, self.params, self.page, self)
                return self.next()
            else:
                raise

    def __iter__(self):
        return self
