#!/usr/bin/env python

import unittest
from StringIO import StringIO

from boto.ec2.connection import EC2Connection
from boto.ec2.elb import ELBConnection
from boto.route53.connection import Route53Connection
from boto.ses.connection import SESConnection
from boto.sqs.connection import SQSConnection
from boto.s3.connection import S3Connection
from boto.sns.connection import SNSConnection
from boto.cloudsearch.layer1 import Layer1 as CloudSearchConnection
from boto.swf.layer1 import Layer1 as SWFConnection


GENERIC_BAD_REQUEST = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Response><Errors><Error><Code>Invalid Request</Code>'
    '<Message>Unknown Parameter.</Message></Error></Errors>'
    '<RequestID>ab8cd8bd-bf38-451e-a61f-b007a336427b</RequestID></Response>'
)

EC2_EXPIRED = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Response><Errors><Error><Code>RequestExpired</Code>'
    '<Message>Request has expired.</Message></Error></Errors>'
    '<RequestID>ab8cd8bd-bf38-451e-a61f-b007a336427a</RequestID></Response>'
)

ROUTE_53_EXPIRED = (
    '<?xml version="1.0"?>\n'
    '<ErrorResponse xmlns="https://route53.amazonaws.com/doc/2012-02-29/">'
    '<Error><Type>Sender</Type><Code>InvalidClientTokenId</Code>'
    '<Message>The security token included in the request is invalid</Message>'
    '</Error><RequestId>'
    '6ae75e39-ae50-11e1-bb74-6f99ae4b5ac7</RequestId></ErrorResponse>'
)

SES_EXPIRED = (
    '<ErrorResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">\n'
    '  <Error>\n'
    '    <Type>Sender</Type>\n'
    '    <Code>InvalidClientTokenId</Code>\n'
    '    <Message>The security token included in the request'
    'is invalid</Message>\n'
    '  </Error>\n'
    '  <RequestId>19e6091f-ae53-11e1-83f2-e9ee6fcf8644</RequestId>\n'
    '</ErrorResponse>'
)

SQS_EXPIRED = (
    '<?xml version="1.0"?>\n'
    '<ErrorResponse xmlns="http://queue.amazonaws.com/doc/2011-10-01/">'
    '<Error><Type>Sender</Type><Code>InvalidAccessKeyId</Code>'
    '<Message>AWS was not able to validate the provided'
    'access credentials.</Message><Detail/></Error>'
    '<RequestId>9e59388c-d590-4750-bf4b-7f5c6f22069e</RequestId>'
    '</ErrorResponse>'
)

S3_EXPIRED = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Error><Code>ExpiredToken</Code>'
    '<Message>The provided token has expired.</Message>'
    '<RequestId>8F73002DD7CE6806</RequestId>'
    '<HostId>Y3X4aRVBW</HostId>'
    '<Token-0>+3jZbqJRcmn4FTAslS/vCDq29dfpOGlcGiesXvSDh4bL+BA=='
    '</Token-0></Error>'
)

SNS_EXPIRED = (
    '{"Error":{"Code":"ExpiredToken",'
    '"Message":"The security token included in the '
    'request is expired","Type":"Sender"},'
    '"RequestId":"49da0955-ae53-11e1-a190-fd9a9336a444"}'
)

SWF_EXPIRED = (
    '{"message": "The security token included in the request is invalid",'
    '"__type": "com.amazon.coral.service#UnrecognizedClientException"}'
)

# The majority of services (with the exception of the xmlns attr) have
# an error response like this: autoscale, cloudformation, cloudsearch
# 
GENERAL_EXPIRED = (
    '<ErrorResponse xmlns="http://elasticloadbalancing.amazonaws.com/'
    'doc/2011-11-15/">\n'
    '  <Error>\n'
    '    <Type>Sender</Type>\n'
    '    <Code>ExpiredToken</Code>\n'
    '    <Message>The security token included in the request'
    'is expired</Message>\n'
    '  </Error>\n'
    '  <RequestId>7dfbf919-ae4f-11e1-bc8c-039e0b6d4242</RequestId>\n'
    '</ErrorResponse>\n'
)
# Similar to GENERAL_EXPIRED, but not quite correct.
INVALID_FORMAT = (
    '<ErrorResponse xmlns="http://elasticloadbalancing.amazonaws.com/'
    'doc/2011-11-15/">\n'
    '  <Error>\n'
    '    <Type>Sender</Type>\n'
    '    <Code><Message>The security token included in the request '
    'is expired</Message></Code>\n'
    '  </Error>\n'
    '  <RequestId>7dfbf919-ae4f-11e1-bc8c-039e0b6d4242</RequestId>\n'
    '</ErrorResponse>\n'
)


class FakeResponse(StringIO):
    def __init__(self, content, status):
        StringIO.__init__(self, content)
        self.status = status


class TestExpire(unittest.TestCase):
    def assert_is_expired(self, connection, response, status):
        self.assertTrue(connection._credentials_expired(
            FakeResponse(response, status=status)),
            "Connection was suppose to be expired but was not: %s" % response)

    def assert_is_not_expired(self, connection, response, status):
        self.assertFalse(connection._credentials_expired(
            FakeResponse(response, status=status)),
            "Connection was NOT suppose to be expired but was: %s" % response)

    def test_ec2_expiration(self):
        c = EC2Connection(aws_access_key_id='aws_access_key_id',
                          aws_secret_access_key='aws_secret_access_key')
        self.assert_is_expired(c, EC2_EXPIRED, status=400)
        self.assert_is_not_expired(c, GENERIC_BAD_REQUEST, status=400)
        self.assert_is_not_expired(c, GENERIC_BAD_REQUEST, status=403)

    def test_elb_expiration(self):
        c = ELBConnection(aws_access_key_id='aws_access_key_id',
                          aws_secret_access_key='aws_secret_access_key')
        self.assert_is_expired(c, GENERAL_EXPIRED, status=403)
        self.assert_is_not_expired(c, GENERIC_BAD_REQUEST, status=403)
        self.assert_is_not_expired(c, GENERIC_BAD_REQUEST, status=400)

    def test_cloudsearch_expiration(self):
        c = CloudSearchConnection(aws_access_key_id='aws_access_key_id',
                                  aws_secret_access_key='aws_secret_access_key')
        self.assert_is_expired(c, GENERAL_EXPIRED, status=403)

    def test_route_53_expiration(self):
        c = Route53Connection(aws_access_key_id='aws_access_key_id',
                              aws_secret_access_key='aws_secret_access_key')
        self.assert_is_expired(c, ROUTE_53_EXPIRED, status=403)
        self.assert_is_not_expired(c, GENERIC_BAD_REQUEST, status=403)

    def test_ses_expiration(self):
        c = SESConnection(aws_access_key_id='aws_access_key_id',
                          aws_secret_access_key='aws_secret_access_key')
        self.assert_is_expired(c, SES_EXPIRED, status=403)
        self.assert_is_not_expired(c, GENERIC_BAD_REQUEST, status=403)

    def test_sqs_expiration(self):
        c = SQSConnection(aws_access_key_id='aws_access_key_id',
                          aws_secret_access_key='aws_secret_access_key')
        self.assert_is_expired(c, SQS_EXPIRED, status=401)
        self.assert_is_not_expired(c, GENERIC_BAD_REQUEST, status=403)

    def test_s3_expired(self):
        c = S3Connection(aws_access_key_id='aws_access_key_id',
                         aws_secret_access_key='aws_secret_access_key')
        self.assert_is_expired(c, S3_EXPIRED, status=400)
        self.assert_is_not_expired(c, GENERIC_BAD_REQUEST, status=400)

    def test_sns_expired(self):
        c = SNSConnection(aws_access_key_id='aws_access_key_id',
                          aws_secret_access_key='aws_secret_access_key')
        self.assert_is_expired(c, SNS_EXPIRED, status=403)

    def test_swf_expired(self):
        c = SWFConnection(aws_access_key_id='aws_access_key_id',
                          aws_secret_access_key='aws_secret_access_key')
        self.assert_is_expired(c, SWF_EXPIRED, status=400)

    def test_non_xml_response(self):
        c = CloudSearchConnection(aws_access_key_id='aws_access_key_id',
                                  aws_secret_access_key='aws_secret_access_key')
        self.assert_is_not_expired(c, "{'this is': 'json'}", status=403)

    def test_invalid_schema(self):
        c = CloudSearchConnection(aws_access_key_id='aws_access_key_id',
                                  aws_secret_access_key='aws_secret_access_key')
        self.assert_is_not_expired(c, INVALID_FORMAT, status=403)


if __name__ == '__main__':
    unittest.main()
