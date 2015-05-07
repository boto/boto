#!/usr/bin/env python

from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.ec2.elb import ELBConnection
from boto.ec2.elb.loadbalancer import LoadBalancer
from boto.ec2.elb.tag import TagSet


ADD_TAGS_RESPONSE = br"""<?xml version="1.0" encoding="UTF-8"?>
<AddTagsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <AddTagsResult/>
  <ResponseMetadata>
    <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
  </ResponseMetadata>
</AddTagsResponse>
"""


REMOVE_TAGS_RESPONSE = br"""<?xml version="1.0" encoding="UTF-8"?>
<RemoveTagsResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <RemoveTagsResult/>
  <ResponseMetadata>
    <RequestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</RequestId>
  </ResponseMetadata>
</RemoveTagsResponse>
"""


class TestAddTags(AWSMockServiceTestCase):
    connection_class = ELBConnection

    def default_body(self):
        return ADD_TAGS_RESPONSE

    def test_add_tag(self):
        self.set_http_response(status_code=200)
        lb = LoadBalancer(self.service_connection)
        lb.name = "lb-abcd1234"
        lb._tags = TagSet()
        lb._tags["already_present_key"] = "already_present_value"

        lb.add_tag("new_key", "new_value")

        self.assert_request_parameters({
            'LoadBalancerNames.member.1': 'lb-abcd1234',
            'Action': 'AddTags',
            'Tags.member.1.Key': 'new_key',
            'Tags.member.1.Value': 'new_value'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])

        self.assertEqual(lb._tags, {
            "already_present_key": "already_present_value",
            "new_key": "new_value"})

    def test_add_tags(self):
        self.set_http_response(status_code=200)
        lb = LoadBalancer(self.service_connection)
        lb.name = "lb-abcd1234"
        lb._tags = TagSet()
        lb._tags["already_present_key"] = "already_present_value"

        lb.add_tags({"key1": "value1", "key2": "value2"})

        self.assert_request_parameters({
            'LoadBalancerNames.member.1': 'lb-abcd1234',
            'Action': 'AddTags',
            'Tags.member.1.Key': 'key1',
            'Tags.member.1.Value': 'value1',
            'Tags.member.2.Key': 'key2',
            'Tags.member.2.Value': 'value2'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])

        self.assertEqual(lb._tags, {
            "already_present_key": "already_present_value",
            "key1": "value1",
            "key2": "value2"})


class TestRemoveTags(AWSMockServiceTestCase):
    connection_class = ELBConnection

    def default_body(self):
        return REMOVE_TAGS_RESPONSE

    def test_remove_tag(self):
        self.set_http_response(status_code=200)
        lb = LoadBalancer(self.service_connection)
        lb.name = "lb-abcd1234"
        lb._tags = TagSet()
        lb._tags["key1"] = "value1"
        lb._tags["key2"] = "value2"

        lb.remove_tag("key1")

        self.assert_request_parameters({
            'LoadBalancerNames.member.1': 'lb-abcd1234',
            'Action': 'RemoveTags',
            'Tags.member.1.Key': 'key1'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])

        self.assertEqual(lb._tags, {"key2": "value2"})

    def test_remove_tags(self):
        self.set_http_response(status_code=200)
        lb = LoadBalancer(self.service_connection)
        lb.name = "lb-abcd1234"
        lb._tags = TagSet()
        lb._tags["key1"] = "value1"
        lb._tags["key2"] = "value2"

        lb.remove_tags(["key1", "key2"])

        self.assert_request_parameters({
            'LoadBalancerNames.member.1': 'lb-abcd1234',
            'Action': 'RemoveTags',
            'Tags.member.1.Key': 'key1',
            'Tags.member.2.Key': 'key2'},
            ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                  'SignatureVersion', 'Timestamp',
                                  'Version'])

        self.assertEqual(lb._tags, {})


if __name__ == '__main__':
    unittest.main()
