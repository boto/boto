# Copyright (c) 2006-2009 Mitch Garnaat http://garnaat.org/
# 2014-01-15  Jumping Qu  @ BPO
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

class LogFile(object):

    def __init__(self, connection=None):
        self.connection = connection
        self.size = None
        self.logfilename = None
        self.lastwritten = None
        
    def __repr__(self):
        #return '(%s, %s, %s)' % (self.logfilename, self.size, self.lastwritten)
        return '%s' % (self.logfilename)

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'LastWritten':
            self.lastwritten = value
        elif name == 'LogFileName':
            self.logfilename = value
        elif name == 'Size':
            self.size = value
        else:
            setattr(self, name, value)
