import boto.swf.layer2
from boto.swf.layer2 import Decider, ActivityWorker
from tests.unit import unittest
from mock import Mock


class TestActors(unittest.TestCase):

    def setUp(self):
        boto.swf.layer2.Layer1 = Mock()
        self.worker = ActivityWorker(name='test-worker', domain='test', task_list='test_list')
        self.decider = Decider(name='test-worker', domain='test', task_list='test_list')
        self.worker._swf = Mock()
        self.decider._swf = Mock()
    
    def test_decider_pass_tasktoken(self):
        self.decider._swf.poll_for_decision_task.return_value = {
            'events': [{'eventId': 1,
             'eventTimestamp': 1379019427.953,
             'eventType': 'WorkflowExecutionStarted',
             'workflowExecutionStartedEventAttributes': {
                'childPolicy': 'TERMINATE',
                'executionStartToCloseTimeout': '3600',
                'parentInitiatedEventId': 0,
                'taskList': {'name': 'test_list'},
                'taskStartToCloseTimeout': '123',
                'workflowType': {'name': 'test_workflow_name',
                'version': 'v1'}}},
            {'decisionTaskScheduledEventAttributes': 
                {'startToCloseTimeout': '123',
                'taskList': {'name': 'test_list'}},
             'eventId': 2,
             'eventTimestamp': 1379019427.953,
             'eventType': 'DecisionTaskScheduled'},
            {'decisionTaskStartedEventAttributes': {'scheduledEventId': 2},
             'eventId': 3, 'eventTimestamp': 1379019495.585,
             'eventType': 'DecisionTaskStarted'}],
             'previousStartedEventId': 0, 'startedEventId': 3,
             'taskToken': 'my_specific_task_token',
             'workflowExecution': {'runId': 'fwr243dsa324132jmflkfu0943tr09=',
                       'workflowId': 'test_workflow_name-v1-1379019427'},
             'workflowType': {'name': 'test_workflow_name', 'version': 'v1'}}

        self.decider.poll()
        self.decider.complete()

        self.decider._swf.respond_decision_task_completed.assert_called_with('my_specific_task_token', None)
        self.assertEqual('my_specific_task_token', self.decider.last_tasktoken)

if __name__ == '__main__':
    unittest.main()
