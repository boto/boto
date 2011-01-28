# Copyright (c) 2010 Chris Moyer http://coredumped.org/
# All rights reserved.
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
An individual record set.
"""

class Record(object):
    XMLBody = """<ResourceRecordSet>
        <Name>%(name)s</Name>
        <Type>%(type)s</Type>
        <TTL>%(ttl)s</TTL>
        <ResourceRecords>
            <ResourceRecord>
                <Value>%(value)s</Value>
            </ResourceRecord>
        </ResourceRecords>
    </ResourceRecordSet>"""

    def __init__(self, connection=None, name=None, type=None, ttl=600, value=''):
        """
        Init method to create a new Record for Route 53.

        :type connection: :class:`boto.route53.Route53Connection`
        :param connection: Optional connection object. If this isn't given and
                           you attempt to delete or modify the record, then
                           a connection will attempt to be obtained.

        :type name: string
        :param name: The name you wish to perform the action on.

        :type type: string
        :param type: The type of record.

        :type ttl: int
        :param ttl: Optional TTL for the record.

        :type value: string
        :param value: Optional value for the record.
        """
        self.connection = connection
        self.name = name
        self.type = type
        self.ttl = ttl
        self.value = value

    def __repr__(self):
        return "%s %s %s" % (self.name, self.type, self.value)

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'Name':
            self.name = value
        elif name == 'Type':
            self.type = value
        elif name == 'TTL':
            self.ttl = value
        elif name == 'Value':
            self.value = value
        else:
            setattr(self, name, value)

    def to_xml(self):
        """
        Returns the XML representation for this record.

        :rtype: string
        :returns: The XML representation for this record.
        """
        params = {
            "name": self.name,
            "type": self.type,
            "ttl": self.ttl,
            "value": self.value
        }
        return self.XMLBody % params
