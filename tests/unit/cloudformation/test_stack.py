#!/usr/bin/env python
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

class TestStackParse(unittest.TestCase):
    def test_parse_tags(self):
        rs = boto.resultset.ResultSet([('member', boto.cloudformation.stack.Stack)])
        h = boto.handler.XmlHandler(rs, None)
        xml.sax.parseString(SAMPLE_XML, h)
        tags = rs[0].tags
        self.assertEqual(tags, {u'key0': u'value0', u'key1': u'value1'})

if __name__ == '__main__':
    unittest.main()
