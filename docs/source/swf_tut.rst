.. swf_tut:
 :Authors: Slawek "oozie" Ligus <root@ooz.ie>

===============================
Amazon Simple Workflow Tutorial
===============================

This tutorial focuses on boto's interface to AWS SimpleWorkflow service.
.. _SimpleWorkflow: http://aws.amazon.com/swf/

What is a workflow?
-------------------

A workflow is a sequence of multiple activities aimed at accomplishing a well-defined objective. For instance, booking an airline ticket as a workflow may encompass multiple activities, such as selection of itinerary, submission of personal details, payment validation and booking confirmation. 

Except for the start and completion of a workflow, each step has a well-defined predecessor and successor. With that
  - on successful completion of an activity the workflow can progress with its execution,
  - when one of its activities fails it can be retried,
  - and when it keeps failing repeatedly the workflow may regress to the previous step to gather alternative inputs or it may simply fail at that stage.

Why use workflows?
------------------

Modelling an application on a workflow provides a useful abstraction layer for writing highly-reliable programs for distributed systems, as individual responsibilities can be delegated to a set of redundant, independent and non-critical processing units.

How does Amazon SWF help you accomplish this?
---------------------------------------------

Amazon SimpleWorkflow service defines an interface for workflow orchestration and provides state persistence for workflow executions.

Amazon SWF applications involve communcation between the following entities:
  - The Amazon Simple Workflow Service - providing centralized orcherstration and workflow state persistence,
  - Workflow Executors - some entity starting workflow executions, typically through an action taken by a user or from a cronjob.
  - Deciders - a program codifying the business logic, i.e. a set of instructions and decisions. Deciders take decisions based on initial set of conditions and outcomes from activities.
  - Activity Workers - their objective is very straightforward: to take inputs, execute the tasks and return a result to the Service.

The Workflow Executor contacts SWF Service and requests instantiation of a workflow. A new workflow is created and its state is stored in the service. 
The next time a decider contacts SWF service to ask for a decision task, it will be informed about a new workflow execution is taking place and it will be asked to advise SWF service on what the next steps should be. The decider then instructs the service to dispatch specific tasks to activity workers. At the next activity worker poll, the task is dispatched, then executed and the results reported back to the SWF, which then passes them onto the deciders. This exchange keeps happening repeatedly until the decider is satisfied and instructs the service to complete the execution.

Prerequisites
-------------

You need a valid access and secret key. The examples below assume that you have exported them to your environment, as follows:

.. code-block:: bash

    bash$ export AWS_ACCESS_KEY_ID=<your access key>
    bash$ export AWS_SECRET_ACCESS_KEY=<your secret key>

Before workflows and activities can be used, they have to be registered with SWF service:

.. code-block:: python

    # register.py
    import boto.swf.layer2 as swf
    DOMAIN = 'boto_tutorial'
    VERSION = '1.0'

    swf.Domain(name=DOMAIN).register()
    swf.ActivityType(domain=DOMAIN, name='HelloWorld', version=VERSION, task_list='default').register()
    swf.WorkflowType(domain=DOMAIN, name='HelloWorkflow', version=VERSION, task_list='default').register()

Execution of the above should produce no errors.

.. code-block:: bash

   bash$ python -i register.py
   >>> 

HelloWorld
----------

This example is an implementation of a minimal Hello World workflow. Its execution should unfold as follows:

#. A workflow execution is started.
#. The SWF service schedules the initial decision task.
#. A decider polls for decision tasks and receives one.
#. The decider requests scheduling of an activity task.
#. The SWF service schedules the greeting activity task.
#. An activity worker polls for activity task and receives one.
#. The worker completes the greeting activity.
#. The SWF service schedules a decision task to inform about work outcome.
#. The decider polls and receives a new decision task.
#. The decider schedules workflow completion.
#. The workflow execution finishes.

Workflow logic is encoded in the decider:

.. code-block:: python

    # hello_decider.py
    import boto.swf.layer2 as swf
    
    DOMAIN = 'boto_tutorial'
    ACTIVITY = 'HelloWorld'
    VERSION = '1.0'
    TASKLIST = 'default'
    
    class HelloDecider(swf.Decider):
    
        domain = DOMAIN
        task_list = TASKLIST
        version = VERSION
    
        def run(self):
            history = self.poll()
            if 'events' in history:
                # Find workflow events not related to decision scheduling.
                workflow_events = [e for e in history['events']
                    if not e['eventType'].startswith('Decision')]
                last_event = workflow_events[-1]
    
                decisions = swf.Layer1Decisions()
                if last_event['eventType'] == 'WorkflowExecutionStarted':
                    decisions.schedule_activity_task('saying_hi', ACTIVITY, VERSION, task_list=TASKLIST)
                elif last_event['eventType'] == 'ActivityTaskCompleted':
                    decisions.complete_workflow_execution()
                self.complete(decisions=decisions)
                return True   
    
The activity worker is responsible for printing the greeting message when the activity task is dispatched to it by the service:

.. code-block:: python

    import boto.swf.layer2 as swf
    
    DOMAIN = 'boto_tutorial'
    VERSION = '1.0'
    TASKLIST = 'default'
    
    class HelloWorker(swf.ActivityWorker):
    
        domain = DOMAIN
        version = VERSION
        task_list = TASKLIST
    
        def run(self):
            activity_task = self.poll()
            if 'activityId' in activity_task:
                print 'Hello, World!'
                self.complete()
                return True

With actors implemented we can spin up a workflow execution:

.. code-block:: bash

    $ python
    >>> import boto.swf.layer2 as swf
    >>> execution = swf.WorkflowType(name='HelloWorkflow', domain='boto_tutorial', version='1.0', task_list='default').start()
    >>> 
    
From separate terminals run an instance of a worker and a decider to carry out a workflow execution (the worker and decider may run from two independent machines).

.. code-block:: bash

   $ python -i hello_decider.py
   >>> while HelloDecider().run(): pass
   ... 

.. code-block:: bash

   $ python -i hello_worker.py
   >>> while HelloWorker().run(): pass
   ... 
   Hello, World!

Great. Now, to see what just happened, go back to the original terminal from which the execution was started, and read its history.

.. code-block:: bash

    >>> execution.history()
    [{'eventId': 1,
      'eventTimestamp': 1381095173.2539999,
      'eventType': 'WorkflowExecutionStarted',
      'workflowExecutionStartedEventAttributes': {'childPolicy': 'TERMINATE',
                                                  'executionStartToCloseTimeout': '3600',
                                                  'parentInitiatedEventId': 0,
                                                  'taskList': {'name': 'default'},
                                                  'taskStartToCloseTimeout': '300',
                                                  'workflowType': {'name': 'HelloWorkflow',
                                                                   'version': '1.0'}}},
     {'decisionTaskScheduledEventAttributes': {'startToCloseTimeout': '300',
                                               'taskList': {'name': 'default'}},
      'eventId': 2,
      'eventTimestamp': 1381095173.2539999,
      'eventType': 'DecisionTaskScheduled'},
     {'decisionTaskStartedEventAttributes': {'scheduledEventId': 2},
      'eventId': 3,
      'eventTimestamp': 1381095177.5439999,
      'eventType': 'DecisionTaskStarted'},
     {'decisionTaskCompletedEventAttributes': {'scheduledEventId': 2,
                                               'startedEventId': 3},
      'eventId': 4,
      'eventTimestamp': 1381095177.855,
      'eventType': 'DecisionTaskCompleted'},
     {'activityTaskScheduledEventAttributes': {'activityId': 'saying_hi',
                                               'activityType': {'name': 'HelloWorld',
                                                                'version': '1.0'},
                                               'decisionTaskCompletedEventId': 4,
                                               'heartbeatTimeout': '600',
                                               'scheduleToCloseTimeout': '3900',
                                               'scheduleToStartTimeout': '300',
                                               'startToCloseTimeout': '3600',
                                               'taskList': {'name': 'default'}},
      'eventId': 5,
      'eventTimestamp': 1381095177.855,
      'eventType': 'ActivityTaskScheduled'},
     {'activityTaskStartedEventAttributes': {'scheduledEventId': 5},
      'eventId': 6,
      'eventTimestamp': 1381095179.427,
      'eventType': 'ActivityTaskStarted'},
     {'activityTaskCompletedEventAttributes': {'scheduledEventId': 5,
                                               'startedEventId': 6},
      'eventId': 7,
      'eventTimestamp': 1381095179.6989999,
      'eventType': 'ActivityTaskCompleted'},
     {'decisionTaskScheduledEventAttributes': {'startToCloseTimeout': '300',
                                               'taskList': {'name': 'default'}},
      'eventId': 8,
      'eventTimestamp': 1381095179.6989999,
      'eventType': 'DecisionTaskScheduled'},
     {'decisionTaskStartedEventAttributes': {'scheduledEventId': 8},
      'eventId': 9,
      'eventTimestamp': 1381095179.7420001,
      'eventType': 'DecisionTaskStarted'},
     {'decisionTaskCompletedEventAttributes': {'scheduledEventId': 8,
                                               'startedEventId': 9},
      'eventId': 10,
      'eventTimestamp': 1381095180.026,
      'eventType': 'DecisionTaskCompleted'},
     {'eventId': 11,
      'eventTimestamp': 1381095180.026,
      'eventType': 'WorkflowExecutionCompleted',
      'workflowExecutionCompletedEventAttributes': {'decisionTaskCompletedEventId': 10}}]
    
    
.. _Amazon SWF API Reference: http://docs.aws.amazon.com/amazonswf/latest/apireference/Welcome.html
.. _StackOverflow questions: http://stackoverflow.com/questions/tagged/amazon-swf
.. _Miscellaneous Blog Articles: http://log.ooz.ie/search/label/SimpleWorkflow
