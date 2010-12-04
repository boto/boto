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
import base64
import time
import uuid
import boto
from boto.connection import AWSAuthConnection
from boto import handler
from boto.resultset import ResultSet
import boto.jsonresponse
import exception
import hostedzone

boto.set_stream_logger('dns')

class DNSConnection(AWSAuthConnection):

    DefaultHost = 'route53.amazonaws.com'
    Version = '2010-10-01'
    XMLNameSpace = 'https://route53.amazonaws.com/doc/2010-10-01/'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 port=None, proxy=None, proxy_port=None,
                 host=DefaultHost, debug=2):
        AWSAuthConnection.__init__(self, host,
                aws_access_key_id, aws_secret_access_key,
                True, port, proxy, proxy_port, debug=debug)

    def add_aws_auth_header(self, headers, method, path):
        if not headers.has_key('Date'):
            headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT",
                                            time.gmtime())

        if self.hmac_256:
            hmac = self.hmac_256.copy()
            alg = 'HmacSHA256'
        else:
            hmac = self.hmac.copy()
            alg = 'HmacSHA1'

        hmac.update(headers['Date'])
        b64_hmac = base64.encodestring(hmac.digest()).strip()
        s = "AWS3-HTTPS AWSAccessKeyId=%s," % self.aws_access_key_id
        s += "Algorithm=%s,Signature=%s" % (alg, b64_hmac)
        headers['X-Amzn-Authorization'] = s

    # Generics
    
    def _get_all_objects(self, resource, list_marker, item_marker):
        response = self.make_request('GET', '/%s/%s' % (self.Version, resource))
        body = response.read()
        boto.log.debug(body)
        if response.status >= 300:
            raise exception.DNSServerError(response.status, response.reason, body)
        e = boto.jsonresponse.Element(list_marker='HostedZones',
                                      item_marker=('HostedZone',))
        h = boto.jsonresponse.XmlHandler(e, None)
        h.parse(body)
        return e

    def _get_object(self, id, resource, list_marker, item_marker):
        uri = '/%s/%s/%s' % (self.Version, resource, id)
        response = self.make_request('GET', uri)
        body = response.read()
        boto.log.debug(body)
        if response.status >= 300:
            raise exception.DNSServerError(response.status, response.reason, body)
        e = boto.jsonresponse.Element(list_marker=list_marker,
                                      item_marker=item_marker)
        h = boto.jsonresponse.XmlHandler(e, None)
        h.parse(body)
        return e

    def _create_object(self, xml, resource, list_marker, item_marker):
        response = self.make_request('POST', '/%s/%s' % (self.Version, resource),
                                     {'Content-Type' : 'text/xml'}, xml)
        body = response.read()
        boto.log.debug(body)
        if response.status == 201:
            e = boto.jsonresponse.Element(list_marker=list_marker,
                                          item_marker=item_marker)
            h = boto.jsonresponse.XmlHandler(e, None)
            h.parse(body)
            return e
        else:
            raise exception.DNSServerError(response.status, response.reason, body)
        
    def _delete_object(self, id, resource):
        uri = '/%s/%s/%s' % (self.Version, resource, id)
        response = self.make_request('DELETE', uri)
        body = response.read()
        boto.log.debug(body)
        if response.status != 204:
            raise exception.DNSServerError(response.status, response.reason, body)
        e = boto.jsonresponse.Element(list_marker=None,
                                      item_marker=None)
        h = boto.jsonresponse.XmlHandler(e, None)
        h.parse(body)
        return e

    # Hosted Zones

    HZXML = """
    <?xml version="1.0" encoding="UTF-8"?>
      <CreateHostedZoneRequest xmlns="%(xmlns)s">
        <Name>%(name)s</Name>
        <CallerReference>%(caller_ref)s</CallerReference>
        <HostedZoneConfig>
          <Comment>%(comment)s</Comment>
        </HostedZoneConfig>
      </CreateHostedZoneRequest>"""
        
    def get_all_hosted_zones(self):
        return self._get_all_objects('hostedzone',
                                     list_marker='HostedZones',
                                     item_marker=('HostedZone',))
    
    def get_hosted_zone(self, hosted_zone_id):
        return self._get_object(hosted_zone_id, 'hostedzone',
                                list_marker='NameServers',
                                item_marker=('NameServer',))

    def create_hosted_zone(self, domain_name, caller_ref=None, comment=''):
        if caller_ref is None:
            caller_ref = str(uuid.uuid4())
        params = {'name' : domain_name,
                  'caller_ref' : caller_ref,
                  'comment' : comment,
                  'xmlns' : self.XMLNameSpace}
        xml = self.HZXML % params
        return self._create_object(xml, 'hostedzone',
                                   list_marker='NameServers',
                                   item_marker=('NameServer',))
        
    def delete_hosted_zone(self, hosted_zone_id):
        return self._delete_object(hosted_zone_id, 'distribution')

