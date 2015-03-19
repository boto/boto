#!/usr/bin/env python

from boto.ec2.elb import ELBConnection

from tests.unit import unittest
from tests.unit import AWSQueryConnectionParamOverrideTestBase

class TestELBConnectionParamOverride(AWSQueryConnectionParamOverrideTestBase):
    def get_conn_class(self):
        return ELBConnection

if __name__ == '__main__':
    unittest.main()
