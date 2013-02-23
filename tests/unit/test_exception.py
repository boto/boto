from tests.unit import unittest

from boto.exception import BotoServerError

class TestBotoServerError(unittest.TestCase):

    def test_botoservererror_basics(self):
        bse = BotoServerError('400', 'Bad Request')
        self.assertEqual(bse.status, '400')
        self.assertEqual(bse.reason, 'Bad Request')

    def test_message_elb_xml(self):
        # This test XML response comes from #509
        xml = """
<ErrorResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2011-11-15/">
  <Error>
    <Type>Sender</Type>
    <Code>LoadBalancerNotFound</Code>
    <Message>Cannot find Load Balancer webapp-balancer2</Message>
  </Error>
  <RequestId>093f80d0-4473-11e1-9234-edce8ec08e2d</RequestId>
</ErrorResponse>"""
        bse = BotoServerError('400', 'Bad Request', body=xml)
        
        self.assertEqual(bse.error_message, 'Cannot find Load Balancer webapp-balancer2')
        self.assertEqual(bse.request_id, '093f80d0-4473-11e1-9234-edce8ec08e2d')
        self.assertEqual(bse.error_code, 'LoadBalancerNotFound')
        self.assertEqual(bse.status, '400')
        self.assertEqual(bse.reason, 'Bad Request')

    def test_message_sd_xml(self):
        # Sample XML response from: https://forums.aws.amazon.com/thread.jspa?threadID=87393
        xml = """
<Response>
  <Errors>
    <Error>
      <Code>AuthorizationFailure</Code>
      <Message>Session does not have permission to perform (sdb:CreateDomain) on resource (arn:aws:sdb:us-east-1:xxxxxxx:domain/test_domain). Contact account owner.</Message>
      <BoxUsage>0.0055590278</BoxUsage>
    </Error>
  </Errors>
  <RequestID>e73bb2bb-63e3-9cdc-f220-6332de66dbbe</RequestID>
</Response>"""
        bse = BotoServerError('403', 'Forbidden', body=xml)
        self.assertEqual(bse.error_message, 
            'Session does not have permission to perform (sdb:CreateDomain) on '
            'resource (arn:aws:sdb:us-east-1:xxxxxxx:domain/test_domain). '
            'Contact account owner.')
        self.assertEqual(bse.box_usage, '0.0055590278')
        self.assertEqual(bse.error_code, 'AuthorizationFailure')
        self.assertEqual(bse.status, '403')
        self.assertEqual(bse.reason, 'Forbidden')

    def test_message_not_xml(self):
        body = 'This is not XML'

        bse = BotoServerError('400', 'Bad Request', body=body)
        self.assertEqual(bse.error_message, 'This is not XML')

    def test_getters(self):
        body = "This is the body"

        bse = BotoServerError('400', 'Bad Request', body=body)
        self.assertEqual(bse.code, bse.error_code)
