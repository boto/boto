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
    <ChangeResourceRecordSetsRequest xmlns="https://route53.amazonaws.com/doc/2011-05-05/">
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

    def add_change(self, action, name, type, ttl=600,
            alias_hosted_zone_id=None, alias_dns_name=None, identifier=None,
            weight=None):
        """Add a change request"""
        change = Record(name, type, ttl,
                alias_hosted_zone_id=alias_hosted_zone_id,
                alias_dns_name=alias_dns_name, identifier=identifier,
                weight=weight)
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
        %(weight)s
        %(body)s
    </ResourceRecordSet>"""

    WRRBody = """
        <SetIdentifier>%(identifier)s</SetIdentifier>
        <Weight>%(weight)s</Weight>
    """

    ResourceRecordsBody = """
        <TTL>%(ttl)s</TTL>
        <ResourceRecords>
            %(records)s
        </ResourceRecords>"""

    ResourceRecordBody = """<ResourceRecord>
        <Value>%s</Value>
    </ResourceRecord>"""

    AliasBody = """<AliasTarget>
        <HostedZoneId>%s</HostedZoneId>
        <DNSName>%s</DNSName>
    </AliasTarget>"""



    def __init__(self, name=None, type=None, ttl=600, resource_records=None,
            alias_hosted_zone_id=None, alias_dns_name=None, identifier=None,
            weight=None):
        self.name = name
        self.type = type
        self.ttl = ttl
        if resource_records == None:
            resource_records = []
        self.resource_records = resource_records
        self.alias_hosted_zone_id = alias_hosted_zone_id
        self.alias_dns_name = alias_dns_name
        self.identifier = identifier
        self.weight = weight

    def add_value(self, value):
        """Add a resource record value"""
        self.resource_records.append(value)

    def set_alias(self, alias_hosted_zone_id, alias_dns_name):
        """Make this an alias resource record set"""
        self.alias_hosted_zone_id = alias_hosted_zone_id
        self.alias_dns_name = alias_dns_name

    def to_xml(self):
        """Spit this resource record set out as XML"""
        if self.alias_hosted_zone_id != None and self.alias_dns_name != None:
            # Use alias
            body = self.AliasBody % (self.alias_hosted_zone_id, self.alias_dns_name)
        else:
            # Use resource record(s)
            records = ""
            for r in self.resource_records:
                records += self.ResourceRecordBody % r
            body = self.ResourceRecordsBody % {
                "ttl": self.ttl,
                "records": records,
            }
        weight = ""
        if self.identifier != None and self.weight != None:
            weight = self.WRRBody % {"identifier": self.identifier, "weight":
                    self.weight}
        params = {
            "name": self.name,
            "type": self.type,
            "weight": weight,
            "body": body,
        }
        return self.XMLBody % params

    def to_print(self):
        rr = ""
        if self.alias_hosted_zone_id != None and self.alias_dns_name != None:
            # Show alias
            rr = 'ALIAS ' + self.alias_hosted_zone_id + ' ' + self.alias_dns_name
        else:
            # Show resource record(s)
            rr =  ",".join(self.resource_records)

        if self.identifier != None and self.weight != None:
            rr += ' (WRR id=%s, w=%s)' % (self.identifier, self.weight)

        return rr

    def endElement(self, name, value, connection):
        if name == 'Name':
            self.name = value
        elif name == 'Type':
            self.type = value
        elif name == 'TTL':
            self.ttl = value
        elif name == 'Value':
            self.resource_records.append(value)
        elif name == 'HostedZoneId':
            self.alias_hosted_zone_id = value
        elif name == 'DNSName':
            self.alias_dns_name = value
        elif name == 'SetIdentifier':
            self.identifier = value
        elif name == 'Weight':
            self.weight = value

    def startElement(self, name, attrs, connection):
        return None
