#!/usr/bin/env python
import datetime
import xml.sax
import unittest
import boto.handler
import boto.resultset
import boto.cloudformation

SAMPLE_XML = r"""
<DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <DescribeStacksResult>
    <Stacks>
      <member>
        <Tags>
          <member>
            <Value>value0</Value>
            <Key>key0</Key>
          </member>
          <member>
            <Key>key1</Key>
            <Value>value1</Value>
          </member>
        </Tags>
        <StackId>arn:aws:cloudformation:ap-southeast-1:100:stack/Name/id</StackId>
        <StackStatus>CREATE_COMPLETE</StackStatus>
        <StackName>Name</StackName>
        <StackStatusReason/>
        <Description/>
        <NotificationARNs>
          <member>arn:aws:sns:ap-southeast-1:100:name</member>
        </NotificationARNs>
        <CreationTime>2013-01-10T05:04:56Z</CreationTime>
        <DisableRollback>false</DisableRollback>
        <Outputs>
          <member>
            <OutputValue>value0</OutputValue>
            <Description>output0</Description>
            <OutputKey>key0</OutputKey>
          </member>
          <member>
            <OutputValue>value1</OutputValue>
            <Description>output1</Description>
            <OutputKey>key1</OutputKey>
          </member>
        </Outputs>
      </member>
    </Stacks>
  </DescribeStacksResult>
  <ResponseMetadata>
    <RequestId>1</RequestId>
  </ResponseMetadata>
</DescribeStacksResponse>
"""

DESCRIBE_STACK_RESOURCE_XML = r"""
<DescribeStackResourcesResult>
  <StackResources>
    <member>
      <StackId>arn:aws:cloudformation:us-east-1:123456789:stack/MyStack/aaf549a0-a413-11df-adb3-5081b3858e83</StackId>
      <StackName>MyStack</StackName>
      <LogicalResourceId>MyDBInstance</LogicalResourceId>
      <PhysicalResourceId>MyStack_DB1</PhysicalResourceId>
      <ResourceType>AWS::DBInstance</ResourceType>
      <Timestamp>2010-07-27T22:27:28Z</Timestamp>
      <ResourceStatus>CREATE_COMPLETE</ResourceStatus>
    </member>
    <member>
      <StackId>arn:aws:cloudformation:us-east-1:123456789:stack/MyStack/aaf549a0-a413-11df-adb3-5081b3858e83</StackId>
      <StackName>MyStack</StackName>
      <LogicalResourceId>MyAutoScalingGroup</LogicalResourceId>
      <PhysicalResourceId>MyStack_ASG1</PhysicalResourceId>
      <ResourceType>AWS::AutoScalingGroup</ResourceType>
      <Timestamp>2010-07-27T22:28:28.123456Z</Timestamp>
      <ResourceStatus>CREATE_IN_PROGRESS</ResourceStatus>
    </member>
  </StackResources>
</DescribeStackResourcesResult>
"""

class TestStackParse(unittest.TestCase):
    def test_parse_tags(self):
        rs = boto.resultset.ResultSet([('member', boto.cloudformation.stack.Stack)])
        h = boto.handler.XmlHandler(rs, None)
        xml.sax.parseString(SAMPLE_XML, h)
        tags = rs[0].tags
        self.assertEqual(tags, {u'key0': u'value0', u'key1': u'value1'})

    def test_event_creation_time_with_millis(self):
        millis_xml = SAMPLE_XML.replace(
          "<CreationTime>2013-01-10T05:04:56Z</CreationTime>",
          "<CreationTime>2013-01-10T05:04:56.102342Z</CreationTime>"
        )

        rs = boto.resultset.ResultSet([('member', boto.cloudformation.stack.Stack)])
        h = boto.handler.XmlHandler(rs, None)
        xml.sax.parseString(millis_xml, h)
        creation_time = rs[0].creation_time
        self.assertEqual(creation_time, datetime.datetime(2013, 1, 10, 5, 4, 56, 102342))

    def test_resource_time_with_millis(self):
        rs = boto.resultset.ResultSet([('member', boto.cloudformation.stack.StackResource)])
        h = boto.handler.XmlHandler(rs, None)
        xml.sax.parseString(DESCRIBE_STACK_RESOURCE_XML, h)
        timestamp_1= rs[0].timestamp
        self.assertEqual(timestamp_1, datetime.datetime(2010, 7, 27, 22, 27, 28))
        timestamp_2 = rs[1].timestamp
        self.assertEqual(timestamp_2, datetime.datetime(2010, 7, 27, 22, 28, 28, 123456))

if __name__ == '__main__':
    unittest.main()
