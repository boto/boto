import unittest
import os


CURRENT_DIR = os.path.dirname(
    os.path.realpath(__file__))


class BotoConfigOverrideTestcase(unittest.TestCase):

    def setUp(self):
        os.environ['BOTO_PATH'] = os.path.join(CURRENT_DIR, 'ut_boto.cfg')

    def test_dynamodb2(self):
        import boto.dynamodb2
        conn = boto.dynamodb2.connect_to_region('ap-southeast-2')
        self.assertEqual(conn.is_secure, False)
        self.assertEqual(conn.host, 'localhost')
        self.assertEqual(conn.port, 8000)
