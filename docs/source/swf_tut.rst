.. swf_tut:
:Authors: Slawek "oozie" Ligus <root@ooz.ie>

===============================
Amazon Simple Workflow Tutorial
===============================

This tutorial focuses on boto's interface to AWS SimpleWorkflow service. It is based on a series of blog articles and questions submitted to StackOverflow under amazon-swf tag.

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


HelloWorld
----------

In this example, we'll create and run a minimal workflow. It's a boto reimplementation of HelloWorld workflow initially created in Java:

https://github.com/aws/aws-sdk-java/tree/master/src/samples/AwsFlowFramework/src/com/amazonaws/services/simpleworkflow/flow/examples/helloworld


Here is what I mean::

    >>> import boto.swf.layer2 as swf




.. _Amazon SWF API Reference: http://docs.aws.amazon.com/amazonswf/latest/apireference/Welcome.html
.. _StackOverflow questions: http://stackoverflow.com/questions/tagged/amazon-swf
.. _Miscellaneous Blog Articles: http://log.ooz.ie/search/label/SimpleWorkflow
