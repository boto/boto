# Copyright (c) 2010 Spotify AB
# Copyright (c) 2010-2011 Yelp
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
import boto.utils
from boto.ec2.regioninfo import RegionInfo
from boto.emr.emrobject import JobFlow, RunJobFlowResponse
from boto.emr.emrobject import AddInstanceGroupsResponse, ModifyInstanceGroupsResponse
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
            region = RegionInfo(self, self.DefaultRegionName,
                                self.DefaultRegionEndpoint)
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
            params['CreatedAfter'] = created_after.strftime(
                boto.utils.ISO8601)
        if created_before:
            params['CreatedBefore'] = created_before.strftime(
                boto.utils.ISO8601)

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
        return self.get_status('TerminateJobFlows', params, verb='POST')

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

        return self.get_object(
            'AddJobFlowSteps', params, RunJobFlowResponse, verb='POST')

    def add_instance_groups(self, jobflow_id, instance_groups):
        """
        Adds instance groups to a running cluster.

        :type jobflow_id: str
        :param jobflow_id: The id of the jobflow which will take the
            new instance groups
            
        :type instance_groups: list(boto.emr.InstanceGroup)
        :param instance_groups: A list of instance groups to add to the job
        """
        if type(instance_groups) != types.ListType:
            instance_groups = [instance_groups]
        params = {}
        params['JobFlowId'] = jobflow_id
        params.update(self._build_instance_group_list_args(instance_groups))

        return self.get_object('AddInstanceGroups', params,
                               AddInstanceGroupsResponse, verb='POST')

    def modify_instance_groups(self, instance_group_ids, new_sizes):
        """
        Modify the number of nodes and configuration settings in an
        instance group.

        :type instance_group_ids: list(str)
        :param instance_group_ids: A list of the ID's of the instance
            groups to be modified
            
        :type new_sizes: list(int)
        :param new_sizes: A list of the new sizes for each instance group
        """
        if type(instance_group_ids) != types.ListType:
            instance_group_ids = [instance_group_ids]
        if type(new_sizes) != types.ListType:
            new_sizes = [new_sizes]

        instance_groups = zip(instance_group_ids, new_sizes)

        params = {}
        for k, ig in enumerate(instance_groups):
            # could be wrong - the example amazon gives uses
            # InstanceRequestCount, while the api documentation
            # says InstanceCount
            params['InstanceGroups.member.%d.InstanceGroupId' % (k+1) ] = ig[0]
            params['InstanceGroups.member.%d.InstanceCount' % (k+1) ] = ig[1]

        return self.get_object('ModifyInstanceGroups', params,
                               ModifyInstanceGroupsResponse, verb='POST')

    def run_jobflow(self, name, log_uri=None, ec2_keyname=None,
                    availability_zone=None,
                    master_instance_type='m1.small',
                    slave_instance_type='m1.small', num_instances=1,
                    action_on_failure='TERMINATE_JOB_FLOW', keep_alive=False,
                    enable_debugging=False,
                    hadoop_version=None,
                    steps=[],
                    bootstrap_actions=[],
                    instance_groups=None,
                    additional_info=None,
                    ami_version=None,
                    api_params=None):
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
        :param keep_alive: Denotes whether the cluster should stay
            alive upon completion
            
        :type enable_debugging: bool
        :param enable_debugging: Denotes whether AWS console debugging
            should be enabled.

        :type hadoop_version: str
        :param hadoop_version: Version of Hadoop to use. This no longer
        defaults to '0.20' and now uses the AMI default. 

        :type steps: list(boto.emr.Step)
        :param steps: List of steps to add with the job
        
        :type bootstrap_actions: list(boto.emr.BootstrapAction)
        :param bootstrap_actions: List of bootstrap actions that run
            before Hadoop starts.
            
        :type instance_groups: list(boto.emr.InstanceGroup)
        :param instance_groups: Optional list of instance groups to
            use when creating this job.
            NB: When provided, this argument supersedes num_instances
            and master/slave_instance_type.
                
        :type ami_version: str
        :param ami_version: Amazon Machine Image (AMI) version to use
            for instances. Values accepted by EMR are '1.0', '2.0', and
            'latest'; EMR currently defaults to '1.0' if you don't set
            'ami_version'.
            
        :type additional_info: JSON str
        :param additional_info: A JSON string for selecting additional features

        :type api_params: dict
        :param api_params: a dictionary of additional parameters to pass
            directly to the EMR API (so you don't have to upgrade boto to
            use new EMR features). You can also delete an API parameter
            by setting it to None.

        :rtype: str
        :return: The jobflow id
        """
        params = {}
        if action_on_failure:
            params['ActionOnFailure'] = action_on_failure
        if log_uri:
            params['LogUri'] = log_uri
        params['Name'] = name

        # Common instance args
        common_params = self._build_instance_common_args(ec2_keyname,
                                                         availability_zone,
                                                         keep_alive,
                                                         hadoop_version)
        params.update(common_params)

        # NB: according to the AWS API's error message, we must
        # "configure instances either using instance count, master and
        # slave instance type or instance groups but not both."
        #
        # Thus we switch here on the truthiness of instance_groups.
        if not instance_groups:
            # Instance args (the common case)
            instance_params = self._build_instance_count_and_type_args(
                                                        master_instance_type,
                                                        slave_instance_type,
                                                        num_instances)
            params.update(instance_params)
        else:
            # Instance group args (for spot instances or a heterogenous cluster)
            list_args = self._build_instance_group_list_args(instance_groups)
            instance_params = dict(
                ('Instances.%s' % k, v) for k, v in list_args.iteritems()
                )
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

        if ami_version:
            params['AmiVersion'] = ami_version

        if additional_info is not None:
            params['AdditionalInfo'] = additional_info

        if api_params:
            for key, value in api_params.iteritems():
                if value is None:
                    params.pop(key, None)
                else:
                    params[key] = value

        response = self.get_object(
            'RunJobFlow', params, RunJobFlowResponse, verb='POST')
        return response.jobflowid

    def set_termination_protection(self, jobflow_id,
                                   termination_protection_status):
        """
        Set termination protection on specified Elastic MapReduce job flows

        :type jobflow_ids: list or str
        :param jobflow_ids: A list of job flow IDs
        
        :type termination_protection_status: bool
        :param termination_protection_status: Termination protection status
        """
        assert termination_protection_status in (True, False)

        params = {}
        params['TerminationProtected'] = (termination_protection_status and "true") or "false"
        self.build_list_params(params, [jobflow_id], 'JobFlowIds.member')

        return self.get_status('SetTerminationProtection', params, verb='POST')


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
                params['BootstrapActions.member.%s.%s' % (i + 1, key)] = value
        return params

    def _build_step_list(self, steps):
        if type(steps) != types.ListType:
            steps = [steps]

        params = {}
        for i, step in enumerate(steps):
            for key, value in step.iteritems():
                params['Steps.member.%s.%s' % (i+1, key)] = value
        return params

    def _build_instance_common_args(self, ec2_keyname, availability_zone,
                                    keep_alive, hadoop_version):
        """
        Takes a number of parameters used when starting a jobflow (as
        specified in run_jobflow() above). Returns a comparable dict for
        use in making a RunJobFlow request.
        """
        params = {
            'Instances.KeepJobFlowAliveWhenNoSteps' : str(keep_alive).lower(),
        }

        if hadoop_version:
            params['Instances.HadoopVersion'] = hadoop_version
        if ec2_keyname:
            params['Instances.Ec2KeyName'] = ec2_keyname
        if availability_zone:
            params['Instances.Placement.AvailabilityZone'] = availability_zone

        return params

    def _build_instance_count_and_type_args(self, master_instance_type,
                                            slave_instance_type, num_instances):
        """
        Takes a master instance type (string), a slave instance type
        (string), and a number of instances. Returns a comparable dict
        for use in making a RunJobFlow request.
        """
        params = {
            'Instances.MasterInstanceType' : master_instance_type,
            'Instances.SlaveInstanceType' : slave_instance_type,
            'Instances.InstanceCount' : num_instances,
            }
        return params

    def _build_instance_group_args(self, instance_group):
        """
        Takes an InstanceGroup; returns a dict that, when its keys are
        properly prefixed, can be used for describing InstanceGroups in
        RunJobFlow or AddInstanceGroups requests.
        """
        params = {
            'InstanceCount' : instance_group.num_instances,
            'InstanceRole' : instance_group.role,
            'InstanceType' : instance_group.type,
            'Name' : instance_group.name,
            'Market' : instance_group.market
        }
        if instance_group.market == 'SPOT':
            params['BidPrice'] = instance_group.bidprice
        return params

    def _build_instance_group_list_args(self, instance_groups):
        """
        Takes a list of InstanceGroups, or a single InstanceGroup. Returns
        a comparable dict for use in making a RunJobFlow or AddInstanceGroups
        request.
        """
        if type(instance_groups) != types.ListType:
            instance_groups = [instance_groups]

        params = {}
        for i, instance_group in enumerate(instance_groups):
            ig_dict = self._build_instance_group_args(instance_group)
            for key, value in ig_dict.iteritems():
                params['InstanceGroups.member.%d.%s' % (i+1, key)] = value
        return params
