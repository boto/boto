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

class User:
    def __init__(self, parent=None, id='', display_name='', xml_attrs=None):
        if parent:
            parent.owner = self
        self.type = None
        if xml_attrs:
            if xml_attrs.has_key('xsi:type'):
                self.type = xml_attrs['xsi:type']
        self.id = id
        self.display_name = display_name

    # This allows the XMLHandler to set the attributes as they are named
    # in the XML response but have the capitalized names converted to
    # more conventional looking python variables names automatically
    def __setattr__(self, key, value):
        if key == 'DisplayName':
            self.__dict__['display_name'] = value
        elif key == 'ID':
            self.__dict__['id'] = value
        elif key == 'URI':
            self.__dict__['uri'] = value
        else:
            self.__dict__[key] = value

