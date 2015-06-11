#!/usr/bin/env python
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
import time

import boto
from boto.compat import six
from tests.compat import unittest

class TestVPCEndpoint(unittest.TestCase):
    def setUp(self):
        # Registry of instances to be removed
        self.instances = []
        # Registry for cleaning up the vpc after all instances are terminated
        # in the format [ ( func, (arg1, ... argn) ) ]
        self.post_terminate_cleanups = []

        self.api = boto.connect_vpc()
        self.vpc = self.api.create_vpc('10.0.0.0/16')

        # Need time for the VPC to be in place. :/
        self.subnet = self.api.create_subnet(self.vpc.id, '10.0.0.0/24')
        # Register the subnet to be deleted after instance termination
        self.post_terminate_cleanups.append((self.api.delete_subnet, (self.subnet.id,)))

    def post_terminate_cleanup(self):
        """Helper to run clean up tasks after instances are removed."""
        for fn, args in self.post_terminate_cleanups:
            fn(*args)
            # Give things time to catch up each time
            time.sleep(10)

        # Now finally delete the vpc
        if self.vpc:
            self.api.delete_vpc(self.vpc.id)

    def terminate_instances(self):
        """Helper to remove all instances and kick off additional cleanup
        once they are terminated.
        """
        for instance in self.instances:
            self.terminate_instance(instance)
        self.post_terminate_cleanup()

    def terminate_instance(self, instance):
        instance.terminate()
        for i in six.moves.range(300):
            instance.update()
            if instance.state == 'terminated':
                # Give it a litle more time to settle.
                time.sleep(30)
                return
            else:
                time.sleep(10)

    def tearDown(self):
        self.post_terminate_cleanup()


    def test_creation(self):
        endpoint = self.api.create_endpoint(service_name='com.amazonaws.us-east-1.s3', vpc_id=self.vpc.id) 

