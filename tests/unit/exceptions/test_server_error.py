try:
    import unittest2 as unittest
except ImportError:
    import unittest

from boto.exception import BotoServerError

class BotoServerErrorTest(unittest.TestCase):
    def setUp(self):
        self.body = """<?xml version="1.0" encoding="UTF-8"?><Error><Code>NoSuchKey</Code><Message>The resource you requested does not exist</Message><Resource>/mybucket/myfoto.jpg</Resource> <RequestId>4442587FB7D0A2F9</RequestId></Error>"""

    def test_exception_message(self):
        e = BotoServerError(404, "No Such Key", body=self.body)
        self.assertEqual("NoSuchKey", e.code)
        self.assertEqual("The resource you requested does not exist", e.message)
