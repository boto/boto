# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
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

class ResultSet:

    def __init__(self, marker_elem='', factory=None):
        self.marker_elem = marker_elem
        self.factory = factory
        self._results = []

    def startElement(self, name, attrs, connection):
        if name == self.marker_elem:
            obj = self.factory(connection)
            self._results.append(obj)
            return obj
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'IsTruncated':
            self.is_truncated = bool(value)
        elif name == 'Marker':
            self.marker = value
        elif name == 'Prefix':
            self.prefix = value
        elif name == 'return':
            self.status = bool(value)
        elif name == 'StatusCode':
            if (value == 'Success'):
                self.status = True
            else:
                self.status = False
        else:
            setattr(self, name, value)
        
    def __repr__(self):
        return repr(self._results)

    def __len__(self):
        return len(self._results)

    def __getitem__(self, key):
        return self._results[key]

    def append(self, value):
        self._results.append(value)

    def count(self):
        return self._results.count()

    def insert(self, value):
        self._results.insert(value)

    def pop(self):
        return self._results.pop()

    def __contains__(self, item):
        return item in self._results

