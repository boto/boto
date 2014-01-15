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

class LogFile(object):

    def __init__(self, connection=None):
        self.connection = connection
        self.size = None
        self.logfilename = None
        self.lastwritten = None
        
    def __repr__(self):
        #return '(%s, %s, %s)' % (self.logfilename, self.size, self.lastwritten)
        return '%s' % (self.logfilename)
        #return '' 

    def startElement(self, name, attrs, connection):
        #print "startElement : {0}".format(name)
        #print "startElement connection {0}".format(connection)
        #if name == 'DescribeDBLogFilesDetails':
        ##print name
        ##if name == 'DescribeDBLogFiles':
        #    #print "LogFile EQ : {0}".format(name)
        #    #print "Handling the self {0}".format(self)
        #    #print "values {0}".format(dir(self))
        #    #print "the name is {0}".format(self.LogFileName)
        #    #print "attrs is {0}".format(attrs)
        #    details = FileDetails(self)
        #    #print "NOW DEALINGS : {0}".format(details)
        #    #print "DescribeDBLogFilesDetails attrs {0}".format(attrs)
        #else:
            #print " ####", name, "####", attrs
        #    pass
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
        #print "{0} size is {1}, last write {2}".format(self.logfilename, self.size, self.lastwritten)
        #print "endElement :%s ----> %s" %(name, value)
        #setattr(self, name, value)
        #pass
        
class FileDetails(object):

    def __init__(self, connection=None):
        self.connection = connection
        self.size = None
        self.logfilename = None
        self.lastwritten = None
        
    def __repr__(self):
        return '"%s"' % self.logfilename

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        #print "$$$$in place", name
        if name == 'LastWritten':
            self.lastwritten = value
        elif name == 'LogFileName':
            self.logfilename = value
        elif name == 'Size':
            self.size = value
        else:
            setattr(self, name, value)
