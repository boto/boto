#!/usr/bin/env python
import unittest
import httplib
import json

from mock import Mock

from boto.cloudformation.connection import CloudFormationConnection


SAMPLE_TEMPLATE = r"""
{
  "AWSTemplateFormatVersion" : "2010-09-09",
  "Description" : "Sample template",
  "Parameters" : {
    "KeyName" : {
      "Description" : "key pair",
      "Type" : "String"
    }
  },
  "Resources" : {
    "Ec2Instance" : {
      "Type" : "AWS::EC2::Instance",
      "Properties" : {
        "KeyName" : { "Ref" : "KeyName" },
        "ImageId" : "ami-7f418316",
        "UserData" : { "Fn::Base64" : "80" }
      }
    }
  },
  "Outputs" : {
    "InstanceId" : {
      "Description" : "InstanceId of the newly created EC2 instance",
      "Value" : { "Ref" : "Ec2Instance" }
    }
}
"""


class CloudFormationConnectionBase(unittest.TestCase):
    # This param is used by the unittest module to display a full
    # diff when assert*Equal methods produce an error message.
    maxDiff = None

    def setUp(self):
        self.https_connection = Mock(spec=httplib.HTTPSConnection)
        self.https_connection_factory = (
            Mock(return_value=self.https_connection), ())
        self.stack_id = u'arn:aws:cloudformation:us-east-1:18:stack/Name/id'
        self.cloud_formation = CloudFormationConnection(
            https_connection_factory=self.https_connection_factory,
            aws_access_key_id='aws_access_key_id',
            aws_secret_access_key='aws_secret_access_key')
        self.actual_request = None
        # We want to be able to verify the request params that
        # are sent to the CloudFormation service. By the time
        # we get to the boto.connection.AWSAuthConnection._mexe
        # method, all of the request params have been populated.
        # By patching out the _mexe method with self._mexe_spy,
        # we can record the actual http request that _mexe is passed
        # so that we can verify the http params (and anything
        # else about the request that we want).
        self.original_mexe = self.cloud_formation._mexe
        self.cloud_formation._mexe = self._mexe_spy

    def _mexe_spy(self, request, *args, **kwargs):
        self.actual_request = request
        return self.original_mexe(request, *args, **kwargs)

    def create_response(self, status_code, reason='', body=None):
        if body is None:
            body = self.default_body()
        response = Mock(spec=httplib.HTTPResponse)
        response.status = status_code
        response.read.return_value = body
        response.reason = reason
        return response

    def assert_request_parameters(self, params, ignore_params_values=None):
        """Verify the actual parameters sent to the service API."""
        request_params = self.actual_request.params.copy()
        if ignore_params_values is not None:
            for param in ignore_params_values:
                # We still want to check that the ignore_params_values params
                # are in the request parameters, we just don't need to check
                # their value.
                self.assertIn(param, request_params)
                del request_params[param]
        self.assertDictEqual(request_params, params)

    def set_http_response(self, status_code, reason='', body=None):
        http_response = self.create_response(status_code, reason, body)
        self.https_connection.getresponse.return_value = http_response

    def default_body(self):
        return json.dumps({})


class TestCloudFormationCreateStack(CloudFormationConnectionBase):
    def default_body(self):
        return json.dumps(
            {u'CreateStackResponse':
                 {u'CreateStackResult': {u'StackId': self.stack_id},
                  u'ResponseMetadata': {u'RequestId': u'1'}}})

    def test_create_stack_has_correct_request_params(self):
        self.set_http_response(status_code=200)
        api_response = self.cloud_formation.create_stack(
            'stack_name', template_url='http://url',
            template_body=SAMPLE_TEMPLATE,
            parameters=[('KeyName', 'myKeyName')],
            notification_arns=['arn:notify1', 'arn:notify2'],
            disable_rollback=True,
            timeout_in_minutes=20, capabilities=['CAPABILITY_IAM']
        )
        self.assertEqual(api_response, self.stack_id)
        # These are the parameters that are actually sent to the CloudFormation
        # service.
        self.assert_request_parameters({
            'AWSAccessKeyId': 'aws_access_key_id',
            'Action': 'CreateStack',
            'Capabilities.member.1': 'CAPABILITY_IAM',
            'ContentType': 'JSON',
            'DisableRollback': 'true',
            'NotificationARNs.member.1': 'arn:notify1',
            'NotificationARNs.member.2': 'arn:notify2',
            'Parameters.member.1.ParameterKey': 'KeyName',
            'Parameters.member.1.ParameterValue': 'myKeyName',
            'SignatureMethod': 'HmacSHA256',
            'SignatureVersion': 2,
            'StackName': 'stack_name',
            'Version': '2010-05-15',
            'TimeoutInMinutes': 20,
            'TemplateBody': SAMPLE_TEMPLATE,
            'TemplateURL': 'http://url',
        }, ignore_params_values=['Timestamp'])

    # The test_create_stack_has_correct_request_params verified all of the
    # params needed when making a create_stack service call.  The rest of the
    # tests for create_stack only verify specific parts of the params sent
    # to CloudFormation.

    def test_create_stack_with_minimum_args(self):
        # This will fail in practice, but the API docs only require stack_name.
        self.set_http_response(status_code=200)
        api_response = self.cloud_formation.create_stack('stack_name')
        self.assertEqual(api_response, self.stack_id)
        self.assert_request_parameters({
            'AWSAccessKeyId': 'aws_access_key_id',
            'Action': 'CreateStack',
            'ContentType': 'JSON',
            'DisableRollback': 'false',
            'SignatureMethod': 'HmacSHA256',
            'SignatureVersion': 2,
            'StackName': 'stack_name',
            'Version': '2010-05-15',
        }, ignore_params_values=['Timestamp'])

    def test_create_stack_fails(self):
        self.set_http_response(status_code=400, reason='Bad Request',
                               body='Invalid arg.')
        with self.assertRaises(self.cloud_formation.ResponseError):
            api_response = self.cloud_formation.create_stack(
                'stack_name', template_body=SAMPLE_TEMPLATE,
                parameters=[('KeyName', 'myKeyName')])


class TestCloudFormationUpdateStack(CloudFormationConnectionBase):
    def default_body(self):
        return json.dumps(
            {u'UpdateStackResponse':
                 {u'UpdateStackResult': {u'StackId': self.stack_id},
                  u'ResponseMetadata': {u'RequestId': u'1'}}})

    def test_update_stack_all_args(self):
        self.set_http_response(status_code=200)
        api_response = self.cloud_formation.update_stack(
            'stack_name', template_url='http://url',
            template_body=SAMPLE_TEMPLATE,
            parameters=[('KeyName', 'myKeyName')],
            notification_arns=['arn:notify1', 'arn:notify2'],
            disable_rollback=True,
            timeout_in_minutes=20
        )
        self.assert_request_parameters({
            'AWSAccessKeyId': 'aws_access_key_id',
            'Action': 'UpdateStack',
            'ContentType': 'JSON',
            'DisableRollback': 'true',
            'NotificationARNs.member.1': 'arn:notify1',
            'NotificationARNs.member.2': 'arn:notify2',
            'Parameters.member.1.ParameterKey': 'KeyName',
            'Parameters.member.1.ParameterValue': 'myKeyName',
            'SignatureMethod': 'HmacSHA256',
            'SignatureVersion': 2,
            'StackName': 'stack_name',
            'Version': '2010-05-15',
            'TimeoutInMinutes': 20,
            'TemplateBody': SAMPLE_TEMPLATE,
            'TemplateURL': 'http://url',
        }, ignore_params_values=['Timestamp'])

    def test_update_stack_with_minimum_args(self):
        self.set_http_response(status_code=200)
        api_response = self.cloud_formation.update_stack('stack_name')
        self.assertEqual(api_response, self.stack_id)
        self.assert_request_parameters({
            'AWSAccessKeyId': 'aws_access_key_id',
            'Action': 'UpdateStack',
            'ContentType': 'JSON',
            'DisableRollback': 'false',
            'SignatureMethod': 'HmacSHA256',
            'SignatureVersion': 2,
            'StackName': 'stack_name',
            'Version': '2010-05-15',
        }, ignore_params_values=['Timestamp'])

    def test_update_stack_fails(self):
        self.set_http_response(status_code=400, reason='Bad Request',
                               body='Invalid arg.')
        with self.assertRaises(self.cloud_formation.ResponseError):
            api_response = self.cloud_formation.update_stack(
                'stack_name', template_body=SAMPLE_TEMPLATE,
                parameters=[('KeyName', 'myKeyName')])


class TestCloudFormationDeleteStack(CloudFormationConnectionBase):
    def default_body(self):
        return json.dumps(
            {u'DeleteStackResponse':
                 {u'ResponseMetadata': {u'RequestId': u'1'}}})

    def test_delete_stack(self):
        self.set_http_response(status_code=200)
        api_response = self.cloud_formation.delete_stack('stack_name')
        self.assertEqual(api_response, json.loads(self.default_body()))
        self.assert_request_parameters({
            'AWSAccessKeyId': 'aws_access_key_id',
            'Action': 'DeleteStack',
            'ContentType': 'JSON',
            'SignatureMethod': 'HmacSHA256',
            'SignatureVersion': 2,
            'StackName': 'stack_name',
            'Version': '2010-05-15',
        }, ignore_params_values=['Timestamp'])

    def test_delete_stack_fails(self):
        self.set_http_response(status_code=400)
        with self.assertRaises(self.cloud_formation.ResponseError):
            api_response = self.cloud_formation.delete_stack('stack_name')


class TestCloudFormationDescribeStackResource(CloudFormationConnectionBase):
    def default_body(self):
        return json.dumps('fake server response')

    def test_describe_stack_resource(self):
        self.set_http_response(status_code=200)
        api_response = self.cloud_formation.describe_stack_resource(
            'stack_name', 'resource_id')
        self.assertEqual(api_response, 'fake server response')
        self.assert_request_parameters({
            'AWSAccessKeyId': 'aws_access_key_id',
            'Action': 'DescribeStackResource',
            'ContentType': 'JSON',
            'LogicalResourceId': 'resource_id',
            'SignatureMethod': 'HmacSHA256',
            'SignatureVersion': 2,
            'StackName': 'stack_name',
            'Version': '2010-05-15',
        }, ignore_params_values=['Timestamp'])

    def test_describe_stack_resource_fails(self):
        self.set_http_response(status_code=400)
        with self.assertRaises(self.cloud_formation.ResponseError):
            api_response = self.cloud_formation.describe_stack_resource(
                'stack_name', 'resource_id')


class TestCloudFormationGetTemplate(CloudFormationConnectionBase):
    def default_body(self):
        return json.dumps('fake server response')

    def test_get_template(self):
        self.set_http_response(status_code=200)
        api_response = self.cloud_formation.get_template('stack_name')
        self.assertEqual(api_response, 'fake server response')
        self.assert_request_parameters({
            'AWSAccessKeyId': 'aws_access_key_id',
            'Action': 'GetTemplate',
            'ContentType': 'JSON',
            'SignatureMethod': 'HmacSHA256',
            'SignatureVersion': 2,
            'StackName': 'stack_name',
            'Version': '2010-05-15',
        }, ignore_params_values=['Timestamp'])


    def test_get_template_fails(self):
        self.set_http_response(status_code=400)
        with self.assertRaises(self.cloud_formation.ResponseError):
            api_response = self.cloud_formation.get_template('stack_name')


if __name__ == '__main__':
    unittest.main()
