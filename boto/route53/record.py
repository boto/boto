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

RECORD_TYPES = ['A', 'AAAA', 'TXT', 'CNAME', 'MX', 'PTR', 'SRV', 'SPF']

from boto.resultset import ResultSet
class ResourceRecordSets(ResultSet):

    ChangeResourceRecordSetsBody = """<?xml version="1.0" encoding="UTF-8"?>
    <ChangeResourceRecordSetsRequest xmlns="https://route53.amazonaws.com/doc/2010-10-01/">
            <ChangeBatch>
                <Comment>%(comment)s</Comment>
                <Changes>%(changes)s</Changes>
            </ChangeBatch>
        </ChangeResourceRecordSetsRequest>"""

    ChangeXML = """<Change>
        <Action>%(action)s</Action>
        %(record)s
    </Change>"""


    def __init__(self, connection=None, hosted_zone_id=None, comment=None):
        self.connection = connection
        self.hosted_zone_id = hosted_zone_id
        self.comment = comment
        self.changes = []
        self.next_record_name = None
        self.next_record_type = None
        ResultSet.__init__(self, [('ResourceRecordSet', Record)])

    def __repr__(self):
        return '<ResourceRecordSets: %s>' % self.hosted_zone_id

    def add_change(self, action, name, type, ttl=600):
        """Add a change request"""
        change = Record(name, type, ttl)
        self.changes.append([action, change])
        return change

    def to_xml(self):
        """Convert this ResourceRecordSet into XML
        to be saved via the ChangeResourceRecordSetsRequest"""
        changesXML = ""
        for change in self.changes:
            changeParams = {"action": change[0], "record": change[1].to_xml()}
            changesXML += self.ChangeXML % changeParams
        params = {"comment": self.comment, "changes": changesXML}
        return self.ChangeResourceRecordSetsBody % params

    def commit(self):
        """Commit this change"""
        if not self.connection:
            import boto
            self.connection = boto.connect_route53()
        return self.connection.change_rrsets(self.hosted_zone_id, self.to_xml())

    def endElement(self, name, value, connection):
        """Overwritten to also add the NextRecordName and 
        NextRecordType to the base object"""
        if name == 'NextRecordName':
            self.next_record_name = value
        elif name == 'NextRecordType':
            self.next_record_type = value
        else:
            return ResultSet.endElement(self, name, value, connection)

    def __iter__(self):
        """Override the next function to support paging"""
        results = ResultSet.__iter__(self)
        while results:
            for obj in results:
                yield obj
            if self.is_truncated:
                self.is_truncated = False
                results = self.connection.get_all_rrsets(self.hosted_zone_id, name=self.next_record_name, type=self.next_record_type)
            else:
                results = None



class Record(object):
    """An individual ResourceRecordSet"""

    XMLBody = """<ResourceRecordSet>
        <Name>%(name)s</Name>
        <Type>%(type)s</Type>
        <TTL>%(ttl)s</TTL>
        <ResourceRecords>%(records)s</ResourceRecords>
    </ResourceRecordSet>"""

    ResourceRecordBody = """<ResourceRecord>
        <Value>%s</Value>
    </ResourceRecord>"""


    def __init__(self, name=None, type=None, ttl=600, resource_records=None):
        self.name = name
        self.type = type
        self.ttl = ttl
        if resource_records == None:
            resource_records = []
        self.resource_records = resource_records
    
    def add_value(self, value):
        """Add a resource record value"""
        self.resource_records.append(value)

    def to_xml(self):
        """Spit this resource record set out as XML"""
        records = ""
        for r in self.resource_records:
            records += self.ResourceRecordBody % r
        params = {
            "name": self.name,
            "type": self.type,
            "ttl": self.ttl,
            "records": records
        }
        return self.XMLBody % params

    def endElement(self, name, value, connection):
        if name == 'Name':
            self.name = value
        elif name == 'Type':
            self.type = value
        elif name == 'TTL':
            self.ttl = value
        elif name == 'Value':
            self.resource_records.append(value)

    def startElement(self, name, attrs, connection):
        return None
