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

import xml.sax
import time
import uuid
import urllib
import boto
from boto.connection import AWSAuthConnection
from boto import handler
from boto.resultset import ResultSet
from boto.route53.change_info import ChangeInfo
from boto.route53.hostedzone import HostedZone
from boto.route53.record import Record
from boto.exception import BotoServerError
import boto.jsonresponse

HZXML = """<?xml version="1.0" encoding="UTF-8"?>
<CreateHostedZoneRequest xmlns="%(xmlns)s">
  <Name>%(name)s</Name>
  <CallerReference>%(caller_ref)s</CallerReference>
  <HostedZoneConfig>
    <Comment>%(comment)s</Comment>
  </HostedZoneConfig>
</CreateHostedZoneRequest>"""

class Route53Connection(AWSAuthConnection):

    DefaultHost = 'route53.amazonaws.com'
    Version = '2010-10-01'
    RequestURI = '%s/hostedzone' % Version
    XMLNameSpace = 'https://route53.amazonaws.com/doc/2010-10-01/'
    ResponseError = BotoServerError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 port=None, proxy=None, proxy_port=None,
                 host=DefaultHost, debug=0):
        AWSAuthConnection.__init__(self, host,
                aws_access_key_id, aws_secret_access_key,
                True, port, proxy, proxy_port, debug=debug)

    def _required_auth_capability(self):
        return ['route53']

    def make_request(self, path, params=None, data='', verb='GET'):
        http_request = self.build_base_http_request(verb, path, None, params, data=data)
        http_request = self.fill_in_auth(http_request)
        return self._send_http_request(http_request)

    def get_list(self, markers, action='', params=None, data='', verb='GET', request_uri=RequestURI):
        path = '/%s/%s' % (request_uri, action)
        response = self.make_request(path, params, data, verb)
        body = response.read()
        boto.log.debug(body)
        if response.status == 200:
            rs = ResultSet(markers)
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)

    def get_object(self, cls, action='', params=None, data='', verb='GET', expected_status=200, request_uri=RequestURI):
        path = '/%s/%s' % (request_uri, action)
        response = self.make_request(path, params, data, verb)
        body = response.read()
        boto.log.debug(body)
        if response.status == expected_status:
            obj = cls(self)
            h = handler.XmlHandler(obj, self)
            xml.sax.parseString(body, h)
            return obj
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)

    def get_all_hosted_zones(self):
        """
        Returns a HostedZone object for each zone defined for this AWS
        account.

        :rtype: list
        :return: A list of :class:`boto.route53.hostedzone.HostedZone`
        """
        return self.get_list([('HostedZone', HostedZone)])

    def get_hosted_zone(self, hosted_zone_id):
        """
        Get detailed information about a particular Hosted Zone.

        :type hosted_zone_id: str
        :param hosted_zone_id: The unique identifier for the Hosted Zone

        :rtype: :class:`boto.route53.hostedzone.HostedZone`
        :return: The HostedZone object.
        """
        return self.get_object(HostedZone, action=hosted_zone_id)

    def create_hosted_zone(self, domain_name, caller_ref=None, comment=''):
        """
        Create a new Hosted Zone. Returns the new zone object created.

        :type domain_name: str
        :param domain_name: The name of the domain. This should be a
                            fully-specified domain, and should end with
                            a final period as the last label indication.
                            If you omit the final period, Amazon Route 53
                            assumes the domain is relative to the root.
                            This is the name you have registered with your
                            DNS registrar. It is also the name you will
                            delegate from your registrar to the Amazon
                            Route 53 delegation servers returned in
                            response to this request.A list of strings
                            with the image IDs wanted

        :type caller_ref: str
        :param caller_ref: A unique string that identifies the request
                           and that allows failed CreateHostedZone requests
                           to be retried without the risk of executing the
                           operation twice.
                           If you don't provide a value for this, boto will
                           generate a Type 4 UUID and use that.

        :type comment: str
        :param comment: Any comments you want to include about the hosted
                        zone.

        :rtype: :class:`boto.route53.hostedzone.HostedZone`
        :returns: The newly created HostedZone.
        """
        if caller_ref is None:
            caller_ref = str(uuid.uuid4())
        params = {'name' : domain_name,
                  'caller_ref' : caller_ref,
                  'comment' : comment,
                  'xmlns' : self.XMLNameSpace}
        xml = HZXML % params

        return self.get_object(HostedZone, data=xml, verb='POST', expected_status=201)

    def delete_hosted_zone(self, hosted_zone_id):
        """
        Delete a hosted zone with the given ID.

        :rtype: :class:`boto.route53.change_info.ChangeInfo`
        :return: The ChangeInfo result of the operation.
        """
        return self.get_object(ChangeInfo, action=hosted_zone_id, verb='DELETE', expected_status=200)

    # Resource Record Sets

    def get_all_rrsets(self, hosted_zone_id, type=None,
                       name=None, maxitems=None):
        """
        Retrieve the Resource Record Sets defined for this Hosted Zone.
        Returns an array of Record objects.

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

        :type name: str
        :param name: The first name in the lexicographic ordering of domain
                     names to be retrieved

        :type maxitems: int
        :param maxitems: The maximum number of records
        """
        params = {'type': type, 'name': name, 'maxitems': maxitems}
        action = '%s/rrset' % hosted_zone_id
        return self.get_list([('ResourceRecordSet', Record)], action=action, params=params)

    def change_rrsets(self, hosted_zone_id, xml_body):
        """
        Create or change the authoritative DNS information for this
        Hosted Zone. Returns an instance of ChangeInfo for checking on the
        status of this operation.

        :type hosted_zone_id: str
        :param hosted_zone_id: The unique identifier for the Hosted Zone

        :type xml_body: str
        :param xml_body: The list of changes to be made, defined in the
                         XML schema defined by the Route53 service.

        :rtype: :class:`boto.route53.change_info.ChangeInfo`
        :return: The ChangeInfo object for checking on the status of this operation.
        """
        action = '%s/rrset' % hosted_zone_id
        return self.get_object(ChangeInfo, action=action, data=xml_body, verb='POST')

    def get_change(self, change_id):
        """
        Get information about a proposed set of changes, as submitted
        by the change_rrsets method.

        :type change_id: str
        :param change_id: The unique identifier for the set of changes.
                          This ID is returned in the response to the
                          change_rrsets method.

        :rtype: :class:`boto.route53.change_info.ChangeInfo`
        :return: The ChangeInfo object for the ID requested.
        """
        request_uri = "%s/change" % self.Version
        return self.get_object(ChangeInfo, action=change_id, request_uri=request_uri)

