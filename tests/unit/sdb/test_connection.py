#!/usr/bin/env python

from boto.sdb.connection import SDBConnection

from tests.unit import unittest
from tests.unit import AWSQueryConnectionParamOverrideTestBase

class TestSDBConnectionParamOverride(AWSQueryConnectionParamOverrideTestBase):
    def get_conn_class(self):
        return SDBConnection

if __name__ == '__main__':
    unittest.main()
