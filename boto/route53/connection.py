# Copyright (c) 2006-2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010, Eucalyptus Systems, Inc.
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
#

import copy
import xml.sax
import uuid
import urllib
import boto
from boto.connection import AWSAuthConnection
from boto import handler
from boto.exception import TooManyRecordsException
from boto.route53.record import ResourceRecordSets
import boto.jsonresponse
import exception

HZXML = """<?xml version="1.0" encoding="UTF-8"?>
<CreateHostedZoneRequest xmlns="%(xmlns)s">
  <Name>%(name)s</Name>
  <CallerReference>%(caller_ref)s</CallerReference>
  <HostedZoneConfig>
    <Comment>%(comment)s</Comment>
  </HostedZoneConfig>
</CreateHostedZoneRequest>"""

#boto.set_stream_logger('dns')


class Route53Connection(AWSAuthConnection):
    DefaultHost = 'route53.amazonaws.com'
    """The default Route53 API endpoint to connect to."""

    Version = '2012-02-29'
    """Route53 API version."""

    XMLNameSpace = 'https://route53.amazonaws.com/doc/2012-02-29/'
    """XML schema for this Route53 API version."""

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 port=None, proxy=None, proxy_port=None,
                 host=DefaultHost, debug=0, security_token=None,
                 validate_certs=True):
        AWSAuthConnection.__init__(self, host,
                                   aws_access_key_id, aws_secret_access_key,
                                   True, port, proxy, proxy_port, debug=debug,
                                   security_token=security_token,
                                   validate_certs=validate_certs)

    def _required_auth_capability(self):
        return ['route53']

    def make_request(self, action, path, headers=None, data='', params=None):
        if params:
            pairs = []
            for key, val in params.iteritems():
                if val is None:
                    continue
                pairs.append(key + '=' + urllib.quote(str(val)))
            path += '?' + '&'.join(pairs)
        return AWSAuthConnection.make_request(self, action, path,
                                              headers, data)

    # Hosted Zones

    def get_all_hosted_zones(self, start_marker=None, zone_list=None):
        """
        Returns a Python data structure with information about all
        Hosted Zones defined for the AWS account.

        :param int start_marker: start marker to pass when fetching additional
            results after a truncated list
        :param list zone_list: a HostedZones list to prepend to results
        """
        params = {}
        if start_marker:
            params = {'marker': start_marker}
        response = self.make_request('GET', '/%s/hostedzone' % self.Version,
                params=params)
        body = response.read()
        boto.log.debug(body)
        if response.status >= 300:
            raise exception.DNSServerError(response.status,
                                           response.reason,
                                           body)
        e = boto.jsonresponse.Element(list_marker='HostedZones',
                                      item_marker=('HostedZone',))
        h = boto.jsonresponse.XmlHandler(e, None)
        h.parse(body)
        if zone_list:
            e['ListHostedZonesResponse']['HostedZones'].extend(zone_list)
        while 'NextMarker' in e['ListHostedZonesResponse']:
            next_marker = e['ListHostedZonesResponse']['NextMarker']
            zone_list = e['ListHostedZonesResponse']['HostedZones']
            e = self.get_all_hosted_zones(next_marker, zone_list)
        return e

    def get_hosted_zone(self, hosted_zone_id):
        """
        Get detailed information about a particular Hosted Zone.

        :type hosted_zone_id: str
        :param hosted_zone_id: The unique identifier for the Hosted Zone

        """
        uri = '/%s/hostedzone/%s' % (self.Version, hosted_zone_id)
        response = self.make_request('GET', uri)
        body = response.read()
        boto.log.debug(body)
        if response.status >= 300:
            raise exception.DNSServerError(response.status,
                                           response.reason,
                                           body)
        e = boto.jsonresponse.Element(list_marker='NameServers',
                                      item_marker=('NameServer',))
        h = boto.jsonresponse.XmlHandler(e, None)
        h.parse(body)
        return e

    def get_hosted_zone_by_name(self, hosted_zone_name):
        """
        Get detailed information about a particular Hosted Zone.

        :type hosted_zone_name: str
        :param hosted_zone_name: The fully qualified domain name for the Hosted
        Zone

        """
        if hosted_zone_name[-1] != '.':
            hosted_zone_name += '.'
        all_hosted_zones = self.get_all_hosted_zones()
        for zone in all_hosted_zones['ListHostedZonesResponse']['HostedZones']:
            #check that they gave us the FQDN for their zone
            if zone['Name'] == hosted_zone_name:
                return self.get_hosted_zone(zone['Id'].split('/')[-1])

    def create_hosted_zone(self, domain_name, caller_ref=None, comment=''):
        """
        Create a new Hosted Zone.  Returns a Python data structure with
        information about the newly created Hosted Zone.

        :type domain_name: str
        :param domain_name: The name of the domain. This should be a
            fully-specified domain, and should end with a final period
            as the last label indication.  If you omit the final period,
            Amazon Route 53 assumes the domain is relative to the root.
            This is the name you have registered with your DNS registrar.
            It is also the name you will delegate from your registrar to
            the Amazon Route 53 delegation servers returned in
            response to this request.A list of strings with the image
            IDs wanted.

        :type caller_ref: str
        :param caller_ref: A unique string that identifies the request
            and that allows failed CreateHostedZone requests to be retried
            without the risk of executing the operation twice.  If you don't
            provide a value for this, boto will generate a Type 4 UUID and
            use that.

        :type comment: str
        :param comment: Any comments you want to include about the hosted
            zone.

        """
        if caller_ref is None:
            caller_ref = str(uuid.uuid4())
        params = {'name': domain_name,
                  'caller_ref': caller_ref,
                  'comment': comment,
                  'xmlns': self.XMLNameSpace}
        xml_body = HZXML % params
        uri = '/%s/hostedzone' % self.Version
        response = self.make_request('POST', uri,
                                     {'Content-Type': 'text/xml'}, xml_body)
        body = response.read()
        boto.log.debug(body)
        if response.status == 201:
            e = boto.jsonresponse.Element(list_marker='NameServers',
                                          item_marker=('NameServer',))
            h = boto.jsonresponse.XmlHandler(e, None)
            h.parse(body)
            return e
        else:
            raise exception.DNSServerError(response.status,
                                           response.reason,
                                           body)

    def delete_hosted_zone(self, hosted_zone_id):
        uri = '/%s/hostedzone/%s' % (self.Version, hosted_zone_id)
        response = self.make_request('DELETE', uri)
        body = response.read()
        boto.log.debug(body)
        if response.status not in (200, 204):
            raise exception.DNSServerError(response.status,
                                           response.reason,
                                           body)
        e = boto.jsonresponse.Element()
        h = boto.jsonresponse.XmlHandler(e, None)
        h.parse(body)
        return e

    # Resource Record Sets

    def get_all_rrsets(self, hosted_zone_id, type=None,
                       name=None, identifier=None, maxitems=None):
        """
        Retrieve the Resource Record Sets defined for this Hosted Zone.
        Returns the raw XML data returned by the Route53 call.

        :type hosted_zone_id: str
        :param hosted_zone_id: The unique identifier for the Hosted Zone

        :type type: str
        :param type: The type of resource record set to begin the record
            listing from.  Valid choices are:

                * A
                * AAAA
                * CNAME
                * MX
                * NS
                * PTR
                * SOA
                * SPF
                * SRV
                * TXT

            Valid values for weighted resource record sets:

                * A
                * AAAA
                * CNAME
                * TXT

            Valid values for Zone Apex Aliases:

                * A
                * AAAA

        :type name: str
        :param name: The first name in the lexicographic ordering of domain
                     names to be retrieved

        :type identifier: str
        :param identifier: In a hosted zone that includes weighted resource
            record sets (multiple resource record sets with the same DNS
            name and type that are differentiated only by SetIdentifier),
            if results were truncated for a given DNS name and type,
            the value of SetIdentifier for the next resource record
            set that has the current DNS name and type

        :type maxitems: int
        :param maxitems: The maximum number of records

        """
        params = {'type': type, 'name': name,
                  'Identifier': identifier, 'maxitems': maxitems}
        uri = '/%s/hostedzone/%s/rrset' % (self.Version, hosted_zone_id)
        response = self.make_request('GET', uri, params=params)
        body = response.read()
        boto.log.debug(body)
        if response.status >= 300:
            raise exception.DNSServerError(response.status,
                                           response.reason,
                                           body)
        rs = ResourceRecordSets(connection=self, hosted_zone_id=hosted_zone_id)
        h = handler.XmlHandler(rs, self)
        xml.sax.parseString(body, h)
        return rs

    def change_rrsets(self, hosted_zone_id, xml_body):
        """
        Create or change the authoritative DNS information for this
        Hosted Zone.
        Returns a Python data structure with information about the set of
        changes, including the Change ID.

        :type hosted_zone_id: str
        :param hosted_zone_id: The unique identifier for the Hosted Zone

        :type xml_body: str
        :param xml_body: The list of changes to be made, defined in the
            XML schema defined by the Route53 service.

        """
        uri = '/%s/hostedzone/%s/rrset' % (self.Version, hosted_zone_id)
        response = self.make_request('POST', uri,
                                     {'Content-Type': 'text/xml'},
                                     xml_body)
        body = response.read()
        boto.log.debug(body)
        if response.status >= 300:
            raise exception.DNSServerError(response.status,
                                           response.reason,
                                           body)
        e = boto.jsonresponse.Element()
        h = boto.jsonresponse.XmlHandler(e, None)
        h.parse(body)
        return e

    def get_change(self, change_id):
        """
        Get information about a proposed set of changes, as submitted
        by the change_rrsets method.
        Returns a Python data structure with status information about the
        changes.

        :type change_id: str
        :param change_id: The unique identifier for the set of changes.
            This ID is returned in the response to the change_rrsets method.

        """
        uri = '/%s/change/%s' % (self.Version, change_id)
        response = self.make_request('GET', uri)
        body = response.read()
        boto.log.debug(body)
        if response.status >= 300:
            raise exception.DNSServerError(response.status,
                                           response.reason,
                                           body)
        e = boto.jsonresponse.Element()
        h = boto.jsonresponse.XmlHandler(e, None)
        h.parse(body)
        return e

    def create_zone(self, name):
        """
        Create a new Hosted Zone.  Returns a Zone object for the newly
        created Hosted Zone.

        :type name: str
        :param name: The name of the domain. This should be a
            fully-specified domain, and should end with a final period
            as the last label indication.  If you omit the final period,
            Amazon Route 53 assumes the domain is relative to the root.
            This is the name you have registered with your DNS registrar.
            It is also the name you will delegate from your registrar to
            the Amazon Route 53 delegation servers returned in
            response to this request.
        """
        zone = self.create_hosted_zone(name)
        return Zone(self, zone['CreateHostedZoneResponse']['HostedZone'])

    def get_zone(self, name):
        """
        Returns a Zone object for the specified Hosted Zone.

        :param name: The name of the domain. This should be a
            fully-specified domain, and should end with a final period
            as the last label indication.
        """
        name = self._make_qualified(name)
        for zone in self.get_zones():
            if name == zone.name:
                return zone

    def get_zones(self):
        """
        Returns a list of Zone objects, one for each of the Hosted
        Zones defined for the AWS account.
        """
        zones = self.get_all_hosted_zones()
        return [Zone(self, zone) for zone in
                zones['ListHostedZonesResponse']['HostedZones']]

    def _make_qualified(self, value):
        """
        Ensure passed domain names end in a period (.) character.
        This will usually make a domain fully qualified.
        """
        if type(value) in [list, tuple, set]:
            new_list = []
            for record in value:
                if record and not record[-1] == '.':
                    new_list.append("%s." % record)
                else:
                    new_list.append(record)
            return new_list
        else:
            value = value.strip()
            if value and not value[-1] == '.':
                value = "%s." % value
            return value

default_ttl = 60


class Zone(object):
    """
    A Route53 Zone.

    :ivar Route53Connection route53connection
    :ivar str Id: The ID of the hosted zone.
    """
    def __init__(self, route53connection, zone_dict):
        self.route53connection = route53connection
        for key in zone_dict:
            if key == 'Id':
                self.id = zone_dict['Id'].replace('/hostedzone/', '')
            else:
                self.__setattr__(key.lower(), zone_dict[key])

    def __repr__(self):
        return '<Zone:%s>' % self.name

    def _commit(self, changes):
        """
        Commit a set of changes and return the ChangeInfo portion of
        the response.

        :type changes: ResourceRecordSets
        :param changes: changes to be committed
        """
        response = changes.commit()
        return response['ChangeResourceRecordSetsResponse']['ChangeInfo']

    def _new_record(self, changes, resource_type, name, value, ttl, identifier,
                   comment=""):
        """
        Add a CREATE change record to an existing ResourceRecordSets

        :type changes: ResourceRecordSets
        :param changes: change set to append to

        :type name: str
        :param name: The name of the resource record you want to
            perform the action on.

        :type resource_type: str
        :param resource_type: The DNS record type

        :param value: Appropriate value for resource_type

        :type ttl: int
        :param ttl: The resource record cache time to live (TTL), in seconds.

        :type identifier: tuple
        :param identifier: A tuple for setting WRR or LBR attributes.  Valid
           forms are:

           * (str, int): WRR record [e.g. ('foo',10)]
           * (str, str): LBR record [e.g. ('foo','us-east-1')

        :type comment: str
        :param comment: A comment that will be stored with the change.
        """
        weight = None
        region = None
        if identifier is not None:
            try:
                int(identifier[1])
                weight = identifier[1]
                identifier = identifier[0]
            except:
                region = identifier[1]
                identifier = identifier[0]
        change = changes.add_change("CREATE", name, resource_type, ttl,
                                    identifier=identifier, weight=weight,
                                    region=region)
        if type(value) in [list, tuple, set]:
            for record in value:
                change.add_value(record)
        else:
            change.add_value(value)

    def add_record(self, resource_type, name, value, ttl=60, identifier=None,
                   comment=""):
        """
        Add a new record to this Zone.  See _new_record for parameter
        documentation.
        """
        changes = ResourceRecordSets(self.route53connection, self.id, comment)
        self._new_record(changes, resource_type, name, value, ttl, identifier,
                         comment)
        Status(self.route53connection, self._commit(changes))

    def update_record(self, old_record, new_value, new_ttl=None,
                      new_identifier=None, comment=""):
        """
        Update an existing record in this Zone.

        :type old_record: ResourceRecord
        :param old_record: A ResourceRecord (e.g. returned by find_records)

        See _new_record for additional parameter documentation.
        """
        new_ttl = new_ttl or default_ttl
        record = copy.copy(old_record)
        changes = ResourceRecordSets(self.route53connection, self.id, comment)
        changes.add_change_record("DELETE", record)
        self._new_record(changes, record.type, record.name,
                         new_value, new_ttl, new_identifier, comment)
        Status(self.route53connection, self._commit(changes))

    def delete_record(self, record, comment=""):
        """
        Delete one or more records from this Zone.

        :param record: A ResourceRecord (e.g. returned by
           find_records) or list, tuple, or set of ResourceRecords.

        :type comment: str
        :param comment: A comment that will be stored with the change.
        """
        changes = ResourceRecordSets(self.route53connection, self.id, comment)
        if type(record) in [list, tuple, set]:
            for r in record:
                changes.add_change_record("DELETE", r)
        else:
            changes.add_change_record("DELETE", record)
        Status(self.route53connection, self._commit(changes))

    def add_cname(self, name, value, ttl=None, identifier=None, comment=""):
        """
        Add a new CNAME record to this Zone.  See _new_record for
        parameter documentation.
        """
        ttl = ttl or default_ttl
        name = self.route53connection._make_qualified(name)
        value = self.route53connection._make_qualified(value)
        return self.add_record(resource_type='CNAME',
                               name=name,
                               value=value,
                               ttl=ttl,
                               identifier=identifier,
                               comment=comment)

    def add_a(self, name, value, ttl=None, identifier=None, comment=""):
        """
        Add a new A record to this Zone.  See _new_record for
        parameter documentation.
        """
        ttl = ttl or default_ttl
        name = self.route53connection._make_qualified(name)
        return self.add_record(resource_type='A',
                               name=name,
                               value=value,
                               ttl=ttl,
                               identifier=identifier,
                               comment=comment)

    def add_mx(self, name, records, ttl=None, identifier=None, comment=""):
        """
        Add a new MX record to this Zone.  See _new_record for
        parameter documentation.
        """
        ttl = ttl or default_ttl
        records = self.route53connection._make_qualified(records)
        return self.add_record(resource_type='MX',
                               name=name,
                               value=records,
                               ttl=ttl,
                               identifier=identifier,
                               comment=comment)

    def find_records(self, name, type, desired=1, all=False, identifier=None):
        """
        Search this Zone for records that match given parameters.
        Returns None if no results, a ResourceRecord if one result, or
        a ResourceRecordSets if more than one result.

        :type name: str
        :param name: The name of the records should match this parameter

        :type type: str
        :param type: The type of the records should match this parameter

        :type desired: int
        :param desired: The number of desired results.  If the number of
           matching records in the Zone exceeds the value of this parameter,
           throw TooManyRecordsException

        :type all: Boolean
        :param all: If true return all records that match name, type, and
          identifier parameters

        :type identifier: Tuple
        :param identifier: A tuple specifying WRR or LBR attributes.  Valid
           forms are:

           * (str, int): WRR record [e.g. ('foo',10)]
           * (str, str): LBR record [e.g. ('foo','us-east-1')

        """
        name = self.route53connection._make_qualified(name)
        returned = self.route53connection.get_all_rrsets(self.id, name=name,
                                                         type=type)

        # name/type for get_all_rrsets sets the starting record; they
        # are not a filter
        results = [r for r in returned if r.name == name and r.type == type]

        weight = None
        region = None
        if identifier is not None:
            try:
                int(identifier[1])
                weight = identifier[1]
            except:
                region = identifier[1]

        if weight is not None:
            results = [r for r in results if (r.weight == weight and
                                              r.identifier == identifier[0])]
        if region is not None:
            results = [r for r in results if (r.region == region and
                                              r.identifier == identifier[0])]

        if ((not all) and (len(results) > desired)):
            message = "Search: name %s type %s" % (name, type)
            message += "\nFound: "
            message += ", ".join(["%s %s %s" % (r.name, r.type, r.to_print())
                                  for r in results])
            raise TooManyRecordsException(message)
        elif len(results) > 1:
            return results
        elif len(results) == 1:
            return results[0]
        else:
            return None

    def get_cname(self, name, all=False):
        """
        Search this Zone for CNAME records that match name.

        Returns a ResourceRecord.

        If there is more than one match return all as a
        ResourceRecordSets if all is True, otherwise throws
        TooManyRecordsException.
        """
        return self.find_records(name, 'CNAME', all=all)

    def get_a(self, name, all=False):
        """
        Search this Zone for A records that match name.

        Returns a ResourceRecord.

        If there is more than one match return all as a
        ResourceRecordSets if all is True, otherwise throws
        TooManyRecordsException.
        """
        return self.find_records(name, 'A', all=all)

    def get_mx(self, name, all=False):
        """
        Search this Zone for MX records that match name.

        Returns a ResourceRecord.

        If there is more than one match return all as a
        ResourceRecordSets if all is True, otherwise throws
        TooManyRecordsException.
        """
        return self.find_records(name, 'MX', all=all)

    def update_cname(self, name, value, ttl=None, identifier=None, comment=""):
        """
        Update the given CNAME record in this Zone to a new value, ttl,
        and identifier.

        Will throw TooManyRecordsException is name, value does not match
        a single record.
        """
        name = self.route53connection._make_qualified(name)
        value = self.route53connection._make_qualified(value)
        old_record = self.get_cname(name)
        ttl = ttl or old_record.ttl
        return self.update_record(old_record,
                                  new_value=value,
                                  new_ttl=ttl,
                                  new_identifier=identifier,
                                  comment=comment)

    def update_a(self, name, value, ttl=None, identifier=None, comment=""):
        """
        Update the given A record in this Zone to a new value, ttl,
        and identifier.

        Will throw TooManyRecordsException is name, value does not match
        a single record.
        """
        name = self.route53connection._make_qualified(name)
        old_record = self.get_a(name)
        ttl = ttl or old_record.ttl
        return self.update_record(old_record,
                                  new_value=value,
                                  new_ttl=ttl,
                                  new_identifier=identifier,
                                  comment=comment)

    def update_mx(self, name, value, ttl=None, identifier=None, comment=""):
        """
        Update the given MX record in this Zone to a new value, ttl,
        and identifier.

        Will throw TooManyRecordsException is name, value does not match
        a single record.
        """
        name = self.route53connection._make_qualified(name)
        value = self.route53connection._make_qualified(value)
        old_record = self.get_mx(name)
        ttl = ttl or old_record.ttl
        return self.update_record(old_record,
                                  new_value=value,
                                  new_ttl=ttl,
                                  new_identifier=identifier,
                                  comment=comment)

    def delete_cname(self, name, identifier=None, all=False):
        """
        Delete a CNAME record matching name and identifier from
        this Zone.

        If there is more than one match delete all matching records if
        all is True, otherwise throws TooManyRecordsException.
        """
        name = self.route53connection._make_qualified(name)
        record = self.find_records(name, 'CNAME', identifier=identifier,
                                   all=all)
        return self.delete_record(record)

    def delete_a(self, name, identifier=None, all=False):
        """
        Delete an A record matching name and identifier from this
        Zone.

        If there is more than one match delete all matching records if
        all is True, otherwise throws TooManyRecordsException.
        """
        name = self.route53connection._make_qualified(name)
        record = self.find_records(name, 'A', identifier=identifier,
                                   all=all)
        return self.delete_record(record)

    def delete_mx(self, name, identifier=None, all=False):
        """
        Delete an MX record matching name and identifier from this
        Zone.

        If there is more than one match delete all matching records if
        all is True, otherwise throws TooManyRecordsException.
        """
        name = self.route53connection._make_qualified(name)
        record = self.find_records(name, 'MX', identifier=identifier,
                                   all=all)
        return self.delete_record(record)

    def get_records(self):
        """
        Return a ResourceRecordsSets for all of the records in this zone.
        """
        return self.route53connection.get_all_rrsets(self.id)

    def delete(self):
        """
        Request that this zone be deleted by Amazon.
        """
        self.route53connection.delete_hosted_zone(self.id)

    def get_nameservers(self):
        """ Get the list of nameservers for this zone."""
        ns = self.find_records(self.name, 'NS')
        if ns is not None:
            ns = ns.resource_records
        return ns


class Status(object):
    def __init__(self, route53connection, change_dict):
        self.route53connection = route53connection
        for key in change_dict:
            if key == 'Id':
                self.__setattr__(key.lower(),
                                 change_dict[key].replace('/change/', ''))
            else:
                self.__setattr__(key.lower(), change_dict[key])

    def update(self):
        """ Update the status of this request."""
        status = self.route53connection.get_change(self.id)['GetChangeResponse']['ChangeInfo']['Status']
        self.status = status
        return status

    def __repr__(self):
        return '<Status:%s>' % self.status
