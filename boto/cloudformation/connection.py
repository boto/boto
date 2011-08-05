# Copyright (c) 2006-2009 Mitch Garnaat http://garnaat.org/
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

try:
    import simplejson as json
except:
    import json

import boto
from boto.cloudformation.stack import Stack, StackSummary, StackEvent
from boto.cloudformation.stack import StackResource, StackResourceSummary
from boto.cloudformation.template import Template
from boto.connection import AWSQueryConnection
from boto.regioninfo import RegionInfo

class CloudFormationConnection(AWSQueryConnection):

    """
    A Connection to the CloudFormation Service.
    """
    DefaultRegionName = 'us-east-1'
    DefaultRegionEndpoint = 'cloudformation.us-east-1.amazonaws.com'
    APIVersion = '2010-05-15'

    valid_states = ("CREATE_IN_PROGRESS", "CREATE_FAILED", "CREATE_COMPLETE",
            "ROLLBACK_IN_PROGRESS", "ROLLBACK_FAILED", "ROLLBACK_COMPLETE",
            "DELETE_IN_PROGRESS", "DELETE_FAILED", "DELETE_COMPLETE")

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None, path='/', converter=None):
        if not region:
            region = RegionInfo(self, self.DefaultRegionName,
                self.DefaultRegionEndpoint, CloudFormationConnection)
        self.region = region
        AWSQueryConnection.__init__(self, aws_access_key_id, aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                                    self.region.endpoint, debug, https_connection_factory, path)

    def _required_auth_capability(self):
        return ['cloudformation']

    def encode_bool(self, v):
        v = bool(v)
        return {True: "true", False: "false"}[v]

    def create_stack(self, stack_name, template_body=None, template_url=None,
            parameters=[], notification_arns=[], disable_rollback=False,
            timeout_in_minutes=None):
        """
        Creates a CloudFormation Stack as specified by the template.

        :type stack_name: string
        :param stack_name: The name of the Stack, must be unique amoung running
                            Stacks

        :type template_body: string
        :param template_body: The template body (JSON string)

        :type template_url: string
        :param template_url: An S3 URL of a stored template JSON document. If
                            both the template_body and template_url are
                            specified, the template_body takes precedence

        :type parameters: list of tuples
        :param parameters: A list of (key, value) pairs for template input
                            parameters.

        :type notification_arns: list of strings
        :param notification_arns: A list of SNS topics to send Stack event
                            notifications to

        :type disable_rollback: bool
        :param disable_rollback: Indicates whether or not to rollback on
                            failure

        :type timeout_in_minutes: int
        :param timeout_in_minutes: Maximum amount of time to let the Stack
                            spend creating itself. If this timeout is exceeded,
                            the Stack will enter the CREATE_FAILED state

        :rtype: string
        :return: The unique Stack ID
        """
        params = {'ContentType': "JSON", 'StackName': stack_name,
                'DisableRollback': self.encode_bool(disable_rollback)}
        if template_body:
            params['TemplateBody'] = template_body
        if template_url:
            params['TemplateURL'] = template_url
        if template_body and template_url:
            boto.log.warning("If both TemplateBody and TemplateURL are"
                " specified, only TemplateBody will be honored by the API")
        if len(parameters) > 0:
            for i, (key, value) in enumerate(parameters):
                params['Parameters.member.%d.ParameterKey' % (i+1)] = key
                params['Parameters.member.%d.ParameterValue' % (i+1)] = value
        if len(notification_arns) > 0:
            self.build_list_params(params, notification_arns, "NotificationARNs.member")
        if timeout_in_minutes:
            params['TimeoutInMinutes'] = int(timeout_in_minutes)

        response = self.make_request('CreateStack', params, '/', 'POST')
        body = response.read()
        if response.status == 200:
            body = json.loads(body)
            return body['CreateStackResponse']['CreateStackResult']['StackId']
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)

    def delete_stack(self, stack_name_or_id):
        params = {'ContentType': "JSON", 'StackName': stack_name_or_id}
        # TODO: change this to get_status ?
        response = self.make_request('DeleteStack', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)

    def describe_stack_events(self, stack_name_or_id=None, next_token=None):
        params = {}
        if stack_name_or_id:
            params['StackName'] = stack_name_or_id
        if next_token:
            params['NextToken'] = next_token
        return self.get_list('DescribeStackEvents', params, [('member',
            StackEvent)])

    def describe_stack_resource(self, stack_name_or_id, logical_resource_id):
        params = {'ContentType': "JSON", 'StackName': stack_name_or_id,
                'LogicalResourceId': logical_resource_id}
        response = self.make_request('DescribeStackResource', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)

    def describe_stack_resources(self, stack_name_or_id=None,
            logical_resource_id=None,
            physical_resource_id=None):
        params = {}
        if stack_name_or_id:
            params['StackName'] = stack_name_or_id
        if logical_resource_id:
            params['LogicalResourceId'] = logical_resource_id
        if physical_resource_id:
            params['PhysicalResourceId'] = physical_resource_id
        return self.get_list('DescribeStackResources', params, [('member',
            StackResource)])

    def describe_stacks(self, stack_name_or_id=None):
        params = {}
        if stack_name_or_id:
            params['StackName'] = stack_name_or_id
        return self.get_list('DescribeStacks', params, [('member', Stack)])

    def get_template(self, stack_name_or_id):
        params = {'ContentType': "JSON", 'StackName': stack_name_or_id}
        response = self.make_request('GetTemplate', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)

    def list_stack_resources(self, stack_name_or_id, next_token=None):
        params = {'StackName': stack_name_or_id}
        if next_token:
            params['NextToken'] = next_token
        return self.get_list('ListStackResources', params, [('member',
            StackResourceSummary)])

    def list_stacks(self, stack_status_filters=[], next_token=None):
        params = {}
        if next_token:
            params['NextToken'] = next_token
        if len(stack_status_filters) > 0:
            self.build_list_params(params, stack_status_filters,
                "StackStatusFilter.member")

        return self.get_list('ListStacks', params, [('member',
            StackSummary)])

    def validate_template(self, template_body=None, template_url=None):
        params = {}
        if template_body:
            params['TemplateBody'] = template_body
        if template_url:
            params['TemplateUrl'] = template_url
        if template_body and template_url:
            boto.log.warning("If both TemplateBody and TemplateURL are"
                " specified, only TemplateBody will be honored by the API")
        return self.get_object('ValidateTemplate', params, Template,
                verb="POST")
