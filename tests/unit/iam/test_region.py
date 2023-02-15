from __future__ import unicode_literals

import unittest

import mock

from boto.iam import IAMRegionInfo


class IAMRegionInfoTest(unittest.TestCase):
    def setUp(self):
        self.connection_cls = mock.Mock()
        self.region_info = IAMRegionInfo(
            name='test-region',
            endpoint='default.region.endpoint',
            connection_cls=self.connection_cls
        )

    def test_does_not_attempt_to_overwrite_host_kwarg(self):
        self.region_info.connect(host='custom.host')
        self.connection_cls.assert_called_once_with(host='custom.host')
