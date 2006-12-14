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

"""
Represents an EC2 Instance
"""

class Instance:
    
    def __init__(self, parent=None):
        self.id = None
        self.location = None
        self.state = None
        self.ownerId = None
        self.isPublic = False

    # This allows the XMLHandler to set the attributes as they are named
    # in the XML response but have the capitalized names converted to
    # more conventional looking python variables names automatically
    def __setattr__(self, key, value):
        if key == 'imageId':
            self.__dict__['id'] = value
        elif key == 'imageLocation':
            self.__dict__['location'] = value
        elif key == 'imageState':
            self.__dict__['state'] = value
        elif key == 'imageOwnerId':
            self.__dict__['ownerId'] = value
        elif key == 'isPublic':
            self.__dict__['ownerId'] = bool(value)
        else:
            self.__dict__[key] = value



