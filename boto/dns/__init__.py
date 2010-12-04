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

    def _get_object(self, id, resource, cls):
        uri = '/%s/%s/%s' % (self.Version, resource, id)
        response = self.make_request('GET', uri)
        body = response.read()
        boto.log.debug(body)
        if response.status >= 300:
            raise exception.DNSServerError(response.status, response.reason, body)
        o = cls(connection=self)
        h = handler.XmlHandler(o, self)
        xml.sax.parseString(body, h)
        return o

    def _create_object(self, xml, resource, cls):
        response = self.make_request('POST', '/%s/%s' % (self.Version, resource),
                                     {'Content-Type' : 'text/xml'}, xml)
        body = response.read()
        boto.log.debug(body)
        if response.status == 201:
            o = cls()
            h = handler.XmlHandler(o, self)
            xml.sax.parseString(body, h)
            return o
        else:
            raise exception.DNSServerError(response.status, response.reason, body)
        
    def _delete_object(self, id, etag, resource):
        uri = '/%s/%s/%s' % (self.Version, resource, id)
        response = self.make_request('DELETE', uri, {'If-Match' : etag})
        body = response.read()
        boto.log.debug(body)
        if response.status != 204:
            raise exception.DNSServerError(response.status, response.reason, body)

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
        return self._get_info(hosted_zone_id, 'hostedzone',
                              hostedzone.HostedZone)

    def create_hosted_zone(self, domain_name, caller_ref=None, comment=''):
        if caller_ref is None:
            caller_ref = str(uuid.uuid4())
        params = {'name' : domain_name,
                  'caller_ref' : caller_ref,
                  'comment' : comment,
                  'xmlns' : self.XMLNameSpace}
        xml = self.HZXML % params
        return self._create_object(xml, 'hostedzone', hostedzone.HostedZone)
        
    def delete_distribution(self, distribution_id, etag):
        return self._delete_object(distribution_id, etag, 'distribution')

    # Streaming Distributions
        
    def get_all_streaming_distributions(self):
        tags=[('StreamingDistributionSummary', StreamingDistributionSummary)]
        return self._get_all_objects('streaming-distribution', tags)

    def get_streaming_distribution_info(self, distribution_id):
        return self._get_info(distribution_id, 'streaming-distribution',
                              StreamingDistribution)

    def get_streaming_distribution_config(self, distribution_id):
        return self._get_config(distribution_id, 'streaming-distribution',
                                StreamingDistributionConfig)
    
    def set_streaming_distribution_config(self, distribution_id, etag, config):
        return self._set_config(distribution_id, etag, config)
    
    def create_streaming_distribution(self, origin, enabled,
                                      caller_reference='',
                                      cnames=None, comment=''):
        config = StreamingDistributionConfig(origin=origin, enabled=enabled,
                                             caller_reference=caller_reference,
                                             cnames=cnames, comment=comment)
        return self._create_object(config, 'streaming-distribution',
                                   StreamingDistribution)
        
    def delete_streaming_distribution(self, distribution_id, etag):
        return self._delete_object(distribution_id, etag, 'streaming-distribution')

    # Origin Access Identity

    def get_all_origin_access_identity(self):
        tags=[('CloudFrontOriginAccessIdentitySummary',
               OriginAccessIdentitySummary)]
        return self._get_all_objects('origin-access-identity/cloudfront', tags)

    def get_origin_access_identity_info(self, access_id):
        return self._get_info(access_id, 'origin-access-identity/cloudfront',
                              OriginAccessIdentity)

    def get_origin_access_identity_config(self, access_id):
        return self._get_config(access_id,
                                'origin-access-identity/cloudfront',
                                OriginAccessIdentityConfig)
    
    def set_origin_access_identity_config(self, access_id,
                                          etag, config):
        return self._set_config(access_id, etag, config)
    
    def create_origin_access_identity(self, caller_reference='', comment=''):
        config = OriginAccessIdentityConfig(caller_reference=caller_reference,
                                            comment=comment)
        return self._create_object(config, 'origin-access-identity/cloudfront',
                                   OriginAccessIdentity)
        
    def delete_origin_access_identity(self, access_id, etag):
        return self._delete_object(access_id, etag,
                                   'origin-access-identity/cloudfront')

    # Object Invalidation
    
    def create_invalidation_request(self, distribution_id, paths, caller_reference=None):
        """Creates a new invalidation request
            :see: http://docs.amazonwebservices.com/AmazonCloudFront/2010-08-01/APIReference/index.html?CreateInvalidation.html
        """
        # We allow you to pass in either an array or
        # an InvalidationBatch object
        if not isinstance(paths, InvalidationBatch):
            paths = InvalidationBatch(paths)
        paths.connection = self
        response = self.make_request('POST', '/%s/distribution/%s/invalidation' % (self.Version, distribution_id),
                                     {'Content-Type' : 'text/xml'}, data=paths.to_xml())
        body = response.read()
        if response.status == 201:
            h = handler.XmlHandler(paths, self)
            xml.sax.parseString(body, h)
            return paths
        else:
            raise exception.DNSServerError(response.status, response.reason, body)

