# Copyright (c) 2006-2010 Chris Moyer http://coredumped.org/
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

import uuid
import urllib

class InvalidationBatch(object):
    """A simple invalidation request.
        :see: http://docs.amazonwebservices.com/AmazonCloudFront/2010-08-01/APIReference/index.html?InvalidationBatchDatatype.html
    """

    def __init__(self, paths=[], connection=None, distribution=None, caller_reference=''):
        """Create a new invalidation request:
            :paths: An array of paths to invalidate
        """
        self.paths = paths
        self.distribution = distribution
        self.caller_reference = caller_reference
        if not self.caller_reference:
            self.caller_reference = str(uuid.uuid4())

        # If we passed in a distribution,
        # then we use that as the connection object
        if distribution:
            self.connection = connection
        else:
            self.connection = connection

    def add(self, path):
        """Add another path to this invalidation request"""
        return self.paths.append(path)

    def remove(self, path):
        """Remove a path from this invalidation request"""
        return self.paths.remove(path)

    def __iter__(self):
        return iter(self.paths)

    def __getitem__(self, i):
        return self.paths[i]

    def __setitem__(self, k, v):
        self.paths[k] = v

    def escape(self, p):
        """Escape a path, make sure it begins with a slash and contains no invalid characters"""
        if not p[0] == "/":
            p = "/%s" % p
        return urllib.quote(p)

    def to_xml(self):
        """Get this batch as XML"""
        assert self.connection != None
        s = '<?xml version="1.0" encoding="UTF-8"?>\n'
        s += '<InvalidationBatch xmlns="http://cloudfront.amazonaws.com/doc/%s/">\n' % self.connection.Version
        for p in self.paths:
            s += '    <Path>%s</Path>\n' % self.escape(p)
        s += '    <CallerReference>%s</CallerReference>\n' % self.caller_reference
        s += '</InvalidationBatch>\n'
        return s

    def startElement(self, name, attrs, connection):
        if name == "InvalidationBatch":
            self.paths = []
        return None

    def endElement(self, name, value, connection):
        if name == 'Path':
            self.paths.append(value)
        elif name == "Status":
            self.status = value
        elif name == "Id":
            self.id = id
        elif name == "CreateTime":
            self.create_time = value
        elif name == "CallerReference":
            self.caller_reference = value
        return None
