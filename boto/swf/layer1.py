# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.
# All Rights Reserved
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

import boto
from boto.connection import AWSAuthConnection
from boto.provider import Provider
from boto.exception import SWFResponseError
from boto.swf import exceptions as swf_exceptions

import time
try:
    import simplejson as json
except ImportError:
    import json

#
# To get full debug output, uncomment the following line and set the
# value of Debug to be 2
#
#boto.set_stream_logger('swf')
Debug = 0


class Layer1(AWSAuthConnection):
    """
    Low-level interface to Simple WorkFlow Service.
    """

    DefaultRegionName = 'us-east-1'
    """The default region name for Simple Workflow."""

    ServiceName = 'com.amazonaws.swf.service.model.SimpleWorkflowService'
    """The name of the Service"""

    # In some cases, the fault response __type value is mapped to
    # an exception class more specific than SWFResponseError.
    _fault_excp = {
        'com.amazonaws.swf.base.model#DomainAlreadyExistsFault':
            swf_exceptions.SWFDomainAlreadyExistsError,
        'com.amazonaws.swf.base.model#LimitExceededFault':
            swf_exceptions.SWFLimitExceededError,
        'com.amazonaws.swf.base.model#OperationNotPermittedFault':
            swf_exceptions.SWFOperationNotPermittedError,
        'com.amazonaws.swf.base.model#TypeAlreadyExistsFault':
            swf_exceptions.SWFTypeAlreadyExistsError,
        'com.amazonaws.swf.base.model#WorkflowExecutionAlreadyStartedFault':
            swf_exceptions.SWFWorkflowExecutionAlreadyStartedError,
    }

    ResponseError = SWFResponseError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 debug=0, session_token=None, region=None):
        if not region:
            region_name = boto.config.get('SWF', 'region',
                                          self.DefaultRegionName)
            for reg in boto.swf.regions():
                if reg.name == region_name:
                    region = reg
                    break

        self.region = region
        AWSAuthConnection.__init__(self, self.region.endpoint,
                                   aws_access_key_id, aws_secret_access_key,
                                   is_secure, port, proxy, proxy_port,
                                   debug, session_token)

    def _required_auth_capability(self):
        return ['hmac-v3-http']

    def make_request(self, action, body='', object_hook=None):
        """
        :raises: ``SWFResponseError`` if response status is not 200.
        """
        headers = {'X-Amz-Target': '%s.%s' % (self.ServiceName, action),
                   'Host': self.region.endpoint,
                   'Content-Type': 'application/json; charset=UTF-8',
                   'Content-Encoding': 'amz-1.0',
                   'Content-Length': str(len(body))}
        http_request = self.build_base_http_request('POST', '/', '/',
                                                    {}, headers, body, None)
        response = self._mexe(http_request, sender=None,
                              override_num_retries=10)
        response_body = response.read()
        boto.log.debug(response_body)
        if response.status == 200:
            if response_body:
                return json.loads(response_body, object_hook=object_hook)
            else:
                return None
        else:
            json_body = json.loads(response_body)
            fault_name = json_body.get('__type', None)
            # Certain faults get mapped to more specific exception classes.
            excp_cls = self._fault_excp.get(fault_name, self.ResponseError)
            raise excp_cls(response.status, response.reason, body=json_body)

    # Actions related to Activities

    def poll_for_activity_task(self, domain, task_list, identity=None):
        """
        Used by workers to get an ActivityTask from the specified
        activity taskList. This initiates a long poll, where the
        service holds the HTTP connection open and responds as soon as
        a task becomes available. The maximum time the service holds
        on to the request before responding is 60 seconds. If no task
        is available within 60 seconds, the poll will return an empty
        result. An empty result, in this context, means that an
        ActivityTask is returned, but that the value of taskToken is
        an empty string. If a task is returned, the worker should use
        its type to identify and process it correctly.

        :type domain: string
        :param domain: The name of the domain that contains the task
            lists being polled.

        :type task_list: string
        :param task_list: Specifies the task list to poll for activity tasks.

        :type identity: string
        :param identity: Identity of the worker making the request, which
            is recorded in the ActivityTaskStarted event in the workflow
            history. This enables diagnostic tracing when problems arise.
            The form of this identity is user defined.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain, 'taskList': {'name': task_list}}
        if identity:
            data['identity'] = identity
        json_input = json.dumps(data)
        return self.make_request('PollForActivityTask', json_input)

    def respond_activity_task_completed(self, task_token, result=None):
        """
        Used by workers to tell the service that the ActivityTask
        identified by the taskToken completed successfully with a
        result (if provided).

        :type task_token: string
        :param task_token: The taskToken of the ActivityTask.

        :type result: string
        :param result: The result of the activity task. It is a free
            form string that is implementation specific.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'taskToken': task_token}
        if result:
            data['result'] = result
        json_input = json.dumps(data)
        return self.make_request('RespondActivityTaskCompleted', json_input)

    def respond_activity_task_failed(self, task_token,
                                     details=None, reason=None):
        """
        Used by workers to tell the service that the ActivityTask
        identified by the taskToken has failed with reason (if
        specified).

        :type task_token: string
        :param task_token: The taskToken of the ActivityTask.

        :type details: string
        :param details: Optional detailed information about the failure.

        :type reason: string
        :param reason: Description of the error that may assist in diagnostics.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'taskToken': task_token}
        if details:
            data['details'] = details
        if reason:
            data['reason'] = reason
        json_input = json.dumps(data)
        return self.make_request('RespondActivityTaskFailed', json_input)

    def respond_activity_task_canceled(self, task_token, details=None):
        """
        Used by workers to tell the service that the ActivityTask
        identified by the taskToken was successfully
        canceled. Additional details can be optionally provided using
        the details argument.

        :type task_token: string
        :param task_token: The taskToken of the ActivityTask.

        :type details: string
        :param details: Optional detailed information about the failure.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'taskToken': task_token}
        if details:
            data['details'] = details
        json_input = json.dumps(data)
        return self.make_request('RespondActivityTaskCanceled', json_input)

    def record_activity_task_heartbeat(self, task_token, details=None):
        """
        Used by activity workers to report to the service that the
        ActivityTask represented by the specified taskToken is still
        making progress. The worker can also (optionally) specify
        details of the progress, for example percent complete, using
        the details parameter. This action can also be used by the
        worker as a mechanism to check if cancellation is being
        requested for the activity task. If a cancellation is being
        attempted for the specified task, then the boolean
        cancelRequested flag returned by the service is set to true.

        :type task_token: string
        :param task_token: The taskToken of the ActivityTask.

        :type details: string
        :param details: If specified, contains details about the
            progress of the task.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'taskToken': task_token}
        if details:
            data['details'] = details
        json_input = json.dumps(data)
        return self.make_request('RecordActivityTaskHeartbeat', json_input)

    # Actions related to Deciders

    def poll_for_decision_task(self, domain, task_list, identity=None,
                               maximum_page_size=None,
                               next_page_token=None,
                               reverse_order=None):
        """
        Used by deciders to get a DecisionTask from the specified
        decision taskList. A decision task may be returned for any
        open workflow execution that is using the specified task
        list. The task includes a paginated view of the history of the
        workflow execution. The decider should use the workflow type
        and the history to determine how to properly handle the task.

        :type domain: string
        :param domain: The name of the domain containing the task
            lists to poll.

        :type task_list: string
        :param task_list: Specifies the task list to poll for decision tasks.

        :type identity: string
        :param identity: Identity of the decider making the request,
            which is recorded in the DecisionTaskStarted event in the
            workflow history. This enables diagnostic tracing when
            problems arise. The form of this identity is user defined.

        :type maximum_page_size: integer :param maximum_page_size: The
            maximum number of history events returned in each page. The
            default is 100, but the caller can override this value to a
            page size smaller than the default. You cannot specify a page
            size greater than 100.

        :type next_page_token: string
        :param next_page_token: If on a previous call to this method a
            NextPageToken was returned, the results are being paginated.
            To get the next page of results, repeat the call with the
            returned token and all other arguments unchanged.

        :type reverse_order: boolean
        :param reverse_order: When set to true, returns the events in
            reverse order. By default the results are returned in
            ascending order of the eventTimestamp of the events.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain, 'taskList': {'name': task_list}}
        if identity:
            data['identity'] = identity
        if maximum_page_size:
            data['maximumPageSize'] = maximum_page_size
        if next_page_token:
            data['nextPageToken'] = next_page_token
        if reverse_order:
            data['reverseOrder'] = 'true'
        json_input = json.dumps(data)
        return self.make_request('PollForDecisionTask', json_input)

    def respond_decision_task_completed(self, task_token,
                                        decisions=None,
                                        execution_context=None):
        """
        Used by deciders to tell the service that the DecisionTask
        identified by the taskToken has successfully completed.
        The decisions argument specifies the list of decisions
        made while processing the task.

        :type task_token: string
        :param task_token: The taskToken of the ActivityTask.

        :type decisions: list
        :param decisions: The list of decisions (possibly empty) made by
            the decider while processing this decision task. See the docs
            for the Decision structure for details.

        :type execution_context: string
        :param execution_context: User defined context to add to
            workflow execution.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'taskToken': task_token}
        if decisions:
            data['decisions'] = decisions
        if execution_context:
            data['executionContext'] = execution_context
        json_input = json.dumps(data)
        return self.make_request('RespondDecisionTaskCompleted', json_input)

    def request_cancel_workflow_execution(self, domain, workflow_id,
                                          run_id=None):
        """
        Records a WorkflowExecutionCancelRequested event in the
        currently running workflow execution identified by the given
        domain, workflowId, and runId. This logically requests the
        cancellation of the workflow execution as a whole. It is up to
        the decider to take appropriate actions when it receives an
        execution history with this event.

        :type domain: string
        :param domain: The name of the domain containing the workflow
            execution to cancel.

        :type run_id: string
        :param run_id: The runId of the workflow execution to cancel.

        :type workflow_id: string
        :param workflow_id: The workflowId of the workflow execution
            to cancel.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain, 'workflowId': workflow_id}
        if run_id:
            data['runId'] = run_id
        json_input = json.dumps(data)
        return self.make_request('RequestCancelWorkflowExecution', json_input)

    def start_workflow_execution(self, domain, workflow_id,
                                 workflow_name, workflow_version,
                                 task_list=None, child_policy=None,
                                 execution_start_to_close_timeout=None,
                                 input=None, tag_list=None,
                                 task_start_to_close_timeout=None):
        """
        Starts an execution of the workflow type in the specified
        domain using the provided workflowId and input data.

        :type domain: string
        :param domain: The name of the domain in which the workflow
            execution is created.

        :type workflow_id: string
        :param workflow_id: The user defined identifier associated with
            the workflow execution. You can use this to associate a
            custom identifier with the workflow execution. You may
            specify the same identifier if a workflow execution is
            logically a restart of a previous execution. You cannot
            have two open workflow executions with the same workflowId
            at the same time.

        :type workflow_name: string
        :param workflow_name: The name of the workflow type.

        :type workflow_version: string
        :param workflow_version: The version of the workflow type.

        :type task_list: string
        :param task_list: The task list to use for the decision tasks
            generated for this workflow execution. This overrides the
            defaultTaskList specified when registering the workflow type.

        :type child_policy: string
        :param child_policy: If set, specifies the policy to use for the
            child workflow executions of this workflow execution if it
            is terminated, by calling the TerminateWorkflowExecution
            action explicitly or due to an expired timeout. This policy
            overrides the default child policy specified when registering
            the workflow type using RegisterWorkflowType. The supported
            child policies are:

             * TERMINATE: the child executions will be terminated.
             * REQUEST_CANCEL: a request to cancel will be attempted
                 for each child execution by recording a
                 WorkflowExecutionCancelRequested event in its history.
                 It is up to the decider to take appropriate actions
                 when it receives an execution history with this event.
             * ABANDON: no action will be taken. The child executions
                 will continue to run.

        :type execution_start_to_close_timeout: string
        :param execution_start_to_close_timeout: The total duration for
            this workflow execution. This overrides the
            defaultExecutionStartToCloseTimeout specified when
            registering the workflow type.

        :type input: string
        :param input: The input for the workflow
            execution. This is a free form string which should be
            meaningful to the workflow you are starting. This input is
            made available to the new workflow execution in the
            WorkflowExecutionStarted history event.

        :type tag_list: list :param tag_list: The list of tags to
            associate with the workflow execution. You can specify a
            maximum of 5 tags. You can list workflow executions with a
            specific tag by calling list_open_workflow_executions or
            list_closed_workflow_executions and specifying a TagFilter.

        :type task_start_to_close_timeout: string :param
        task_start_to_close_timeout: Specifies the maximum duration of
            decision tasks for this workflow execution. This parameter
            overrides the defaultTaskStartToCloseTimout specified when
            registering the workflow type using register_workflow_type.

        :raises: UnknownResourceFault, TypeDeprecatedFault,
            SWFWorkflowExecutionAlreadyStartedError, SWFLimitExceededError,
            SWFOperationNotPermittedError, DefaultUndefinedFault
        """
        data = {'domain': domain, 'workflowId': workflow_id}
        data['workflowType'] = {'name': workflow_name,
                                'version': workflow_version}
        if task_list:
            data['taskList'] = {'name': task_list}
        if child_policy:
            data['childPolicy'] = child_policy
        if execution_start_to_close_timeout:
            data['executionStartToCloseTimeout'] = execution_start_to_close_timeout
        if input:
            data['input'] = input
        if tag_list:
            data['tagList'] = tag_list
        if task_start_to_close_timeout:
            data['taskStartToCloseTimeout'] = task_start_to_close_timeout
        json_input = json.dumps(data)
        return self.make_request('StartWorkflowExecution', json_input)

    def signal_workflow_execution(self, domain, signal_name, workflow_id,
                                  input=None, run_id=None):
        """
        Records a WorkflowExecutionSignaled event in the workflow
        execution history and creates a decision task for the workflow
        execution identified by the given domain, workflowId and
        runId. The event is recorded with the specified user defined
        signalName and input (if provided).

        :type domain: string
        :param domain: The name of the domain containing the workflow
            execution to signal.

        :type signal_name: string
        :param signal_name: The name of the signal. This name must be
            meaningful to the target workflow.

        :type workflow_id: string
        :param workflow_id: The workflowId of the workflow execution
            to signal.

        :type input: string
        :param input: Data to attach to the WorkflowExecutionSignaled
            event in the target workflow execution's history.

        :type run_id: string
        :param run_id: The runId of the workflow execution to signal.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain, 'signalName': signal_name,
                'workflowId': workflow_id}
        if input:
            data['input'] = input
        if run_id:
            data['runId'] = run_id
        json_input = json.dumps(data)
        return self.make_request('SignalWorkflowExecution', json_input)

    def terminate_workflow_execution(self, domain, workflow_id,
                                     child_policy=None, details=None,
                                     reason=None, run_id=None):
        """
        Records a WorkflowExecutionTerminated event and forces closure
        of the workflow execution identified by the given domain,
        runId, and workflowId. The child policy, registered with the
        workflow type or specified when starting this execution, is
        applied to any open child workflow executions of this workflow
        execution.

        :type domain: string
        :param domain: The domain of the workflow execution to terminate.

        :type workflow_id: string
        :param workflow_id: The workflowId of the workflow execution
            to terminate.

        :type child_policy: string
        :param child_policy: If set, specifies the policy to use for
            the child workflow executions of the workflow execution being
            terminated. This policy overrides the child policy specified
            for the workflow execution at registration time or when
            starting the execution. The supported child policies are:

            * TERMINATE: the child executions will be terminated.

            * REQUEST_CANCEL: a request to cancel will be attempted
              for each child execution by recording a
              WorkflowExecutionCancelRequested event in its
              history. It is up to the decider to take appropriate
              actions when it receives an execution history with this
              event.

            * ABANDON: no action will be taken. The child executions
              will continue to run.

        :type details: string
        :param details: Optional details for terminating the
            workflow execution.

        :type reason: string
        :param reason: An optional descriptive reason for terminating
            the workflow execution.

        :type run_id: string
        :param run_id: The runId of the workflow execution to terminate.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain, 'workflowId': workflow_id}
        if child_policy:
            data['childPolicy'] = child_policy
        if details:
            data['details'] = details
        if reason:
            data['reason'] = reason
        if run_id:
            data['runId'] = run_id
        json_input = json.dumps(data)
        return self.make_request('TerminateWorkflowExecution', json_input)

# Actions related to Administration

## Activity Management

    def register_activity_type(self, domain, name, version, task_list=None,
                               default_task_heartbeat_timeout=None,
                               default_task_schedule_to_close_timeout=None,
                               default_task_schedule_to_start_timeout=None,
                               default_task_start_to_close_timeout=None,
                               description=None):
        """
        Registers a new activity type along with its configuration
        settings in the specified domain.

        :type domain: string
        :param domain: The name of the domain in which this activity is
            to be registered.

        :type name: string
        :param name: The name of the activity type within the domain.

        :type version: string
        :param version: The version of the activity type.

        :type task_list: string
        :param task_list: If set, specifies the default task list to
            use for scheduling tasks of this activity type. This default
            task list is used if a task list is not provided when a task
            is scheduled through the schedule_activity_task Decision.

        :type default_task_heartbeat_timeout: string
        :param default_task_heartbeat_timeout: If set, specifies the
            default maximum time before which a worker processing a task
            of this type must report progress by calling
            RecordActivityTaskHeartbeat. If the timeout is exceeded, the
            activity task is automatically timed out. This default can be
            overridden when scheduling an activity task using the
            ScheduleActivityTask Decision. If the activity worker
            subsequently attempts to record a heartbeat or returns a
            result, the activity worker receives an UnknownResource
            fault. In this case, Amazon SWF no longer considers the
            activity task to be valid; the activity worker should clean up
            the activity task.no docs

        :type default_task_schedule_to_close_timeout: string
        :param default_task_schedule_to_close_timeout: If set,
            specifies the default maximum duration for a task of this
            activity type. This default can be overridden when scheduling
            an activity task using the ScheduleActivityTask Decision.no
            docs

        :type default_task_schedule_to_start_timeout: string
        :param default_task_schedule_to_start_timeout: If set,
            specifies the default maximum duration that a task of this
            activity type can wait before being assigned to a worker. This
            default can be overridden when scheduling an activity task
            using the ScheduleActivityTask Decision.

        :type default_task_start_to_close_timeout: string
        :param default_task_start_to_close_timeout: If set, specifies
            the default maximum duration that a worker can take to process
            tasks of this activity type. This default can be overridden
            when scheduling an activity task using the
            ScheduleActivityTask Decision.

        :type description: string
        :param description: A textual description of the activity type.

        :raises: SWFTypeAlreadyExistsError, SWFLimitExceededError,
            UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain,
                'name': name,
                'version': version}
        if task_list:
            data['defaultTaskList'] = {'name': task_list}
        if default_task_heartbeat_timeout:
            data['defaultTaskHeartbeatTimeout'] = default_task_heartbeat_timeout
        if default_task_schedule_to_close_timeout:
            data['defaultTaskScheduleToCloseTimeout'] = default_task_schedule_to_close_timeout
        if default_task_schedule_to_start_timeout:
            data['defaultTaskScheduleToStartTimeout'] = default_task_schedule_to_start_timeout
        if default_task_start_to_close_timeout:
            data['defaultTaskStartToCloseTimeout'] = default_task_start_to_close_timeout
        if description:
            data['description'] = description
        json_input = json.dumps(data)
        return self.make_request('RegisterActivityType', json_input)

    def deprecate_activity_type(self, domain, activity_name, activity_version):
        """
        Returns information about the specified activity type. This
        includes configuration settings provided at registration time
        as well as other general information about the type.

        :type domain: string
        :param domain: The name of the domain in which the activity
            type is registered.

        :type activity_name: string
        :param activity_name: The name of this activity.

        :type activity_version: string
        :param activity_version: The version of this activity.

        :raises: UnknownResourceFault, TypeDeprecatedFault,
            SWFOperationNotPermittedError
        """
        data = {'domain': domain}
        data['activityType'] = {'name': activity_name,
                                'version': activity_version}
        json_input = json.dumps(data)
        return self.make_request('DeprecateActivityType', json_input)

## Workflow Management

    def register_workflow_type(self, domain, name, version,
                               task_list=None,
                               default_child_policy=None,
                               default_execution_start_to_close_timeout=None,
                               default_task_start_to_close_timeout=None,
                               description=None):
        """
        Registers a new workflow type and its configuration settings
        in the specified domain.

        :type domain: string
        :param domain: The name of the domain in which to register
            the workflow type.

        :type name: string
        :param name: The name of the workflow type.

        :type version: string
        :param version: The version of the workflow type.

        :type task_list: list of name, version of tasks
        :param task_list: If set, specifies the default task list to use
            for scheduling decision tasks for executions of this workflow
            type. This default is used only if a task list is not provided
            when starting the execution through the StartWorkflowExecution
            Action or StartChildWorkflowExecution Decision.

        :type default_child_policy: string

        :param default_child_policy: If set, specifies the default
            policy to use for the child workflow executions when a
            workflow execution of this type is terminated, by calling the
            TerminateWorkflowExecution action explicitly or due to an
            expired timeout. This default can be overridden when starting
            a workflow execution using the StartWorkflowExecution action
            or the StartChildWorkflowExecution Decision. The supported
            child policies are:

            * TERMINATE: the child executions will be terminated.

            * REQUEST_CANCEL: a request to cancel will be attempted
              for each child execution by recording a
              WorkflowExecutionCancelRequested event in its
              history. It is up to the decider to take appropriate
              actions when it receives an execution history with this
              event.

            * ABANDON: no action will be taken. The child executions
              will continue to run.no docs

        :type default_execution_start_to_close_timeout: string
        :param default_execution_start_to_close_timeout: If set,
            specifies the default maximum duration for executions of this
            workflow type. You can override this default when starting an
            execution through the StartWorkflowExecution Action or
            StartChildWorkflowExecution Decision.

        :type default_task_start_to_close_timeout: string
        :param default_task_start_to_close_timeout: If set, specifies
            the default maximum duration of decision tasks for this
            workflow type. This default can be overridden when starting a
            workflow execution using the StartWorkflowExecution action or
            the StartChildWorkflowExecution Decision.

        :type description: string
        :param description: Textual description of the workflow type.

        :raises: SWFTypeAlreadyExistsError, SWFLimitExceededError,
            UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain, 'name': name, 'version': version}
        if task_list:
            data['defaultTaskList'] = {'name': task_list}
        if default_child_policy:
            data['defaultChildPolicy'] = default_child_policy
        if default_execution_start_to_close_timeout:
            data['defaultExecutionStartToCloseTimeout'] = default_execution_start_to_close_timeout
        if default_task_start_to_close_timeout:
            data['defaultTaskStartToCloseTimeout'] = default_task_start_to_close_timeout
        if description:
            data['description'] = description
        json_input = json.dumps(data)
        return self.make_request('RegisterWorkflowType', json_input)

    def deprecate_workflow_type(self, domain, workflow_name, workflow_version):
        """
        Deprecates the specified workflow type. After a workflow type
        has been deprecated, you cannot create new executions of that
        type. Executions that were started before the type was
        deprecated will continue to run. A deprecated workflow type
        may still be used when calling visibility actions.

        :type domain: string
        :param domain: The name of the domain in which the workflow
            type is registered.

        :type workflow_name: string
        :param workflow_name: The name of the workflow type.

        :type workflow_version: string
        :param workflow_version: The version of the workflow type.

        :raises: UnknownResourceFault, TypeDeprecatedFault,
            SWFOperationNotPermittedError
        """
        data = {'domain': domain}
        data['workflowType'] = {'name': workflow_name,
                                'version': workflow_version}
        json_input = json.dumps(data)
        return self.make_request('DeprecateWorkflowType', json_input)

## Domain Management

    def register_domain(self, name,
                        workflow_execution_retention_period_in_days,
                        description=None):
        """
        Registers a new domain.

        :type name: string
        :param name: Name of the domain to register. The name must be unique.

        :type workflow_execution_retention_period_in_days: string

        :param workflow_execution_retention_period_in_days: Specifies
            the duration *in days* for which the record (including the
            history) of workflow executions in this domain should be kept
            by the service. After the retention period, the workflow
            execution will not be available in the results of visibility
            calls. If a duration of NONE is specified, the records for
            workflow executions in this domain are not retained at all.

        :type description: string
        :param description: Textual description of the domain.

        :raises: SWFDomainAlreadyExistsError, SWFLimitExceededError,
            SWFOperationNotPermittedError
        """
        data = {'name': name,
                'workflowExecutionRetentionPeriodInDays': workflow_execution_retention_period_in_days}
        if description:
            data['description'] = description
        json_input = json.dumps(data)
        return self.make_request('RegisterDomain', json_input)

    def deprecate_domain(self, name):
        """
        Deprecates the specified domain. After a domain has been
        deprecated it cannot be used to create new workflow executions
        or register new types. However, you can still use visibility
        actions on this domain. Deprecating a domain also deprecates
        all activity and workflow types registered in the
        domain. Executions that were started before the domain was
        deprecated will continue to run.

        :type name: string
        :param name: The name of the domain to deprecate.

        :raises: UnknownResourceFault, DomainDeprecatedFault,
            SWFOperationNotPermittedError
        """
        data = {'name': name}
        json_input = json.dumps(data)
        return self.make_request('DeprecateDomain', json_input)

# Visibility Actions

## Activity Visibility

    def list_activity_types(self, domain, registration_status,
                            name=None,
                            maximum_page_size=None,
                            next_page_token=None, reverse_order=None):
        """
        Returns information about all activities registered in the
        specified domain that match the specified name and
        registration status. The result includes information like
        creation date, current status of the activity, etc. The
        results may be split into multiple pages. To retrieve
        subsequent pages, make the call again using the nextPageToken
        returned by the initial call.

        :type domain: string
        :param domain: The name of the domain in which the activity
            types have been registered.

        :type registration_status: string
        :param registration_status: Specifies the registration status
            of the activity types to list.  Valid values are:

            * REGISTERED
            * DEPRECATED

        :type name: string
        :param name: If specified, only lists the activity types that
            have this name.

        :type maximum_page_size: integer
        :param maximum_page_size: The maximum number of results
            returned in each page. The default is 100, but the caller can
            override this value to a page size smaller than the
            default. You cannot specify a page size greater than 100.

        :type next_page_token: string
        :param next_page_token: If on a previous call to this method a
            NextResultToken was returned, the results have more than one
            page. To get the next page of results, repeat the call with
            the nextPageToken and keep all other arguments unchanged.

        :type reverse_order: boolean

        :param reverse_order: When set to true, returns the results in
            reverse order. By default the results are returned in
            ascending alphabetical order of the name of the activity
            types.

        :raises: SWFOperationNotPermittedError, UnknownResourceFault
        """
        data = {'domain': domain, 'registrationStatus': registration_status}
        if name:
            data['name'] = name
        if maximum_page_size:
            data['maximumPageSize'] = maximum_page_size
        if next_page_token:
            data['nextPageToken'] = next_page_token
        if reverse_order:
            data['reverseOrder'] = 'true'
        json_input = json.dumps(data)
        return self.make_request('ListActivityTypes', json_input)

    def describe_activity_type(self, domain, activity_name, activity_version):
        """
        Returns information about the specified activity type. This
        includes configuration settings provided at registration time
        as well as other general information about the type.

        :type domain: string
        :param domain: The name of the domain in which the activity
            type is registered.

        :type activity_name: string
        :param activity_name: The name of this activity.

        :type activity_version: string
        :param activity_version: The version of this activity.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain}
        data['activityType'] = {'name': activity_name,
                                'version': activity_version}
        json_input = json.dumps(data)
        return self.make_request('DescribeActivityType', json_input)

## Workflow Visibility

    def list_workflow_types(self, domain, registration_status,
                            maximum_page_size=None, name=None,
                            next_page_token=None, reverse_order=None):
        """
        Returns information about workflow types in the specified
        domain. The results may be split into multiple pages that can
        be retrieved by making the call repeatedly.

        :type domain: string
        :param domain: The name of the domain in which the workflow
            types have been registered.

        :type registration_status: string
        :param registration_status: Specifies the registration status
            of the activity types to list.  Valid values are:

            * REGISTERED
            * DEPRECATED

        :type name: string
        :param name: If specified, lists the workflow type with this name.

        :type maximum_page_size: integer
        :param maximum_page_size: The maximum number of results
            returned in each page. The default is 100, but the caller can
            override this value to a page size smaller than the
            default. You cannot specify a page size greater than 100.

        :type next_page_token: string
        :param next_page_token: If on a previous call to this method a
            NextPageToken was returned, the results are being
            paginated. To get the next page of results, repeat the call
            with the returned token and all other arguments unchanged.

        :type reverse_order: boolean
        :param reverse_order: When set to true, returns the results in
            reverse order. By default the results are returned in
            ascending alphabetical order of the name of the workflow
            types.

        :raises: SWFOperationNotPermittedError, UnknownResourceFault
        """
        data = {'domain': domain, 'registrationStatus': registration_status}
        if maximum_page_size:
            data['maximumPageSize'] = maximum_page_size
        if name:
            data['name'] = name
        if next_page_token:
            data['nextPageToken'] = next_page_token
        if reverse_order:
            data['reverseOrder'] = 'true'
        json_input = json.dumps(data)
        return self.make_request('ListWorkflowTypes', json_input)

    def describe_workflow_type(self, domain, workflow_name, workflow_version):
        """
        Returns information about the specified workflow type. This
        includes configuration settings specified when the type was
        registered and other information such as creation date,
        current status, etc.

        :type domain: string
        :param domain: The name of the domain in which this workflow
            type is registered.

        :type workflow_name: string
        :param workflow_name: The name of the workflow type.

        :type workflow_version: string
        :param workflow_version: The version of the workflow type.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain}
        data['workflowType'] = {'name': workflow_name,
                                'version': workflow_version}
        json_input = json.dumps(data)
        return self.make_request('DescribeWorkflowType', json_input)

## Workflow Execution Visibility

    def describe_workflow_execution(self, domain, run_id, workflow_id):
        """
        Returns information about the specified workflow execution
        including its type and some statistics.

        :type domain: string
        :param domain: The name of the domain containing the
            workflow execution.

        :type run_id: string
        :param run_id: A system generated unique identifier for the
            workflow execution.

        :type workflow_id: string
        :param workflow_id: The user defined identifier associated
            with the workflow execution.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain}
        data['execution'] = {'runId': run_id, 'workflowId': workflow_id}
        json_input = json.dumps(data)
        return self.make_request('DescribeWorkflowExecution', json_input)

    def get_workflow_execution_history(self, domain, run_id, workflow_id,
                                       maximum_page_size=None,
                                       next_page_token=None,
                                       reverse_order=None):
        """
        Returns the history of the specified workflow execution. The
        results may be split into multiple pages. To retrieve
        subsequent pages, make the call again using the nextPageToken
        returned by the initial call.

        :type domain: string
        :param domain: The name of the domain containing the
            workflow execution.

        :type run_id: string
        :param run_id: A system generated unique identifier for the
            workflow execution.

        :type workflow_id: string
        :param workflow_id: The user defined identifier associated
            with the workflow execution.

        :type maximum_page_size: integer
        :param maximum_page_size: Specifies the maximum number of
            history events returned in one page. The next page in the
            result is identified by the NextPageToken returned. By default
            100 history events are returned in a page but the caller can
            override this value to a page size smaller than the
            default. You cannot specify a page size larger than 100.

        :type next_page_token: string
        :param next_page_token: If a NextPageToken is returned, the
            result has more than one pages. To get the next page, repeat
            the call and specify the nextPageToken with all other
            arguments unchanged.

        :type reverse_order: boolean
        :param reverse_order: When set to true, returns the events in
            reverse order. By default the results are returned in
            ascending order of the eventTimeStamp of the events.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain}
        data['execution'] = {'runId': run_id, 'workflowId': workflow_id}
        if maximum_page_size:
            data['maximumPageSize'] = maximum_page_size
        if next_page_token:
            data['nextPageToken'] = next_page_token
        if reverse_order:
            data['reverseOrder'] = 'true'
        json_input = json.dumps(data)
        return self.make_request('GetWorkflowExecutionHistory', json_input)

    def count_open_workflow_executions(self, domain, latest_date, oldest_date,
                                       tag=None,
                                       workflow_id=None,
                                       workflow_name=None,
                                       workflow_version=None):
        """
        Returns the number of open workflow executions within the
        given domain that meet the specified filtering criteria.

        .. note:
            workflow_id, workflow_name/workflow_version and tag are mutually
            exclusive. You can specify at most one of these in a request.

        :type domain: string
        :param domain: The name of the domain containing the
            workflow executions to count.

        :type latest_date: timestamp
        :param latest_date: Specifies the latest start or close date
            and time to return.

        :type oldest_date: timestamp
        :param oldest_date: Specifies the oldest start or close date
            and time to return.

        :type workflow_name: string
        :param workflow_name: Name of the workflow type to filter on.

        :type workflow_version: string
        :param workflow_version: Version of the workflow type to filter on.

        :type tag: string
        :param tag: If specified, only executions that have a tag
            that matches the filter are counted.

        :type workflow_id: string
        :param workflow_id: If specified, only workflow executions
            matching the workflow_id are counted.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain}
        data['startTimeFilter'] = {'oldestDate': oldest_date,
                                   'latestDate': latest_date}
        if workflow_name and workflow_version:
            data['typeFilter'] = {'name': workflow_name,
                                  'version': workflow_version}
        if workflow_id:
            data['executionFilter'] = {'workflowId': workflow_id}
        if tag:
            data['tagFilter'] = {'tag': tag}
        json_input = json.dumps(data)
        return self.make_request('CountOpenWorkflowExecutions', json_input)

    def list_open_workflow_executions(self, domain,
                                      latest_date=None,
                                      oldest_date=None,
                                      tag=None,
                                      workflow_id=None,
                                      workflow_name=None,
                                      workflow_version=None,
                                      maximum_page_size=None,
                                      next_page_token=None,
                                      reverse_order=None):
        """
        Returns the list of open workflow executions within the
        given domain that meet the specified filtering criteria.

        .. note:
            workflow_id, workflow_name/workflow_version
            and tag are mutually exclusive. You can specify at most
            one of these in a request.

        :type domain: string
        :param domain: The name of the domain containing the
            workflow executions to count.

        :type latest_date: timestamp
        :param latest_date: Specifies the latest start or close date
            and time to return.

        :type oldest_date: timestamp
        :param oldest_date: Specifies the oldest start or close date
            and time to return.

        :type tag: string
        :param tag: If specified, only executions that have a tag
            that matches the filter are counted.

        :type workflow_id: string
        :param workflow_id: If specified, only workflow executions
            matching the workflow_id are counted.

        :type workflow_name: string
        :param workflow_name: Name of the workflow type to filter on.

        :type workflow_version: string
        :param workflow_version: Version of the workflow type to filter on.

        :type maximum_page_size: integer
        :param maximum_page_size: The maximum number of results
            returned in each page. The default is 100, but the caller can
            override this value to a page size smaller than the
            default. You cannot specify a page size greater than 100.

        :type next_page_token: string
        :param next_page_token: If on a previous call to this method a
            NextPageToken was returned, the results are being
            paginated. To get the next page of results, repeat the call
            with the returned token and all other arguments unchanged.

        :type reverse_order: boolean
        :param reverse_order: When set to true, returns the results in
            reverse order. By default the results are returned in
            descending order of the start or the close time of the
            executions.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError

        """
        data = {'domain': domain}
        data['startTimeFilter'] = {'oldestDate': oldest_date,
                                   'latestDate': latest_date}
        if tag:
            data['tagFilter'] = {'tag': tag}
        if workflow_name and workflow_version:
            data['typeFilter'] = {'name': workflow_name,
                                  'version': workflow_version}
        if workflow_id:
            data['executionFilter'] = {'workflowId': workflow_id}

        if maximum_page_size:
            data['maximumPageSize'] = maximum_page_size
        if next_page_token:
            data['nextPageToken'] = next_page_token
        if reverse_order:
            data['reverseOrder'] = 'true'
        json_input = json.dumps(data)
        return self.make_request('ListOpenWorkflowExecutions', json_input)

    def count_closed_workflow_executions(self, domain,
                                         start_latest_date=None,
                                         start_oldest_date=None,
                                         close_latest_date=None,
                                         close_oldest_date=None,
                                         close_status=None,
                                         tag=None,
                                         workflow_id=None,
                                         workflow_name=None,
                                         workflow_version=None):
        """
        Returns the number of closed workflow executions within the
        given domain that meet the specified filtering criteria.

        .. note:
            close_status, workflow_id, workflow_name/workflow_version
            and tag are mutually exclusive. You can specify at most
            one of these in a request.

        .. note:
            start_latest_date/start_oldest_date and
            close_latest_date/close_oldest_date are mutually
            exclusive. You can specify at most one of these in a request.

        :type domain: string
        :param domain: The name of the domain containing the
            workflow executions to count.

        :type start_latest_date: timestamp
        :param start_latest_date: If specified, only workflow executions
            that meet the start time criteria of the filter are counted.

        :type start_oldest_date: timestamp
        :param start_oldest_date: If specified, only workflow executions
            that meet the start time criteria of the filter are counted.

        :type close_latest_date: timestamp
        :param close_latest_date: If specified, only workflow executions
            that meet the close time criteria of the filter are counted.

        :type close_oldest_date: timestamp
        :param close_oldest_date: If specified, only workflow executions
            that meet the close time criteria of the filter are counted.

        :type close_status: string
        :param close_status: The close status that must match the close status
            of an execution for it to meet the criteria of this filter.
            Valid values are:

            * COMPLETED
            * FAILED
            * CANCELED
            * TERMINATED
            * CONTINUED_AS_NEW
            * TIMED_OUT

        :type tag: string
        :param tag: If specified, only executions that have a tag
            that matches the filter are counted.

        :type workflow_id: string
        :param workflow_id: If specified, only workflow executions
            matching the workflow_id are counted.

        :type workflow_name: string
        :param workflow_name: Name of the workflow type to filter on.

        :type workflow_version: string
        :param workflow_version: Version of the workflow type to filter on.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain}
        if start_latest_date and start_oldest_date:
            data['startTimeFilter'] = {'oldestDate': start_oldest_date,
                                       'latestDate': start_latest_date}
        if close_latest_date and close_oldest_date:
            data['closeTimeFilter'] = {'oldestDate': close_oldest_date,
                                       'latestDate': close_latest_date}
        if close_status:
            data['closeStatusFilter'] = {'status': close_status}
        if tag:
            data['tagFilter'] = {'tag': tag}
        if workflow_name and workflow_version:
            data['typeFilter'] = {'name': workflow_name,
                                  'version': workflow_version}
        if workflow_id:
            data['executionFilter'] = {'workflowId': workflow_id}

        json_input = json.dumps(data)
        return self.make_request('CountClosedWorkflowExecutions', json_input)

    def list_closed_workflow_executions(self, domain,
                                        start_latest_date=None,
                                        start_oldest_date=None,
                                        close_latest_date=None,
                                        close_oldest_date=None,
                                        close_status=None,
                                        tag=None,
                                        workflow_id=None,
                                        workflow_name=None,
                                        workflow_version=None,
                                        maximum_page_size=None,
                                        next_page_token=None,
                                        reverse_order=None):
        """
        Returns the number of closed workflow executions within the
        given domain that meet the specified filtering criteria.

        .. note:
            close_status, workflow_id, workflow_name/workflow_version
            and tag are mutually exclusive. You can specify at most
            one of these in a request.

        .. note:
            start_latest_date/start_oldest_date and
            close_latest_date/close_oldest_date are mutually
            exclusive. You can specify at most one of these in a request.

        :type domain: string
        :param domain: The name of the domain containing the
            workflow executions to count.

        :type start_latest_date: timestamp
        :param start_latest_date: If specified, only workflow executions
            that meet the start time criteria of the filter are counted.

        :type start_oldest_date: timestamp
        :param start_oldest_date: If specified, only workflow executions
            that meet the start time criteria of the filter are counted.

        :type close_latest_date: timestamp
        :param close_latest_date: If specified, only workflow executions
            that meet the close time criteria of the filter are counted.

        :type close_oldest_date: timestamp
        :param close_oldest_date: If specified, only workflow executions
            that meet the close time criteria of the filter are counted.

        :type close_status: string
        :param close_status: The close status that must match the close status
            of an execution for it to meet the criteria of this filter.
            Valid values are:

            * COMPLETED
            * FAILED
            * CANCELED
            * TERMINATED
            * CONTINUED_AS_NEW
            * TIMED_OUT

        :type tag: string
        :param tag: If specified, only executions that have a tag
            that matches the filter are counted.

        :type workflow_id: string
        :param workflow_id: If specified, only workflow executions
            matching the workflow_id are counted.

        :type workflow_name: string
        :param workflow_name: Name of the workflow type to filter on.

        :type workflow_version: string
        :param workflow_version: Version of the workflow type to filter on.

        :type maximum_page_size: integer
        :param maximum_page_size: The maximum number of results
            returned in each page. The default is 100, but the caller can
            override this value to a page size smaller than the
            default. You cannot specify a page size greater than 100.

        :type next_page_token: string
        :param next_page_token: If on a previous call to this method a
            NextPageToken was returned, the results are being
            paginated. To get the next page of results, repeat the call
            with the returned token and all other arguments unchanged.

        :type reverse_order: boolean
        :param reverse_order: When set to true, returns the results in
            reverse order. By default the results are returned in
            descending order of the start or the close time of the
            executions.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain}
        if start_latest_date and start_oldest_date:
            data['startTimeFilter'] = {'oldestDate': start_oldest_date,
                                       'latestDate': start_latest_date}
        if close_latest_date and close_oldest_date:
            data['closeTimeFilter'] = {'oldestDate': close_oldest_date,
                                       'latestDate': close_latest_date}

        if workflow_id:
            data['executionFilter'] = {'workflowId': workflow_id}

        if close_status:
            data['closeStatusFilter'] = {'status': close_status}
        if tag:
            data['tagFilter'] = {'tag': tag}
        if workflow_name and workflow_version:
            data['typeFilter'] = {'name': workflow_name,
                                  'version': workflow_version}
        if maximum_page_size:
            data['maximumPageSize'] = maximum_page_size
        if next_page_token:
            data['nextPageToken'] = next_page_token
        if reverse_order:
            data['reverseOrder'] = 'true'
        json_input = json.dumps(data)
        return self.make_request('ListClosedWorkflowExecutions', json_input)

## Domain Visibility

    def list_domains(self, registration_status,
                     maximum_page_size=None,
                     next_page_token=None, reverse_order=None):
        """
        Returns the list of domains registered in the account. The
        results may be split into multiple pages. To retrieve
        subsequent pages, make the call again using the nextPageToken
        returned by the initial call.

        :type registration_status: string
        :param registration_status: Specifies the registration status
            of the domains to list.  Valid Values:

            * REGISTERED
            * DEPRECATED

        :type maximum_page_size: integer
        :param maximum_page_size: The maximum number of results
            returned in each page. The default is 100, but the caller can
            override this value to a page size smaller than the
            default. You cannot specify a page size greater than 100.

        :type next_page_token: string
        :param next_page_token: If on a previous call to this method a
            NextPageToken was returned, the result has more than one
            page. To get the next page of results, repeat the call with
            the returned token and all other arguments unchanged.

        :type reverse_order: boolean
        :param reverse_order: When set to true, returns the results in
            reverse order. By default the results are returned in
            ascending alphabetical order of the name of the domains.

        :raises: SWFOperationNotPermittedError
        """
        data = {'registrationStatus': registration_status}
        if maximum_page_size:
            data['maximumPageSize'] = maximum_page_size
        if next_page_token:
            data['nextPageToken'] = next_page_token
        if reverse_order:
            data['reverseOrder'] = 'true'
        json_input = json.dumps(data)
        return self.make_request('ListDomains', json_input)

    def describe_domain(self, name):
        """
        Returns information about the specified domain including
        description and status.

        :type name: string
        :param name: The name of the domain to describe.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'name': name}
        json_input = json.dumps(data)
        return self.make_request('DescribeDomain', json_input)

## Task List Visibility

    def count_pending_decision_tasks(self, domain, task_list):
        """
        Returns the estimated number of decision tasks in the
        specified task list. The count returned is an approximation
        and is not guaranteed to be exact. If you specify a task list
        that no decision task was ever scheduled in then 0 will be
        returned.

        :type domain: string
        :param domain: The name of the domain that contains the task list.

        :type task_list: string
        :param task_list: The name of the task list.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain, 'taskList': {'name': task_list}}
        json_input = json.dumps(data)
        return self.make_request('CountPendingDecisionTasks', json_input)

    def count_pending_activity_tasks(self, domain, task_list):
        """
        Returns the estimated number of activity tasks in the
        specified task list. The count returned is an approximation
        and is not guaranteed to be exact. If you specify a task list
        that no activity task was ever scheduled in then 0 will be
        returned.

        :type domain: string
        :param domain: The name of the domain that contains the task list.

        :type task_list: string
        :param task_list: The name of the task list.

        :raises: UnknownResourceFault, SWFOperationNotPermittedError
        """
        data = {'domain': domain, 'taskList': {'name': task_list}}
        json_input = json.dumps(data)
        return self.make_request('CountPendingActivityTasks', json_input)
