#!/usr/bin/env python

import json
import mock
import boto
from mock import Mock
try:
    import unittest2 as unittest
except ImportError:
    import unittest
from boto.swf.layer1 import Layer1

class TestSWFConnectionProviderOverride(unittest.TestCase):
    def test_provider_override(self):
        alt_provider = Mock(spec=boto.provider.Provider)
        alt_provider.host = None
        alt_provider.host_header = None
        alt_provider.port = None
        alt_provider.secret_key = 'alt_secret_key'
        layer1 = Layer1(aws_access_key_id='aws_access_key', aws_secret_access_key='aws_secret_key', provider=alt_provider)
        self.assertEqual(alt_provider, layer1.provider)

