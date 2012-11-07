# -*- coding: utf-8 -*-

# Copyright (c) 2011 Mitch Garnaat http://garnaat.org/
# All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
Some unit tests for the S3 Bucket
"""

import unittest
import time

from boto.exception import S3ResponseError
from boto.s3.connection import S3Connection
from boto.s3.bucketlogging import BucketLogging
from boto.s3.acl import Grant
from boto.s3.tagging import Tags, TagSet


class S3BucketTest (unittest.TestCase):
    s3 = True

    def setUp(self):
        self.conn = S3Connection()
        self.bucket_name = 'bucket-%d' % int(time.time())
        self.bucket = self.conn.create_bucket(self.bucket_name)

    def tearDown(self):
        for key in self.bucket:
            key.delete()
        self.bucket.delete()

    def test_next_marker(self):
        expected = ["a/", "b", "c"]
        for key_name in expected:
            key = self.bucket.new_key(key_name)
            key.set_contents_from_string(key_name)

        # Normal list of first 2 keys will have
        # no NextMarker set, so we use last key to iterate
        # last element will be "b" so no issue.
        rs = self.bucket.get_all_keys(max_keys=2)
        for element in rs:
            pass
        self.assertEqual(element.name, "b")
        self.assertEqual(rs.next_marker, None)

        # list using delimiter of first 2 keys will have
        # a NextMarker set (when truncated). As prefixes
        # are grouped together at the end, we get "a/" as
        # last element, but luckily we have next_marker.
        rs = self.bucket.get_all_keys(max_keys=2, delimiter="/")
        for element in rs:
            pass
        self.assertEqual(element.name, "a/")
        self.assertEqual(rs.next_marker, "b")

        # ensure bucket.list() still works by just
        # popping elements off the front of expected.
        rs = self.bucket.list()
        for element in rs:
            self.assertEqual(element.name, expected.pop(0))
        self.assertEqual(expected, [])

    def test_logging(self):
        # use self.bucket as the target bucket so that teardown
        # will delete any log files that make it into the bucket
        # automatically and all we have to do is delete the 
        # source bucket.
        sb_name = "src-" + self.bucket_name 
        sb = self.conn.create_bucket(sb_name)
        # grant log write perms to target bucket using canned-acl
        self.bucket.set_acl("log-delivery-write")
        target_bucket = self.bucket_name
        target_prefix = u"jp/ログ/"
        # Check existing status is disabled
        bls = sb.get_logging_status()
        self.assertEqual(bls.target, None)
        # Create a logging status and grant auth users READ PERM
        authuri = "http://acs.amazonaws.com/groups/global/AuthenticatedUsers"
        authr = Grant(permission="READ", type="Group", uri=authuri)
        sb.enable_logging(target_bucket, target_prefix=target_prefix, grants=[authr])
        # Check the status and confirm its set.
        bls = sb.get_logging_status()
        self.assertEqual(bls.target, target_bucket)
        self.assertEqual(bls.prefix, target_prefix)
        self.assertEqual(len(bls.grants), 1)
        self.assertEqual(bls.grants[0].type, "Group")
        self.assertEqual(bls.grants[0].uri, authuri)
        # finally delete the src bucket
        sb.delete()

    def test_tagging(self):
        tagging = """
            <Tagging>
              <TagSet>
                 <Tag>
                   <Key>tagkey</Key>
                   <Value>tagvalue</Value>
                 </Tag>
              </TagSet>
            </Tagging>
        """
        self.bucket.set_xml_tags(tagging)
        response = self.bucket.get_tags()
        self.assertEqual(response[0][0].key, 'tagkey')
        self.assertEqual(response[0][0].value, 'tagvalue')
        self.bucket.delete_tags()
        try:
            self.bucket.get_tags()
        except S3ResponseError, e:
            self.assertEqual(e.code, 'NoSuchTagSet')
        except Exception, e:
            self.fail("Wrong exception raised (expected S3ResponseError): %s"
                      % e)
        else:
            self.fail("Expected S3ResponseError, but no exception raised.")

    def test_tagging_from_objects(self):
        """Create tags from python objects rather than raw xml."""
        t = Tags()
        tag_set = TagSet()
        tag_set.add_tag('akey', 'avalue')
        tag_set.add_tag('anotherkey', 'anothervalue')
        t.add_tag_set(tag_set)
        self.bucket.set_tags(t)
        response = self.bucket.get_tags()
        self.assertEqual(response[0][0].key, 'akey')
        self.assertEqual(response[0][0].value, 'avalue')
        self.assertEqual(response[0][1].key, 'anotherkey')
        self.assertEqual(response[0][1].value, 'anothervalue')
