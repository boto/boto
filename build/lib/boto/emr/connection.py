# Copyright (c) 2010 Spotify AB
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

"""
Represents a connection to the EMR service
"""
import types

import boto
from boto.ec2.regioninfo import RegionInfo
from boto.emr.emrobject import JobFlow, RunJobFlowResponse
from boto.emr.step import JarStep
from boto.connection import AWSQueryConnection
from boto.exception import EmrResponseError

class EmrConnection(AWSQueryConnection):

    APIVersion = boto.config.get('Boto', 'emr_version', '2009-03-31')
    DefaultRegionName = boto.config.get('Boto', 'emr_region_name', 'us-east-1')
    DefaultRegionEndpoint = boto.config.get('Boto', 'emr_region_endpoint',
                                            'elasticmapreduce.amazonaws.com')
    ResponseError = EmrResponseError

    # Constants for AWS Console debugging
    DebuggingJar = 's3n://us-east-1.elasticmapreduce/libs/script-runner/script-runner.jar'
    DebuggingArgs = 's3n://us-east-1.elasticmapreduce/libs/state-pusher/0.1/fetch'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None, path='/'):
        if not region:
            region = RegionInfo(self, self.DefaultRegionName, self.DefaultRegionEndpoint)
        self.region = region
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
                                    proxy_user, proxy_pass,
                                    self.region.endpoint, debug,
                                    https_connection_factory, path)

    def _required_auth_capability(self):
        return ['emr']

    def describe_jobflow(self, jobflow_id):
        """
        Describes a single Elastic MapReduce job flow

        :type jobflow_id: str
        :param jobflow_id: The job flow id of interest
        """
        jobflows = self.describe_jobflows(jobflow_ids=[jobflow_id])
        if jobflows:
            return jobflows[0]

    def describe_jobflows(self, states=None, jobflow_ids=None,
                           created_after=None, created_before=None):
        """
        Retrieve all the Elastic MapReduce job flows on your account

        :type states: list
        :param states: A list of strings with job flow states wanted

        :type jobflow_ids: list
        :param jobflow_ids: A list of job flow IDs
        :type created_after: datetime
        :param created_after: Bound on job flow creation time

        :type created_before: datetime
        :param created_before: Bound on job flow creation time
        """
        params = {}

        if states:
            self.build_list_params(params, states, 'JobFlowStates.member')
        if jobflow_ids:
            self.build_list_params(params, jobflow_ids, 'JobFlowIds.member')
        if created_after:
            params['CreatedAfter'] = created_after.strftime('%Y-%m-%dT%H:%M:%S')
        if created_before:
            params['CreatedBefore'] = created_before.strftime('%Y-%m-%dT%H:%M:%S')

        return self.get_list('DescribeJobFlows', params, [('member', JobFlow)])

    def terminate_jobflow(self, jobflow_id):
        """
        Terminate an Elastic MapReduce job flow

        :type jobflow_id: str
        :param jobflow_id: A jobflow id 
        """
        self.terminate_jobflows([jobflow_id]) 

    def terminate_jobflows(self, jobflow_ids):
        """
        Terminate an Elastic MapReduce job flow

        :type jobflow_ids: list
        :param jobflow_ids: A list of job flow IDs
        """
        params = {}
        self.build_list_params(params, jobflow_ids, 'JobFlowIds.member')
        return self.get_status('TerminateJobFlows', params)

    def add_jobflow_steps(self, jobflow_id, steps):
        """
        Adds steps to a jobflow

        :type jobflow_id: str
        :param jobflow_id: The job flow id
        :type steps: list(boto.emr.Step)
        :param steps: A list of steps to add to the job
        """
        if type(steps) != types.ListType:
            steps = [steps]
        params = {}
        params['JobFlowId'] = jobflow_id

        # Step args
        step_args = [self._build_step_args(step) for step in steps]
        params.update(self._build_step_list(step_args))

        return self.get_object('AddJobFlowSteps', params, RunJobFlowResponse)

    def run_jobflow(self, name, log_uri, ec2_keyname=None, availability_zone=None,
                    master_instance_type='m1.small',
                    slave_instance_type='m1.small', num_instances=1,
                    action_on_failure='TERMINATE_JOB_FLOW', keep_alive=False,
                    enable_debugging=False,
                    hadoop_version='0.18',
                    steps=[],
                    bootstrap_actions=[]):
        """
        Runs a job flow

        :type name: str
        :param name: Name of the job flow
        :type log_uri: str
        :param log_uri: URI of the S3 bucket to place logs
        :type ec2_keyname: str
        :param ec2_keyname: EC2 key used for the instances
        :type availability_zone: str
        :param availability_zone: EC2 availability zone of the cluster
        :type master_instance_type: str
        :param master_instance_type: EC2 instance type of the master
        :type slave_instance_type: str
        :param slave_instance_type: EC2 instance type of the slave nodes
        :type num_instances: int
        :param num_instances: Number of instances in the Hadoop cluster
        :type action_on_failure: str
        :param action_on_failure: Action to take if a step terminates
        :type keep_alive: bool
        :param keep_alive: Denotes whether the cluster should stay alive upon completion
        :type enable_debugging: bool
        :param enable_debugging: Denotes whether AWS console debugging should be enabled.
        :type steps: list(boto.emr.Step)
        :param steps: List of steps to add with the job

        :rtype: str
        :return: The jobflow id
        """
        params = {}
        if action_on_failure:
            params['ActionOnFailure'] = action_on_failure
        params['Name'] = name
        params['LogUri'] = log_uri

        # Instance args
        instance_params = self._build_instance_args(ec2_keyname, availability_zone,
                                                    master_instance_type, slave_instance_type,
                                                    num_instances, keep_alive, hadoop_version)
        params.update(instance_params)

        # Debugging step from EMR API docs
        if enable_debugging:
            debugging_step = JarStep(name='Setup Hadoop Debugging',
                                     action_on_failure='TERMINATE_JOB_FLOW',
                                     main_class=None,
                                     jar=self.DebuggingJar,
                                     step_args=self.DebuggingArgs)
            steps.insert(0, debugging_step)

        # Step args
        if steps:
            step_args = [self._build_step_args(step) for step in steps]
            params.update(self._build_step_list(step_args))

        if bootstrap_actions:
            bootstrap_action_args = [self._build_bootstrap_action_args(bootstrap_action) for bootstrap_action in bootstrap_actions]
            params.update(self._build_bootstrap_action_list(bootstrap_action_args))

        response = self.get_object('RunJobFlow', params, RunJobFlowResponse)
        return response.jobflowid

    def _build_bootstrap_action_args(self, bootstrap_action):
        bootstrap_action_params = {}
        bootstrap_action_params['ScriptBootstrapAction.Path'] = bootstrap_action.path

        try:
            bootstrap_action_params['Name'] = bootstrap_action.name
        except AttributeError:
            pass

        args = bootstrap_action.args()
        if args:
            self.build_list_params(bootstrap_action_params, args, 'ScriptBootstrapAction.Args.member')

        return bootstrap_action_params

    def _build_step_args(self, step):
        step_params = {}
        step_params['ActionOnFailure'] = step.action_on_failure
        step_params['HadoopJarStep.Jar'] = step.jar()

        main_class = step.main_class()
        if main_class:
            step_params['HadoopJarStep.MainClass'] = main_class

        args = step.args()
        if args:
            self.build_list_params(step_params, args, 'HadoopJarStep.Args.member')

        step_params['Name'] = step.name
        return step_params

    def _build_bootstrap_action_list(self, bootstrap_actions):
        if type(bootstrap_actions) != types.ListType:
            bootstrap_actions = [bootstrap_actions]

        params = {}
        for i, bootstrap_action in enumerate(bootstrap_actions):
            for key, value in bootstrap_action.iteritems():
                params['BootstrapActions.memeber.%s.%s' % (i + 1, key)] = value
        return params

    def _build_step_list(self, steps):
        if type(steps) != types.ListType:
            steps = [steps]

        params = {}
        for i, step in enumerate(steps):
            for key, value in step.iteritems():
                params['Steps.memeber.%s.%s' % (i+1, key)] = value
        return params

    def _build_instance_args(self, ec2_keyname, availability_zone, master_instance_type,
                             slave_instance_type, num_instances, keep_alive, hadoop_version):
        params = {
            'Instances.MasterInstanceType' : master_instance_type,
            'Instances.SlaveInstanceType' : slave_instance_type,
            'Instances.InstanceCount' : num_instances,
            'Instances.KeepJobFlowAliveWhenNoSteps' : str(keep_alive).lower(),
            'Instances.HadoopVersion' : hadoop_version
        }

        if ec2_keyname:
            params['Instances.Ec2KeyName'] = ec2_keyname
        if availability_zone:
            params['Placement'] = availability_zone

        return params

