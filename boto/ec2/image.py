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
Represents an EC2 Image
"""

class Image:
    
    def __init__(self, connection=None):
        self.connection = connection
        self.id = None
        self.location = None
        self.state = None
        self.ownerId = None
        self.isPublic = False

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'imageId':
            self.id = value
        elif name == 'imageLocation':
            self.location = value
        elif name == 'imageState':
            self.state = value
        elif name == 'imageOwnerId':
            self.ownerId = value
        elif name == 'isPublic':
            self.is_public = bool(value)
        else:
            setattr(self, name, value)

    def run(self, min_count=1, max_count=1, key_name=None,
            security_groups=None, user_data=None):
        return self.connection.run_instances(self.id, min_count, max_count,
                                             key_name, security_groups,
                                             user_data)

    def deregister(self):
        return self.connection.deregister_image(self.id)

