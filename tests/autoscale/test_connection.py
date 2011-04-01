# Copyright (c) 2011 Reza Lotun http://reza.lotun.name
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

"""
Some unit tests for the AutoscaleConnection
"""

import unittest
import time
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale.activity import Activity
from boto.ec2.autoscale.group import AutoScalingGroup, ProcessType
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.autoscale.policy import AdjustmentType, MetricCollectionTypes, ScalingPolicy
from boto.ec2.autoscale.scheduled import ScheduledUpdateGroupAction
from boto.ec2.autoscale.instance import Instance

class AutoscaleConnectionTest(unittest.TestCase):

    def test_basic(self):
        # NB: as it says on the tin these are really basic tests that only
        # (lightly) exercise read-only behaviour - and that's only if you
        # have any autoscale groups to introspect. It's useful, however, to
        # catch simple errors

        print '--- running %s tests ---' % self.__class__.__name__
        c = AutoScaleConnection()

        self.assertTrue(repr(c).startswith('AutoScaleConnection'))

        groups = c.get_all_groups()
        for group in groups:
            self.assertTrue(type(group), AutoScalingGroup)

            # get activities
            activities = group.get_activities()

            for activity in activities:
                self.assertEqual(type(activity), Activity)

        # get launch configs
        configs = c.get_all_launch_configurations()
        for config in configs:
            self.assertTrue(type(config), LaunchConfiguration)

        # get policies
        policies = c.get_all_policies()
        for policy in policies:
            self.assertTrue(type(policy), ScalingPolicy)

        # get scheduled actions
        actions = c.get_all_scheduled_actions()
        for action in actions:
            self.assertTrue(type(action), ScheduledUpdateGroupAction)

        # get instances
        instances = c.get_all_autoscaling_instances()
        for instance in instances:
            self.assertTrue(type(instance), Instance)

        # get all scaling process types
        ptypes = c.get_all_scaling_process_types()
        for ptype in ptypes:
            self.assertTrue(type(ptype), ProcessType)

        # get adjustment types
        adjustments = c.get_all_adjustment_types()
        for adjustment in adjustments:
            self.assertTrue(type(adjustment), AdjustmentType)

        # get metrics collection types
        types = c.get_all_metric_collection_types()
        self.assertTrue(type(types), MetricCollectionTypes)

        print '--- tests completed ---'

