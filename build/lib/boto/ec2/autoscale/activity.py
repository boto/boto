# Copyright (c) 2009 Reza Lotun http://reza.lotun.name/
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


class Activity(object):
    def __init__(self, connection=None):
        self.connection = connection
        self.start_time = None
        self.activity_id = None
        self.progress = None
        self.status_code = None
        self.cause = None
        self.description = None

    def __repr__(self):
        return 'Activity:%s status:%s progress:%s' % (self.description,
                                                      self.status_code,
                                                      self.progress)
    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'ActivityId':
            self.activity_id = value
        elif name == 'StartTime':
            self.start_time = value
        elif name == 'Progress':
            self.progress = value
        elif name == 'Cause':
            self.cause = value
        elif name == 'Description':
            self.description = value
        elif name == 'StatusCode':
            self.status_code = value
        else:
            setattr(self, name, value)

