# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.
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
from __future__ import with_statement

import boto.utils

from datetime import datetime
from tests.unit import AWSMockServiceTestCase

from boto.emr.connection import EmrConnection
from boto.emr.emrobject import JobFlowStepList

# These tests are just checking the basic structure of
# the Elastic MapReduce code, by picking a few calls
# and verifying we get the expected results with mocked
# responses.  The integration tests actually verify the
# API calls interact with the service correctly.
class TestListClusters(AWSMockServiceTestCase):
    connection_class = EmrConnection

    def default_body(self):
        return """<ListClustersOutput><Clusters></Clusters></ListClustersOutput>"""

    def test_list_clusters(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.list_clusters()

        self.assert_request_parameters({
            'Action': 'ListClusters',
            'Version': '2009-03-31',
        })

    def test_list_clusters_created_before(self):
        self.set_http_response(status_code=200)

        date = datetime.now()
        response = self.service_connection.list_clusters(created_before=date)

        self.assert_request_parameters({
            'Action': 'ListClusters',
            'CreatedBefore': date.strftime(boto.utils.ISO8601),
            'Version': '2009-03-31'
        })

    def test_list_clusters_created_after(self):
        self.set_http_response(status_code=200)

        date = datetime.now()
        response = self.service_connection.list_clusters(created_after=date)

        self.assert_request_parameters({
            'Action': 'ListClusters',
            'CreatedAfter': date.strftime(boto.utils.ISO8601),
            'Version': '2009-03-31'
        })

    def test_list_clusters_states(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.list_clusters(cluster_states=[
            'RUNNING',
            'WAITING'
        ])

        self.assert_request_parameters({
            'Action': 'ListClusters',
            'ClusterStates.member.1': 'RUNNING',
            'ClusterStates.member.2': 'WAITING',
            'Version': '2009-03-31'
        })


class TestListInstanceGroups(AWSMockServiceTestCase):
    connection_class = EmrConnection

    def default_body(self):
        return """<ListInstanceGroupsOutput><InstanceGroups></InstanceGroups></ListInstanceGroupsOutput>"""

    def test_list_instance_groups(self):
        self.set_http_response(200)

        with self.assertRaises(TypeError):
            self.service_connection.list_instance_groups()

        response = self.service_connection.list_instance_groups(cluster_id='j-123')

        self.assert_request_parameters({
            'Action': 'ListInstanceGroups',
            'ClusterId': 'j-123',
            'Version': '2009-03-31'
        })

class TestListInstances(AWSMockServiceTestCase):
    connection_class = EmrConnection

    def default_body(self):
        return """<ListInstancesOutput><Instances></Instances></ListInstancesOutput>"""

    def test_list_instances(self):
        self.set_http_response(200)

        with self.assertRaises(TypeError):
            self.service_connection.list_instances()

        response = self.service_connection.list_instances(cluster_id='j-123')

        self.assert_request_parameters({
            'Action': 'ListInstances',
            'ClusterId': 'j-123',
            'Version': '2009-03-31'
        })

    def test_list_instances_with_group_id(self):
        self.set_http_response(200)
        response = self.service_connection.list_instances(
            cluster_id='j-123', instance_group_id='abc')

        self.assert_request_parameters({
            'Action': 'ListInstances',
            'ClusterId': 'j-123',
            'InstanceGroupId': 'abc',
            'Version': '2009-03-31'
        })

    def test_list_instances_with_types(self):
        self.set_http_response(200)

        response = self.service_connection.list_instances(
            cluster_id='j-123', instance_group_types=[
                'MASTER',
                'TASK'
            ])

        self.assert_request_parameters({
            'Action': 'ListInstances',
            'ClusterId': 'j-123',
            'InstanceGroupTypeList.member.1': 'MASTER',
            'InstanceGroupTypeList.member.2': 'TASK',
            'Version': '2009-03-31'
        })


class TestListSteps(AWSMockServiceTestCase):
    connection_class = EmrConnection

    def default_body(self):
        return """<ListStepsOutput><Steps></Steps></ListStepsOutput>"""

    def test_list_steps(self):
        self.set_http_response(200)

        with self.assertRaises(TypeError):
            self.service_connection.list_steps()

        response = self.service_connection.list_steps(cluster_id='j-123')

        self.assert_request_parameters({
            'Action': 'ListSteps',
            'ClusterId': 'j-123',
            'Version': '2009-03-31'
        })

    def test_list_steps_with_states(self):
        self.set_http_response(200)
        response = self.service_connection.list_steps(
            cluster_id='j-123', step_states=[
                'COMPLETED',
                'FAILED'
            ])

        self.assert_request_parameters({
            'Action': 'ListSteps',
            'ClusterId': 'j-123',
            'StepStateList.member.1': 'COMPLETED',
            'StepStateList.member.2': 'FAILED',
            'Version': '2009-03-31'
        })


class TestListBootstrapActions(AWSMockServiceTestCase):
    connection_class = EmrConnection

    def default_body(self):
        return """<ListBootstrapActionsOutput></ListBootstrapActionsOutput>"""

    def test_list_bootstrap_actions(self):
        self.set_http_response(200)

        with self.assertRaises(TypeError):
            self.service_connection.list_bootstrap_actions()

        response = self.service_connection.list_bootstrap_actions(cluster_id='j-123')

        self.assert_request_parameters({
            'Action': 'ListBootstrapActions',
            'ClusterId': 'j-123',
            'Version': '2009-03-31'
        })


class TestDescribeCluster(AWSMockServiceTestCase):
    connection_class = EmrConnection

    def default_body(self):
        return """<DescribeClusterOutput></DescribeClusterOutput>"""

    def test_describe_cluster(self):
        self.set_http_response(200)

        with self.assertRaises(TypeError):
            self.service_connection.describe_cluster()

        response = self.service_connection.describe_cluster(cluster_id='j-123')

        self.assert_request_parameters({
            'Action': 'DescribeCluster',
            'ClusterId': 'j-123',
            'Version': '2009-03-31'
        })


class TestDescribeStep(AWSMockServiceTestCase):
    connection_class = EmrConnection

    def default_body(self):
        return """<DescribeStepOutput></DescribeStepOutput>"""

    def test_describe_step(self):
        self.set_http_response(200)

        with self.assertRaises(TypeError):
            self.service_connection.describe_step()

        with self.assertRaises(TypeError):
            self.service_connection.describe_step(cluster_id='j-123')

        with self.assertRaises(TypeError):
            self.service_connection.describe_step(step_id='abc')

        response = self.service_connection.describe_step(
            cluster_id='j-123', step_id='abc')

        self.assert_request_parameters({
            'Action': 'DescribeStep',
            'ClusterId': 'j-123',
            'StepId': 'abc',
            'Version': '2009-03-31'
        })


class TestAddJobFlowSteps(AWSMockServiceTestCase):
    connection_class = EmrConnection

    def default_body(self):
        return """
<AddJobFlowStepsOutput>
    <StepIds>
        <member>Foo</member>
        <member>Bar</member>
    </StepIds>
</AddJobFlowStepsOutput>
"""

    def test_add_jobflow_steps(self):
        self.set_http_response(200)

        response = self.service_connection.add_jobflow_steps(
            jobflow_id='j-123', steps=[])

        # Make sure the correct object is returned, as this was
        # previously set to incorrectly return an empty instance
        # of RunJobFlowResponse.
        self.assertTrue(isinstance(response, JobFlowStepList))
        self.assertEqual(response.stepids[0].value, 'Foo')
        self.assertEqual(response.stepids[1].value, 'Bar')


class TestBuildTagList(AWSMockServiceTestCase):
    connection_class = EmrConnection

    def test_key_without_value_encoding(self):
        input_dict = {
            'KeyWithNoValue': '',
            'AnotherKeyWithNoValue': None
        }
        res = self.service_connection._build_tag_list(input_dict)
        # Keys are outputted in ascending key order.
        expected = {
            'Tags.member.1.Key': 'AnotherKeyWithNoValue',
            'Tags.member.2.Key': 'KeyWithNoValue'
        }
        self.assertEqual(expected, res)

    def test_key_full_key_value_encoding(self):
        input_dict = {
            'FirstKey': 'One',
            'SecondKey': 'Two'
        }
        res = self.service_connection._build_tag_list(input_dict)
        # Keys are outputted in ascending key order.
        expected = {
            'Tags.member.1.Key': 'FirstKey',
            'Tags.member.1.Value': 'One',
            'Tags.member.2.Key': 'SecondKey',
            'Tags.member.2.Value': 'Two'
        }
        self.assertEqual(expected, res)


class TestAddTag(AWSMockServiceTestCase):
    connection_class = EmrConnection

    def default_body(self):
        return """<AddTagsResponse
               xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
                   <AddTagsResult/>
                   <ResponseMetadata>
                        <RequestId>88888888-8888-8888-8888-888888888888</RequestId>
                   </ResponseMetadata>
               </AddTagsResponse>
               """

    def test_add_mix_of_tags_with_without_values(self):
        input_tags = {
            'FirstKey': 'One',
            'SecondKey': 'Two',
            'ZzzNoValue': ''
        }
        self.set_http_response(200)

        with self.assertRaises(TypeError):
            self.service_connection.add_tags()

        with self.assertRaises(TypeError):
            self.service_connection.add_tags('j-123')

        with self.assertRaises(AssertionError):
            self.service_connection.add_tags('j-123', [])

        response = self.service_connection.add_tags('j-123', input_tags)

        self.assertTrue(response)
        self.assert_request_parameters({
            'Action': 'AddTags',
            'ResourceId': 'j-123',
            'Tags.member.1.Key': 'FirstKey',
            'Tags.member.1.Value': 'One',
            'Tags.member.2.Key': 'SecondKey',
            'Tags.member.2.Value': 'Two',
            'Tags.member.3.Key': 'ZzzNoValue',
            'Version': '2009-03-31'
        })


class TestRemoveTag(AWSMockServiceTestCase):
    connection_class = EmrConnection

    def default_body(self):
        return """<RemoveTagsResponse
               xmlns="http://elasticmapreduce.amazonaws.com/doc/2009-03-31">
                   <RemoveTagsResult/>
                   <ResponseMetadata>
                        <RequestId>88888888-8888-8888-8888-888888888888</RequestId>
                   </ResponseMetadata>
               </RemoveTagsResponse>
               """

    def test_remove_tags(self):
        input_tags = {
            'FirstKey': 'One',
            'SecondKey': 'Two',
            'ZzzNoValue': ''
        }
        self.set_http_response(200)

        with self.assertRaises(TypeError):
            self.service_connection.add_tags()

        with self.assertRaises(TypeError):
            self.service_connection.add_tags('j-123')

        with self.assertRaises(AssertionError):
            self.service_connection.add_tags('j-123', [])

        response = self.service_connection.remove_tags('j-123', ['FirstKey', 'SecondKey'])

        self.assertTrue(response)
        self.assert_request_parameters({
            'Action': 'RemoveTags',
            'ResourceId': 'j-123',
            'TagKeys.member.1': 'FirstKey',
            'TagKeys.member.2': 'SecondKey',
            'Version': '2009-03-31'
        })
