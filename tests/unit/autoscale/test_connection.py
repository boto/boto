#!/usr/bin/env python

from tests.unit import unittest
from tests.unit import AWSQueryConnectionParamOverrideTestBase

from boto.ec2.autoscale import AutoScaleConnection


class TestAutoScaleConnectionParamOverride(AWSQueryConnectionParamOverrideTestBase):
    def get_conn_class(self):
        return AutoScaleConnection


if __name__ == '__main__':
    unittest.main()
