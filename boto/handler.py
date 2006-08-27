# Copyright (c) 2006 Mitch Garnaat http://garnaat.org/
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

from boto.resultset import ResultSet
import xml.sax

class XmlHandler(xml.sax.ContentHandler):

    def __init__(self, parent, elements):
        self.rs = ResultSet()
        self.elements = elements
        self.nodes = [parent]
        self.current_text = ''

    def startElement(self, name, attrs):
        if name in self.elements.keys():
            node = self.elements[name](self.nodes[-1])
            self.nodes.append(node)

    def endElement(self, name):
        if name in self.elements.keys():
            node = self.nodes.pop()
            setattr(node, name, self.current_text)
            if len(self.nodes) == 1:
                self.rs.append(node)
        elif len(self.nodes) > 1:
            setattr(self.nodes[-1], name, self.current_text)
        else:
            setattr(self.rs, name, self.current_text)
        self.current_text = ''

    def characters(self, content):
        self.current_text += content
            

