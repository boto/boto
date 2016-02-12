# -*- coding: UTF-8 -*-
from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase, MockServiceProviderTestCase

from boto.vpc import VPCConnection, VpnConnection


class TestVPCConnectionProviderOverride(MockServiceProviderTestCase):
    connection_class = VPCConnection

    def test_provider_override(self):
        self.assert_alt_provider_used()

