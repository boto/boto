import boto
import boto.swf.layer2
from boto.swf.layer2 import SWFBase
from tests.unit import unittest
from mock import Mock


MOCK_DOMAIN = 'Mock'
MOCK_ACCESS_KEY = 'inheritable access key'
MOCK_SECRET_KEY = 'inheritable secret key'
MOCK_REGION = 'Mock Region'


class TestSWFLayer2ProviderOverride(unittest.TestCase):
    def test_provider_override(self):
        alt_provider = Mock(spec=boto.provider.Provider)
        alt_provider.host = None
        alt_provider.host_header = None
        alt_provider.port = None
        alt_provider.secret_key = 'alt_secret_key'
        regions=boto.swf.regions()
        layer2 = SWFBase(
            domain=MOCK_DOMAIN, aws_access_key_id=MOCK_ACCESS_KEY,
            aws_secret_access_key=MOCK_SECRET_KEY, region=regions[0],
            provider = alt_provider
        )
        self.assertEqual(alt_provider, layer2._swf.provider)

