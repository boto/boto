# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
#
from tests.unit import AWSMockServiceTestCase

from boto.s3.connection import S3Connection
from boto.s3.bucket import Bucket
from boto.s3.lifecycle import Rule, Lifecycle, Transition


class TestS3LifeCycle(AWSMockServiceTestCase):
    connection_class = S3Connection

    def default_body(self):
        return """
        <LifecycleConfiguration>
          <Rule>
            <ID>rule-1</ID>
            <Prefix>prefix/foo</Prefix>
            <Status>Enabled</Status>
            <Transition>
              <Days>30</Days>
              <StorageClass>GLACIER</StorageClass>
            </Transition>
            <Expiration>
              <Days>365</Days>
            </Expiration>
          </Rule>
          <Rule>
            <ID>rule-2</ID>
            <Prefix>prefix/bar</Prefix>
            <Status>Disabled</Status>
            <Transition>
              <Date>2012-12-31T00:00:000Z</Date>
              <StorageClass>GLACIER</StorageClass>
            </Transition>
          </Rule>
        </LifecycleConfiguration>
        """

    def test_parse_lifecycle_response(self):
        self.set_http_response(status_code=200)
        bucket = Bucket(self.service_connection, 'mybucket')
        response = bucket.get_lifecycle_config()
        self.assertEqual(len(response), 2)
        rule = response[0]
        self.assertEqual(rule.id, 'rule-1')
        self.assertEqual(rule.prefix, 'prefix/foo')
        self.assertEqual(rule.status, 'Enabled')
        self.assertEqual(rule.expiration.days, 365)
        self.assertIsNone(rule.expiration.date)
        transition = rule.transition
        self.assertEqual(transition.days, 30)
        self.assertEqual(transition.storage_class, 'GLACIER')
        self.assertEqual(response[1].transition.date, '2012-12-31T00:00:000Z')

    def test_expiration_with_no_transition(self):
        lifecycle = Lifecycle()
        lifecycle.add_rule('myid', 'prefix', 'Enabled', 30)
        xml = lifecycle.to_xml()
        self.assertIn('<Expiration><Days>30</Days></Expiration>', xml)

    def test_expiration_is_optional(self):
        t = Transition(days=30, storage_class='GLACIER')
        r = Rule('myid', 'prefix', 'Enabled', expiration=None,
                 transition=t)
        xml = r.to_xml()
        self.assertIn(
            '<Transition><StorageClass>GLACIER</StorageClass><Days>30</Days>',
            xml)

    def test_expiration_with_expiration_and_transition(self):
        t = Transition(date='2012-11-30T00:00:000Z', storage_class='GLACIER')
        r = Rule('myid', 'prefix', 'Enabled', expiration=30, transition=t)
        xml = r.to_xml()
        self.assertIn(
            '<Transition><StorageClass>GLACIER</StorageClass>'
            '<Date>2012-11-30T00:00:000Z</Date>', xml)
        self.assertIn('<Expiration><Days>30</Days></Expiration>', xml)
