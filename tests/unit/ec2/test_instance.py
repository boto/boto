#!/usr/bin/env python

from tests.unit import unittest

import mock

from boto.ec2.connection import EC2Connection


RESPONSE = r"""
<RunInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2012-06-01/">
    <requestId>ad4b83c2-f606-4c39-90c6-5dcc5be823e1</requestId>
    <reservationId>r-c5cef7a7</reservationId>
    <ownerId>184906166255</ownerId>
    <groupSet>
        <item>
            <groupId>sg-99a710f1</groupId>
            <groupName>SSH</groupName>
        </item>
    </groupSet>
    <instancesSet>
        <item>
            <instanceId>i-ff0f1299</instanceId>
            <imageId>ami-ed65ba84</imageId>
            <instanceState>
                <code>0</code>
                <name>pending</name>
            </instanceState>
            <privateDnsName/>
            <dnsName/>
            <reason/>
            <keyName>awskeypair</keyName>
            <amiLaunchIndex>0</amiLaunchIndex>
            <productCodes/>
            <instanceType>t1.micro</instanceType>
            <launchTime>2012-05-30T19:21:18.000Z</launchTime>
            <placement>
                <availabilityZone>us-east-1a</availabilityZone>
                <groupName/>
                <tenancy>default</tenancy>
            </placement>
            <kernelId>aki-b6aa75df</kernelId>
            <monitoring>
                <state>disabled</state>
            </monitoring>
            <groupSet>
                <item>
                    <groupId>sg-99a710f1</groupId>
                    <groupName>SSH</groupName>
                </item>
            </groupSet>
            <stateReason>
                <code>pending</code>
                <message>pending</message>
            </stateReason>
            <architecture>i386</architecture>
            <rootDeviceType>ebs</rootDeviceType>
            <rootDeviceName>/dev/sda1</rootDeviceName>
            <blockDeviceMapping/>
            <virtualizationType>paravirtual</virtualizationType>
            <clientToken/>
            <hypervisor>xen</hypervisor>
            <networkInterfaceSet/>
            <iamInstanceProfile>
                <arn>arn:aws:iam::184906166255:instance-profile/myinstanceprofile</arn>
                <id>AIPAIQ2LVHYBCH7LYQFDK</id>
            </iamInstanceProfile>
        </item>
    </instancesSet>
</RunInstancesResponse>
"""


class TestRunInstanceResponseParsing(unittest.TestCase):
    def testIAMInstanceProfileParsedCorrectly(self):
        ec2 = EC2Connection(aws_access_key_id='aws_access_key_id',
                            aws_secret_access_key='aws_secret_access_key')
        mock_response = mock.Mock()
        mock_response.read.return_value = RESPONSE
        mock_response.status = 200
        ec2.make_request = mock.Mock(return_value=mock_response)
        reservation = ec2.run_instances(image_id='ami-12345')
        self.assertEqual(len(reservation.instances), 1)
        instance = reservation.instances[0]
        self.assertEqual(instance.image_id, 'ami-ed65ba84')
        # iamInstanceProfile has an ID element, so we want to make sure
        # that this does not map to instance.id (which should be the
        # id of the ec2 instance).
        self.assertEqual(instance.id, 'i-ff0f1299')
        self.assertDictEqual(
            instance.instance_profile,
            {'arn': ('arn:aws:iam::184906166255:'
                     'instance-profile/myinstanceprofile'),
             'id': 'AIPAIQ2LVHYBCH7LYQFDK'})


if __name__ == '__main__':
    unittest.main()
