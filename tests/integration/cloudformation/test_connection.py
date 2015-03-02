#!/usr/bin/env python
import time
import json

from tests.unit import  unittest
from boto.cloudformation.connection import CloudFormationConnection


BASIC_EC2_TEMPLATE = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "AWS CloudFormation Sample Template EC2InstanceSample",
    "Parameters": {
    },
    "Mappings": {
        "RegionMap": {
            "us-east-1": {
                "AMI": "ami-7f418316"
            }
        }
    },
    "Resources": {
        "Ec2Instance": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "ImageId": {
                    "Fn::FindInMap": [
                        "RegionMap",
                        {
                            "Ref": "AWS::Region"
                        },
                        "AMI"
                    ]
                },
                "UserData": {
                    "Fn::Base64": "a" * 15000
                }
            }
        }
    },
    "Outputs": {
        "InstanceId": {
            "Description": "InstanceId of the newly created EC2 instance",
            "Value": {
                "Ref": "Ec2Instance"
            }
        },
        "AZ": {
            "Description": "Availability Zone of the newly created EC2 instance",
            "Value": {
                "Fn::GetAtt": [
                    "Ec2Instance",
                    "AvailabilityZone"
                ]
            }
        },
        "PublicIP": {
            "Description": "Public IP address of the newly created EC2 instance",
            "Value": {
                "Fn::GetAtt": [
                    "Ec2Instance",
                    "PublicIp"
                ]
            }
        },
        "PrivateIP": {
            "Description": "Private IP address of the newly created EC2 instance",
            "Value": {
                "Fn::GetAtt": [
                    "Ec2Instance",
                    "PrivateIp"
                ]
            }
        },
        "PublicDNS": {
            "Description": "Public DNSName of the newly created EC2 instance",
            "Value": {
                "Fn::GetAtt": [
                    "Ec2Instance",
                    "PublicDnsName"
                ]
            }
        },
        "PrivateDNS": {
            "Description": "Private DNSName of the newly created EC2 instance",
            "Value": {
                "Fn::GetAtt": [
                    "Ec2Instance",
                    "PrivateDnsName"
                ]
            }
        }
    }
}


class TestCloudformationConnection(unittest.TestCase):
    def setUp(self):
        self.connection = CloudFormationConnection()
        self.stack_name = 'testcfnstack' + str(int(time.time()))

    def test_large_template_stack_size(self):
        # See https://github.com/boto/boto/issues/1037
        body = self.connection.create_stack(
            self.stack_name,
            template_body=json.dumps(BASIC_EC2_TEMPLATE))
        self.addCleanup(self.connection.delete_stack, self.stack_name)

        # A newly created stack should have events
        events = self.connection.describe_stack_events(self.stack_name)
        self.assertTrue(events)

        # No policy should be set on the stack by default
        policy = self.connection.get_stack_policy(self.stack_name)
        self.assertEqual(None, policy)

        # Our new stack should show up in the stack list
        stacks = self.connection.describe_stacks()
        self.assertEqual(self.stack_name, stacks[0].stack_name)


if __name__ == '__main__':
    unittest.main()
