# Copyright (c) 2006-2012 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.
# All Rights Reserved
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


class LbTagSet(dict):
    """
    A TagSet is used to collect the tags associated with a particular
    Load Balancer instance.
    """

    def __init__(self, connection=None):
        self.connection = connection
        self._current_key = None
        self._current_value = None
        self._tags_tag = False

    def startElement(self, name, attrs, connection):
        if name == 'Tags' :
            self._tags_tag = True
        elif name == 'member' and self._tags_tag == True:
            self._current_key = None
            self._current_value = None

    def endElement(self, name, value, connection):
        if name == 'Key':
            self._current_key = value
        elif name == 'Value':
            self._current_value = value
        elif name == 'member' and self._tags_tag == True:
            self[self._current_key] = self._current_value
        elif name == 'Tags':
            self._tags_tag = False
