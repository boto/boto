#!/usr/bin/env python
from tests.compat import unittest

import boto.cloudfront as cf

class CFInvalidationTest(unittest.TestCase):

    cloudfront = True

    def test_wildcard_escape(self):
        """
        Test that wildcards are retained as literals
        See: http://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html#invalidation-specifying-objects-paths
        """
        batch = cf.invalidation.InvalidationBatch()
        self.assertEqual(batch.escape("/*"), "/*")
        self.assertEqual(batch.escape("/foo*"), "/foo*")
        self.assertEqual(batch.escape("/foo/bar/*"), "/foo/bar/*")
        self.assertEqual(batch.escape("/nowildcard"), "/nowildcard")
        self.assertEqual(batch.escape("/other special characters"), "/other%20special%20characters")

    def test_argument_escape(self):
        """
        Test that query string parameters are retained as literals
        See: http://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/QueryStringParameters.html
        """
        batch = cf.invalidation.InvalidationBatch()
        self.assertEqual(batch.escape("/foo/bar/baz.jpg?filtered=false&size=*"), "/foo/bar/baz.jpg?filtered=false&size=*")

if __name__ == '__main__':
    unittest.main()
