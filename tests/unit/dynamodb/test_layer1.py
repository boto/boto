#!/usr/bin/env python

import json

from tests.unit import AWSMockServiceTestCase, MockServiceProviderTestCase

from boto.dynamodb.layer1 import Layer1

class TestDDBConnectionProviderOverride(MockServiceProviderTestCase):
    connection_class = Layer1

    def test_provider_override(self):
        self.assert_alt_provider_used()

