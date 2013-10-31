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
