# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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

import json
import boto
from boto.connection import AWSQueryConnection
from boto.regioninfo import RegionInfo
from boto.exception import JSONResponseError
from boto.datapipeline import exceptions


class DataPipelineConnection(AWSQueryConnection):
    """
    This is the AWS Data Pipeline API Reference. This guide provides
    descriptions and samples of the AWS Data Pipeline API.
    """
    APIVersion = "2012-10-29"
    DefaultRegionName = "us-east-1"
    DefaultRegionEndpoint = "datapipeline.us-east-1.amazonaws.com"
    ServiceName = "DataPipeline"
    ResponseError = JSONResponseError

    _faults = {
        "PipelineDeletedException": exceptions.PipelineDeletedException,
        "InvalidRequestException": exceptions.InvalidRequestException,
        "TaskNotFoundException": exceptions.TaskNotFoundException,
        "PipelineNotFoundException": exceptions.PipelineNotFoundException,
        "InternalServiceError": exceptions.InternalServiceError,
    }


    def __init__(self, **kwargs):
        region = kwargs.get('region')
        if not region:
            region = RegionInfo(self, self.DefaultRegionName,
                                self.DefaultRegionEndpoint)
        kwargs['host'] = region.endpoint
        AWSQueryConnection.__init__(self, **kwargs)
        self.region = region


    def _required_auth_capability(self):
        return ['hmac-v4']

    def activate_pipeline(self, pipeline_id):
        """
        Validates a pipeline and initiates processing. If the pipeline
        does not pass validation, activation fails.

        :type pipeline_id: string
        :param pipeline_id: The identifier of the pipeline to activate.

        """
        params = {'pipelineId': pipeline_id, }
        return self.make_request(action='ActivatePipeline',
                                 body=json.dumps(params))

    def create_pipeline(self, name, unique_id, description=None):
        """
        Creates a new empty pipeline. When this action succeeds, you can
        then use the PutPipelineDefinition action to populate the
        pipeline.

        :type name: string
        :param name: The name of the new pipeline. You can use the same name
            for multiple pipelines associated with your AWS account, because
            AWS Data Pipeline assigns each new pipeline a unique pipeline
            identifier.

        :type unique_id: string
        :param unique_id: A unique identifier that you specify. This identifier
            is not the same as the pipeline identifier assigned by AWS Data
            Pipeline. You are responsible for defining the format and ensuring
            the uniqueness of this identifier. You use this parameter to ensure
            idempotency during repeated calls to CreatePipeline. For example,
            if the first call to CreatePipeline does not return a clear
            success, you can pass in the same unique identifier and pipeline
            name combination on a subsequent call to CreatePipeline.
            CreatePipeline ensures that if a pipeline already exists with the
            same name and unique identifier, a new pipeline will not be
            created. Instead, you'll receive the pipeline identifier from the
            previous attempt. The uniqueness of the name and unique identifier
            combination is scoped to the AWS account or IAM user credentials.

        :type description: string
        :param description: The description of the new pipeline.

        """
        params = {'name': name, 'uniqueId': unique_id, }
        if description is not None:
            params['description'] = description
        return self.make_request(action='CreatePipeline',
                                 body=json.dumps(params))

    def delete_pipeline(self, pipeline_id):
        """
        Permanently deletes a pipeline, its pipeline definition and its
        run history. You cannot query or restore a deleted pipeline. AWS
        Data Pipeline will attempt to cancel instances associated with
        the pipeline that are currently being processed by task runners.
        Deleting a pipeline cannot be undone.

        :type pipeline_id: string
        :param pipeline_id: The identifier of the pipeline to be deleted.

        """
        params = {'pipelineId': pipeline_id, }
        return self.make_request(action='DeletePipeline',
                                 body=json.dumps(params))

    def describe_objects(self, object_ids, pipeline_id, marker=None,
                         evaluate_expressions=None):
        """
        Returns the object definitions for a set of objects associated
        with the pipeline. Object definitions are composed of a set of
        fields that define the properties of the object.

        :type object_ids: list
        :param object_ids: Identifiers of the pipeline objects that contain the
            definitions to be described. You can pass as many as 25 identifiers
            in a single call to DescribeObjects

        :type marker: string
        :param marker: The starting point for the results to be returned. The
            first time you call DescribeObjects, this value should be empty. As
            long as the action returns HasMoreResults as True, you can call
            DescribeObjects again and pass the marker value from the response
            to retrieve the next set of results.

        :type pipeline_id: string
        :param pipeline_id: Identifier of the pipeline that contains the object
            definitions.

        :type evaluate_expressions: boolean
        :param evaluate_expressions:

        """
        params = {
            'objectIds': object_ids,
            'pipelineId': pipeline_id,
        }
        if marker is not None:
            params['marker'] = marker
        if evaluate_expressions is not None:
            params['evaluateExpressions'] = evaluate_expressions
        return self.make_request(action='DescribeObjects',
                                 body=json.dumps(params))

    def describe_pipelines(self, pipeline_ids):
        """
        Retrieve metadata about one or more pipelines. The information
        retrieved includes the name of the pipeline, the pipeline
        identifier, its current state, and the user account that owns
        the pipeline. Using account credentials, you can retrieve
        metadata about pipelines that you or your IAM users have
        created. If you are using an IAM user account, you can retrieve
        metadata about only those pipelines you have read permission
        for.

        :type pipeline_ids: list
        :param pipeline_ids: Identifiers of the pipelines to describe. You can
            pass as many as 25 identifiers in a single call to
            DescribePipelines. You can obtain pipeline identifiers by calling
            ListPipelines.

        """
        params = {'pipelineIds': pipeline_ids, }
        return self.make_request(action='DescribePipelines',
                                 body=json.dumps(params))

    def evaluate_expression(self, pipeline_id, expression, object_id):
        """
        Evaluates a string in the context of a specified object. A task
        runner can use this action to evaluate SQL queries stored in
        Amazon S3.

        :type pipeline_id: string
        :param pipeline_id: The identifier of the pipeline.

        :type expression: string
        :param expression: The expression to evaluate.

        :type object_id: string
        :param object_id: The identifier of the object.

        """
        params = {
            'pipelineId': pipeline_id,
            'expression': expression,
            'objectId': object_id,
        }
        return self.make_request(action='EvaluateExpression',
                                 body=json.dumps(params))

    def get_pipeline_definition(self, pipeline_id, version=None):
        """
        Returns the definition of the specified pipeline. You can call
        GetPipelineDefinition to retrieve the pipeline definition you
        provided using PutPipelineDefinition.

        :type pipeline_id: string
        :param pipeline_id: The identifier of the pipeline.

        :type version: string
        :param version: The version of the pipeline definition to retrieve.

        """
        params = {'pipelineId': pipeline_id, }
        if version is not None:
            params['version'] = version
        return self.make_request(action='GetPipelineDefinition',
                                 body=json.dumps(params))

    def list_pipelines(self, marker=None):
        """
        Returns a list of pipeline identifiers for all active pipelines.
        Identifiers are returned only for pipelines you have permission
        to access.

        :type marker: string
        :param marker: The starting point for the results to be returned. The
            first time you call ListPipelines, this value should be empty. As
            long as the action returns HasMoreResults as True, you can call
            ListPipelines again and pass the marker value from the response to
            retrieve the next set of results.

        """
        params = {}
        if marker is not None:
            params['marker'] = marker
        return self.make_request(action='ListPipelines',
                                 body=json.dumps(params))

    def poll_for_task(self, worker_group, hostname=None,
                      instance_identity=None):
        """
        Task runners call this action to receive a task to perform from
        AWS Data Pipeline. The task runner specifies which tasks it can
        perform by setting a value for the workerGroup parameter of the
        PollForTask call. The task returned by PollForTask may come from
        any of the pipelines that match the workerGroup value passed in
        by the task runner and that was launched using the IAM user
        credentials specified by the task runner.

        :type worker_group: string
        :param worker_group: Indicates the type of task the task runner is
            configured to accept and process. The worker group is set as a
            field on objects in the pipeline when they are created. You can
            only specify a single value for workerGroup in the call to
            PollForTask. There are no wildcard values permitted in workerGroup,
            the string must be an exact, case-sensitive, match.

        :type hostname: string
        :param hostname: The public DNS name of the calling task runner.

        :type instance_identity: structure
        :param instance_identity: Identity information for the Amazon EC2
            instance that is hosting the task runner. You can get this value by
            calling the URI, http://169.254.169.254/latest/meta-data/instance-
            id, from the EC2 instance. For more information, go to Instance
            Metadata in the Amazon Elastic Compute Cloud User Guide. Passing in
            this value proves that your task runner is running on an EC2
            instance, and ensures the proper AWS Data Pipeline service charges
            are applied to your pipeline.

        """
        params = {'workerGroup': worker_group, }
        if hostname is not None:
            params['hostname'] = hostname
        if instance_identity is not None:
            params['instanceIdentity'] = instance_identity
        return self.make_request(action='PollForTask',
                                 body=json.dumps(params))

    def put_pipeline_definition(self, pipeline_objects, pipeline_id):
        """
        Adds tasks, schedules, and preconditions that control the
        behavior of the pipeline. You can use PutPipelineDefinition to
        populate a new pipeline or to update an existing pipeline that
        has not yet been activated.

        :type pipeline_objects: list
        :param pipeline_objects: The objects that define the pipeline. These
            will overwrite the existing pipeline definition.

        :type pipeline_id: string
        :param pipeline_id: The identifier of the pipeline to be configured.

        """
        params = {
            'pipelineObjects': pipeline_objects,
            'pipelineId': pipeline_id,
        }
        return self.make_request(action='PutPipelineDefinition',
                                 body=json.dumps(params))

    def query_objects(self, pipeline_id, sphere, marker=None, query=None,
                      limit=None):
        """
        Queries a pipeline for the names of objects that match a
        specified set of conditions.

        :type marker: string
        :param marker: The starting point for the results to be returned. The
            first time you call QueryObjects, this value should be empty. As
            long as the action returns HasMoreResults as True, you can call
            QueryObjects again and pass the marker value from the response to
            retrieve the next set of results.

        :type query: structure
        :param query: Query that defines the objects to be returned. The Query
            object can contain a maximum of ten selectors. The conditions in
            the query are limited to top-level String fields in the object.
            These filters can be applied to components, instances, and
            attempts.

        :type pipeline_id: string
        :param pipeline_id: Identifier of the pipeline to be queried for object
            names.

        :type limit: integer
        :param limit: Specifies the maximum number of object names that
            QueryObjects will return in a single call. The default value is
            100.

        :type sphere: string
        :param sphere: Specifies whether the query applies to components or
            instances. Allowable values: COMPONENT, INSTANCE, ATTEMPT.

        """
        params = {'pipelineId': pipeline_id, 'sphere': sphere, }
        if marker is not None:
            params['marker'] = marker
        if query is not None:
            params['query'] = query
        if limit is not None:
            params['limit'] = limit
        return self.make_request(action='QueryObjects',
                                 body=json.dumps(params))

    def report_task_progress(self, task_id):
        """
        Updates the AWS Data Pipeline service on the progress of the
        calling task runner. When the task runner is assigned a task, it
        should call ReportTaskProgress to acknowledge that it has the
        task within 2 minutes. If the web service does not recieve this
        acknowledgement within the 2 minute window, it will assign the
        task in a subsequent PollForTask call. After this initial
        acknowledgement, the task runner only needs to report progress
        every 15 minutes to maintain its ownership of the task. You can
        change this reporting time from 15 minutes by specifying a
        reportProgressTimeout field in your pipeline. If a task runner
        does not report its status after 5 minutes, AWS Data Pipeline
        will assume that the task runner is unable to process the task
        and will reassign the task in a subsequent response to
        PollForTask. task runners should call ReportTaskProgress every
        60 seconds.

        :type task_id: string
        :param task_id: Identifier of the task assigned to the task runner.
            This value is provided in the TaskObject that the service returns
            with the response for the PollForTask action.

        """
        params = {'taskId': task_id, }
        return self.make_request(action='ReportTaskProgress',
                                 body=json.dumps(params))

    def report_task_runner_heartbeat(self, taskrunner_id, worker_group=None,
                                     hostname=None):
        """
        Task runners call ReportTaskRunnerHeartbeat to indicate that
        they are operational. In the case of AWS Data Pipeline Task
        Runner launched on a resource managed by AWS Data Pipeline, the
        web service can use this call to detect when the task runner
        application has failed and restart a new instance.

        :type worker_group: string
        :param worker_group: Indicates the type of task the task runner is
            configured to accept and process. The worker group is set as a
            field on objects in the pipeline when they are created. You can
            only specify a single value for workerGroup in the call to
            ReportTaskRunnerHeartbeat. There are no wildcard values permitted
            in workerGroup, the string must be an exact, case-sensitive, match.

        :type hostname: string
        :param hostname: The public DNS name of the calling task runner.

        :type taskrunner_id: string
        :param taskrunner_id: The identifier of the task runner. This value
            should be unique across your AWS account. In the case of AWS Data
            Pipeline Task Runner launched on a resource managed by AWS Data
            Pipeline, the web service provides a unique identifier when it
            launches the application. If you have written a custom task runner,
            you should assign a unique identifier for the task runner.

        """
        params = {'taskrunnerId': taskrunner_id, }
        if worker_group is not None:
            params['workerGroup'] = worker_group
        if hostname is not None:
            params['hostname'] = hostname
        return self.make_request(action='ReportTaskRunnerHeartbeat',
                                 body=json.dumps(params))

    def set_status(self, object_ids, status, pipeline_id):
        """
        Requests that the status of an array of physical or logical
        pipeline objects be updated in the pipeline. This update may not
        occur immediately, but is eventually consistent. The status that
        can be set depends on the type of object.

        :type object_ids: list
        :param object_ids: Identifies an array of objects. The corresponding
            objects can be either physical or components, but not a mix of both
            types.

        :type status: string
        :param status: Specifies the status to be set on all the objects in
            objectIds. For components, this can be either PAUSE or RESUME. For
            instances, this can be either CANCEL, RERUN, or MARK\_FINISHED.

        :type pipeline_id: string
        :param pipeline_id: Identifies the pipeline that contains the objects.

        """
        params = {
            'objectIds': object_ids,
            'status': status,
            'pipelineId': pipeline_id,
        }
        return self.make_request(action='SetStatus',
                                 body=json.dumps(params))

    def set_task_status(self, task_id, task_status, error_code=None,
                        error_message=None, error_stack_trace=None):
        """
        Notifies AWS Data Pipeline that a task is completed and provides
        information about the final status. The task runner calls this
        action regardless of whether the task was sucessful. The task
        runner does not need to call SetTaskStatus for tasks that are
        canceled by the web service during a call to ReportTaskProgress.

        :type error_code: integer
        :param error_code: If an error occurred during the task, specifies a
            numerical value that represents the error. This value is set on the
            physical attempt object. It is used to display error information to
            the user. The web service does not parse this value.

        :type error_message: string
        :param error_message: If an error occurred during the task, specifies a
            text description of the error. This value is set on the physical
            attempt object. It is used to display error information to the
            user. The web service does not parse this value.

        :type error_stack_trace: string
        :param error_stack_trace: If an error occurred during the task,
            specifies the stack trace associated with the error. This value is
            set on the physical attempt object. It is used to display error
            information to the user. The web service does not parse this value.

        :type task_id: string
        :param task_id: Identifies the task assigned to the task runner. This
            value is set in the TaskObject that is returned by the PollForTask
            action.

        :type task_status: string
        :param task_status: If FINISHED, the task successfully completed. If
            FAILED the task ended unsuccessfully. The FALSE value is used by
            preconditions.

        """
        params = {'taskId': task_id, 'taskStatus': task_status, }
        if error_code is not None:
            params['errorCode'] = error_code
        if error_message is not None:
            params['errorMessage'] = error_message
        if error_stack_trace is not None:
            params['errorStackTrace'] = error_stack_trace
        return self.make_request(action='SetTaskStatus',
                                 body=json.dumps(params))

    def validate_pipeline_definition(self, pipeline_objects, pipeline_id):
        """
        Tests the pipeline definition with a set of validation checks to
        ensure that it is well formed and can run without error.

        :type pipeline_objects: list
        :param pipeline_objects: A list of objects that define the pipeline
            changes to validate against the pipeline.

        :type pipeline_id: string
        :param pipeline_id: Identifies the pipeline whose definition is to be
            validated.

        """
        params = {
            'pipelineObjects': pipeline_objects,
            'pipelineId': pipeline_id,
        }
        return self.make_request(action='ValidatePipelineDefinition',
                                 body=json.dumps(params))

    def make_request(self, action, body):
        headers = {
            'X-Amz-Target': '%s.%s' % (self.ServiceName, action),
            'Host': self.region.endpoint,
            'Content-Type': 'application/x-amz-json-1.1',
            'Content-Length': str(len(body)),
        }
        http_request = self.build_base_http_request(
            method='POST', path='/', auth_path='/', params={},
            headers=headers, data=body)
        response = self._mexe(http_request, sender=None,
                              override_num_retries=10)
        response_body = response.read()
        boto.log.debug(response_body)
        if response.status == 200:
            if response_body:
                return json.loads(response_body)
        else:
            json_body = json.loads(response_body)
            fault_name = json_body.get('__type', None)
            exception_class = self._faults.get(fault_name, self.ResponseError)
            raise exception_class(response.status, response.reason,
                                  body=json_body)

