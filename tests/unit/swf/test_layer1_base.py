from boto.swf.layer1 import Layer1
from tests.unit import unittest

MOCK_ACCESS_KEY = 'inheritable access key'
MOCK_SECRET_KEY = 'inheritable secret key'
MOCK_SECURITY_TOKEN = 'inheritable security_token'


class TestBase(unittest.TestCase):
    """
    Test for Layer1.
    """

    def setUp(self):
        self.swf_base = Layer1(
            aws_access_key_id=MOCK_ACCESS_KEY,
            aws_secret_access_key=MOCK_SECRET_KEY,
            security_token=MOCK_SECURITY_TOKEN,
        )

    def test_instantiation(self):
        self.assertEquals(self.swf_base.aws_access_key_id, MOCK_ACCESS_KEY)
        self.assertEquals(self.swf_base.aws_secret_access_key, MOCK_SECRET_KEY)
        self.assertEquals(self.swf_base.provider.security_token,
                          MOCK_SECURITY_TOKEN)
