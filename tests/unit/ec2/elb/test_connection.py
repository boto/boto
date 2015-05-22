
from tests.unit import MockServiceProviderTestCas
from boto.ec2.elb import ELBConnection


class TestELBConnectionProviderOverride(MockServiceProviderTestCase):
    connection_class = ELBConnection

    def test_provider_override(self):
        self.assert_alt_provider_used()


