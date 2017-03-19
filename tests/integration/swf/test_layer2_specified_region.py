"""
Tests for Layer2 of Simple Workflow with speficied region

"""
import os
import sys
import unittest
import time
import boto
import json
from boto.swf import layer2
from boto.swf.layer1 import Layer1
from boto.swf import exceptions as swf_exceptions



# A standard AWS account is permitted a maximum of 100 of SWF domains,
# registered or deprecated.  Deleting deprecated domains on demand does
# not appear possible.  Therefore, these tests reuse a default or
# user-named testing domain.  This is named by the user via the environment
# variable BOTO_SWF_UNITTEST_DOMAIN, if available.  Otherwise the default
# testing domain is literally "boto-swf-unittest-domain".  Do not use
# the testing domain for other purposes.
BOTO_SWF_UNITTEST_DOMAIN = os.environ.get("BOTO_SWF_UNITTEST_DOMAIN", "boto-swf-unittest-domain")

# A standard domain can have a maxiumum of 10,000 workflow types and
# activity types, registered or deprecated.  Therefore, eventually any
# tests which register new workflow types or activity types would begin
# to fail with LimitExceeded.  Instead of generating new workflow types
# and activity types, these tests reuse the existing types.

# The consequence of the limits and inability to delete deprecated
# domains, workflow types, and activity types is that the tests in
# this module will not test for the three register actions:
#    * register_domain
#    * register_workflow_type
#    * register_activity_type
# Instead, the setUp of the TestCase create a domain, workflow type,
# and activity type, expecting that they may already exist, and the
# tests themselves test other things.

# If you really want to re-test the register_* functions in their
# ability to create things (rather than just reporting that they
# already exist), you'll need to use a new BOTO_SWF_UNITTEST_DOMAIN.
# But, beware that once you hit 100 domains, you are cannot create any
# more, delete existing ones, or rename existing ones.

# Some API calls establish resources, but these resources are not instantly
# available to the next API call.  For testing purposes, it is necessary to
# have a short pause to avoid having tests fail for invalid reasons.
PAUSE_SECONDS = 4


class SimpleWorkflowLayer2TestBase(unittest.TestCase):
    swf = True
    # Some params used throughout the tests...
    # Domain registration params...
    _domain = BOTO_SWF_UNITTEST_DOMAIN
    _region = 'us-west-2'
    _workflow_execution_retention_period_in_days = 'NONE'
    _domain_description = 'test workflow domain'
    # Type registration params used for workflow type and activity type...
    _task_list = 'tasklist1'
    # Workflow type registration params...
    _workflow_type_name = 'wft2'
    _workflow_type_version = '1'
    _workflow_type_description = 'wft2 description'
    _default_child_policy = 'REQUEST_CANCEL'
    _default_execution_start_to_close_timeout = '600'
    _default_task_start_to_close_timeout = '60'
    # Activity type registration params...
    _activity_type_name = 'at1'
    _activity_type_version = '1'
    _activity_type_description = 'at1 description'
    _default_task_heartbeat_timeout = '30'
    _default_task_schedule_to_close_timeout = '90'
    _default_task_schedule_to_start_timeout = '10'
    _default_task_start_to_close_timeout = '30'


    def setUp(self):
        # Create a Layer1 connection for testing.
        # Tester needs boto config or keys in environment variables.
        region = None
        for reg in boto.swf.regions():
            if reg.name == self._region:
               region = reg
               break
        assert region.name == self._region
        self.conn = Layer1(region=region)

        # Register a domain.  Expect None (success) or
        # SWFDomainAlreadyExistsError.
        try:
            r = self.conn.register_domain(self._domain,
                    self._workflow_execution_retention_period_in_days,
                    description=self._domain_description)
            assert r is None
            time.sleep(PAUSE_SECONDS)
        except swf_exceptions.SWFDomainAlreadyExistsError:
            pass

        # Register a workflow type.  Expect None (success) or
        # SWFTypeAlreadyExistsError.
        try:
            r = self.conn.register_workflow_type(self._domain,
                    self._workflow_type_name, self._workflow_type_version,
                    task_list=self._task_list,
                    default_child_policy=self._default_child_policy,
                    default_execution_start_to_close_timeout=
                        self._default_execution_start_to_close_timeout,
                    default_task_start_to_close_timeout=
                        self._default_task_start_to_close_timeout,
                    description=self._workflow_type_description)
            assert r is None
            time.sleep(PAUSE_SECONDS)
        except swf_exceptions.SWFTypeAlreadyExistsError:
            pass

        # Register an activity type.  Expect None (success) or
        # SWFTypeAlreadyExistsError.
        try:
            r = self.conn.register_activity_type(self._domain,
                    self._activity_type_name, self._activity_type_version,
                    task_list=self._task_list,
                    default_task_heartbeat_timeout=
                        self._default_task_heartbeat_timeout,
                    default_task_schedule_to_close_timeout=
                        self._default_task_schedule_to_close_timeout,
                    default_task_schedule_to_start_timeout=
                        self._default_task_schedule_to_start_timeout,
                    default_task_start_to_close_timeout=
                        self._default_task_start_to_close_timeout,
                    description=self._activity_type_description)
            assert r is None
            time.sleep(PAUSE_SECONDS)
        except swf_exceptions.SWFTypeAlreadyExistsError:
            pass

        self.l2conn = layer2.Domain(name=self._domain, region=region)

    def tearDown(self):
        # Delete what we can...
        pass


class SimpleWorkflowLayer2Test(SimpleWorkflowLayer2TestBase):

    def test_list_workflow_types(self):
        # Find the workflow type.
        #r = self.conn.list_workflow_types(self._domain, 'REGISTERED')
        r = self.l2conn.workflows()
        found = None
        for wft in r:
            info = wft.describe()
            #sys.stderr.write(json.dumps(info))
            if ( info['typeInfo']['workflowType']['name'] == self._workflow_type_name and
	            info['typeInfo']['workflowType']['version'] == self._workflow_type_version ):
                found = info
                break
        self.assertNotEqual(found, None, 'list_workflow_types; test type not found')
        # Validate some properties.
        self.assertEqual(found['typeInfo']['description'], self._workflow_type_description,
                         'list_workflow_types; description does not match')
        self.assertEqual(found['typeInfo']['status'], 'REGISTERED',
                         'list_workflow_types; status does not match')

