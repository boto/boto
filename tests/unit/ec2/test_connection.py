#!/usr/bin/env python
import httplib

from mock import Mock
from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

import boto.ec2

from boto.regioninfo import RegionInfo
from boto.ec2.connection import EC2Connection


class TestEC2ConnectionBase(AWSMockServiceTestCase):
    connection_class = EC2Connection

    def setUp(self):
        super(TestEC2ConnectionBase, self).setUp()
        self.ec2 = self.service_connection


class TestReservedInstanceOfferings(TestEC2ConnectionBase):

    def default_body(self):
        return """
            <DescribeReservedInstancesOfferingsResponse>
                <requestId>d3253568-edcf-4897-9a3d-fb28e0b3fa38</requestId>
                    <reservedInstancesOfferingsSet>
                    <item>
                        <reservedInstancesOfferingId>2964d1bf71d8</reservedInstancesOfferingId>
                        <instanceType>c1.medium</instanceType>
                        <availabilityZone>us-east-1c</availabilityZone>
                        <duration>94608000</duration>
                        <fixedPrice>775.0</fixedPrice>
                        <usagePrice>0.0</usagePrice>
                        <productDescription>product description</productDescription>
                        <instanceTenancy>default</instanceTenancy>
                        <currencyCode>USD</currencyCode>
                        <offeringType>Heavy Utilization</offeringType>
                        <recurringCharges>
                            <item>
                                <frequency>Hourly</frequency>
                                <amount>0.095</amount>
                            </item>
                        </recurringCharges>
                        <marketplace>false</marketplace>
                        <pricingDetailsSet>
                            <item>
                                <price>0.045</price>
                                <count>1</count>
                            </item>
                        </pricingDetailsSet>
                    </item>
                    <item>
                        <reservedInstancesOfferingId>2dce26e46889</reservedInstancesOfferingId>
                        <instanceType>c1.medium</instanceType>
                        <availabilityZone>us-east-1c</availabilityZone>
                        <duration>94608000</duration>
                        <fixedPrice>775.0</fixedPrice>
                        <usagePrice>0.0</usagePrice>
                        <productDescription>Linux/UNIX</productDescription>
                        <instanceTenancy>default</instanceTenancy>
                        <currencyCode>USD</currencyCode>
                        <offeringType>Heavy Utilization</offeringType>
                        <recurringCharges>
                            <item>
                                <frequency>Hourly</frequency>
                                <amount>0.035</amount>
                            </item>
                        </recurringCharges>
                        <marketplace>false</marketplace>
                        <pricingDetailsSet/>
                    </item>
                </reservedInstancesOfferingsSet>
                <nextToken>next_token</nextToken>
            </DescribeReservedInstancesOfferingsResponse>
        """

    def test_get_reserved_instance_offerings(self):
        self.set_http_response(status_code=200)
        response = self.ec2.get_all_reserved_instances_offerings()
        self.assertEqual(len(response), 2)
        instance = response[0]
        self.assertEqual(instance.id, '2964d1bf71d8')
        self.assertEqual(instance.instance_type, 'c1.medium')
        self.assertEqual(instance.availability_zone, 'us-east-1c')
        self.assertEqual(instance.duration, 94608000)
        self.assertEqual(instance.fixed_price, '775.0')
        self.assertEqual(instance.usage_price, '0.0')
        self.assertEqual(instance.description, 'product description')
        self.assertEqual(instance.instance_tenancy, 'default')
        self.assertEqual(instance.currency_code, 'USD')
        self.assertEqual(instance.offering_type, 'Heavy Utilization')
        self.assertEqual(len(instance.recurring_charges), 1)
        self.assertEqual(instance.recurring_charges[0].frequency, 'Hourly')
        self.assertEqual(instance.recurring_charges[0].amount, '0.095')
        self.assertEqual(len(instance.pricing_details), 1)
        self.assertEqual(instance.pricing_details[0].price, '0.045')
        self.assertEqual(instance.pricing_details[0].count, '1')

    def test_get_reserved_instance_offerings_params(self):
        self.set_http_response(status_code=200)
        self.ec2.get_all_reserved_instances_offerings(
            reserved_instances_offering_ids=['id1','id2'],
            instance_type='t1.micro',
            availability_zone='us-east-1',
            product_description='description',
            instance_tenancy='dedicated',
            offering_type='offering_type',
            include_marketplace=False,
            min_duration=100,
            max_duration=1000,
            max_instance_count=1,
            next_token='next_token',
            max_results=10
        )
        self.assert_request_parameters({
            'Action': 'DescribeReservedInstancesOfferings',
            'ReservedInstancesOfferingId.1': 'id1',
            'ReservedInstancesOfferingId.2': 'id2',
            'InstanceType': 't1.micro',
            'AvailabilityZone': 'us-east-1',
            'ProductDescription': 'description',
            'InstanceTenancy': 'dedicated',
            'OfferingType': 'offering_type',
            'IncludeMarketplace': 'false',
            'MinDuration': '100',
            'MaxDuration': '1000',
            'MaxInstanceCount': '1',
            'NextToken': 'next_token',
            'MaxResults': '10',},
             ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                   'SignatureVersion', 'Timestamp', 'Version'])


class TestPurchaseReservedInstanceOffering(TestEC2ConnectionBase):
    def default_body(self):
        return """<PurchaseReservedInstancesOffering />"""

    def test_serialized_api_args(self):
        self.set_http_response(status_code=200)
        response = self.ec2.purchase_reserved_instance_offering(
                'offering_id', 1, (100.0, 'USD'))
        self.assert_request_parameters({
            'Action': 'PurchaseReservedInstancesOffering',
            'InstanceCount': 1,
            'ReservedInstancesOfferingId': 'offering_id',
            'LimitPrice.Amount': '100.0',
            'LimitPrice.CurrencyCode': 'USD',},
             ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                   'SignatureVersion', 'Timestamp',
                                   'Version'])


class TestCancelReservedInstancesListing(TestEC2ConnectionBase):
    def default_body(self):
        return """
            <CancelReservedInstancesListingResponse>
                <requestId>request_id</requestId>
                <reservedInstancesListingsSet>
                    <item>
                        <reservedInstancesListingId>listing_id</reservedInstancesListingId>
                        <reservedInstancesId>instance_id</reservedInstancesId>
                        <createDate>2012-07-12T16:55:28.000Z</createDate>
                        <updateDate>2012-07-12T16:55:28.000Z</updateDate>
                        <status>cancelled</status>
                        <statusMessage>CANCELLED</statusMessage>
                        <instanceCounts>
                            <item>
                                <state>Available</state>
                                <instanceCount>0</instanceCount>
                            </item>
                            <item>
                                <state>Sold</state>
                                <instanceCount>0</instanceCount>
                            </item>
                            <item>
                                <state>Cancelled</state>
                                <instanceCount>1</instanceCount>
                            </item>
                            <item>
                                <state>Pending</state>
                                <instanceCount>0</instanceCount>
                            </item>
                        </instanceCounts>
                        <priceSchedules>
                            <item>
                                <term>5</term>
                                <price>166.64</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>4</term>
                                <price>133.32</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>3</term>
                                <price>99.99</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>2</term>
                                <price>66.66</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>1</term>
                                <price>33.33</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                        </priceSchedules>
                        <tagSet/>
                        <clientToken>XqJIt1342112125076</clientToken>
                    </item>
                </reservedInstancesListingsSet>
            </CancelReservedInstancesListingResponse>
        """

    def test_reserved_instances_listing(self):
        self.set_http_response(status_code=200)
        response = self.ec2.cancel_reserved_instances_listing()
        self.assertEqual(len(response), 1)
        cancellation = response[0]
        self.assertEqual(cancellation.status, 'cancelled')
        self.assertEqual(cancellation.status_message, 'CANCELLED')
        self.assertEqual(len(cancellation.instance_counts), 4)
        first = cancellation.instance_counts[0]
        self.assertEqual(first.state, 'Available')
        self.assertEqual(first.instance_count, 0)
        self.assertEqual(len(cancellation.price_schedules), 5)
        schedule = cancellation.price_schedules[0]
        self.assertEqual(schedule.term, 5)
        self.assertEqual(schedule.price, '166.64')
        self.assertEqual(schedule.currency_code, 'USD')
        self.assertEqual(schedule.active, False)


class TestCreateReservedInstancesListing(TestEC2ConnectionBase):
    def default_body(self):
        return """
            <CreateReservedInstancesListingResponse>
                <requestId>request_id</requestId>
                <reservedInstancesListingsSet>
                    <item>
                        <reservedInstancesListingId>listing_id</reservedInstancesListingId>
                        <reservedInstancesId>instance_id</reservedInstancesId>
                        <createDate>2012-07-17T17:11:09.449Z</createDate>
                        <updateDate>2012-07-17T17:11:09.468Z</updateDate>
                        <status>active</status>
                        <statusMessage>ACTIVE</statusMessage>
                        <instanceCounts>
                            <item>
                                <state>Available</state>
                                <instanceCount>1</instanceCount>
                            </item>
                            <item>
                                <state>Sold</state>
                                <instanceCount>0</instanceCount>
                            </item>
                            <item>
                                <state>Cancelled</state>
                                <instanceCount>0</instanceCount>
                            </item>
                            <item>
                                <state>Pending</state>
                                <instanceCount>0</instanceCount>
                            </item>
                        </instanceCounts>
                        <priceSchedules>
                            <item>
                                <term>11</term>
                                <price>2.5</price>
                                <currencyCode>USD</currencyCode>
                                <active>true</active>
                            </item>
                            <item>
                                <term>10</term>
                                <price>2.5</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>9</term>
                                <price>2.5</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>8</term>
                                <price>2.0</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>7</term>
                                <price>2.0</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>6</term>
                                <price>2.0</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>5</term>
                                <price>1.5</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>4</term>
                                <price>1.5</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>3</term>
                                <price>0.7</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>2</term>
                                <price>0.7</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                            <item>
                                <term>1</term>
                                <price>0.1</price>
                                <currencyCode>USD</currencyCode>
                                <active>false</active>
                            </item>
                        </priceSchedules>
                        <tagSet/>
                        <clientToken>myIdempToken1</clientToken>
                    </item>
                </reservedInstancesListingsSet>
            </CreateReservedInstancesListingResponse>
        """

    def test_create_reserved_instances_listing(self):
        self.set_http_response(status_code=200)
        response = self.ec2.create_reserved_instances_listing(
            'instance_id', 1, [('2.5', 11), ('2.0', 8)], 'client_token')
        self.assertEqual(len(response), 1)
        cancellation = response[0]
        self.assertEqual(cancellation.status, 'active')
        self.assertEqual(cancellation.status_message, 'ACTIVE')
        self.assertEqual(len(cancellation.instance_counts), 4)
        first = cancellation.instance_counts[0]
        self.assertEqual(first.state, 'Available')
        self.assertEqual(first.instance_count, 1)
        self.assertEqual(len(cancellation.price_schedules), 11)
        schedule = cancellation.price_schedules[0]
        self.assertEqual(schedule.term, 11)
        self.assertEqual(schedule.price, '2.5')
        self.assertEqual(schedule.currency_code, 'USD')
        self.assertEqual(schedule.active, True)

        self.assert_request_parameters({
            'Action': 'CreateReservedInstancesListing',
            'ReservedInstancesId': 'instance_id',
            'InstanceCount': '1',
            'ClientToken': 'client_token',
            'PriceSchedules.0.Price': '2.5',
            'PriceSchedules.0.Term': '11',
            'PriceSchedules.1.Price': '2.0',
            'PriceSchedules.1.Term': '8',},
             ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                   'SignatureVersion', 'Timestamp',
                                   'Version'])


class TestDescribeSpotInstanceRequests(TestEC2ConnectionBase):
    def default_body(self):
        return """
        <DescribeSpotInstanceRequestsResponse>
            <requestId>requestid</requestId>
            <spotInstanceRequestSet>
                <item>
                    <spotInstanceRequestId>sir-id</spotInstanceRequestId>
                    <spotPrice>0.003000</spotPrice>
                    <type>one-time</type>
                    <state>active</state>
                    <status>
                        <code>fulfilled</code>
                        <updateTime>2012-10-19T18:09:26.000Z</updateTime>
                        <message>Your Spot request is fulfilled.</message>
                    </status>
                    <launchGroup>mylaunchgroup</launchGroup>
                    <launchSpecification>
                        <imageId>ami-id</imageId>
                        <keyName>mykeypair</keyName>
                        <groupSet>
                            <item>
                                <groupId>sg-id</groupId>
                                <groupName>groupname</groupName>
                            </item>
                        </groupSet>
                        <instanceType>t1.micro</instanceType>
                        <monitoring>
                            <enabled>false</enabled>
                        </monitoring>
                    </launchSpecification>
                    <instanceId>i-id</instanceId>
                    <createTime>2012-10-19T18:07:05.000Z</createTime>
                    <productDescription>Linux/UNIX</productDescription>
                    <launchedAvailabilityZone>us-east-1d</launchedAvailabilityZone>
                </item>
            </spotInstanceRequestSet>
        </DescribeSpotInstanceRequestsResponse>
        """

    def test_describe_spot_instance_requets(self):
        self.set_http_response(status_code=200)
        response = self.ec2.get_all_spot_instance_requests()
        self.assertEqual(len(response), 1)
        spotrequest = response[0]
        self.assertEqual(spotrequest.id, 'sir-id')
        self.assertEqual(spotrequest.price, 0.003)
        self.assertEqual(spotrequest.type, 'one-time')
        self.assertEqual(spotrequest.state, 'active')
        self.assertEqual(spotrequest.fault, None)
        self.assertEqual(spotrequest.valid_from, None)
        self.assertEqual(spotrequest.valid_until, None)
        self.assertEqual(spotrequest.launch_group, 'mylaunchgroup')
        self.assertEqual(spotrequest.launched_availability_zone, 'us-east-1d')
        self.assertEqual(spotrequest.product_description, 'Linux/UNIX')
        self.assertEqual(spotrequest.availability_zone_group, None)
        self.assertEqual(spotrequest.create_time,
                         '2012-10-19T18:07:05.000Z')
        self.assertEqual(spotrequest.instance_id, 'i-id')
        launch_spec = spotrequest.launch_specification
        self.assertEqual(launch_spec.key_name, 'mykeypair')
        self.assertEqual(launch_spec.instance_type, 't1.micro')
        self.assertEqual(launch_spec.image_id, 'ami-id')
        self.assertEqual(launch_spec.placement, None)
        self.assertEqual(launch_spec.kernel, None)
        self.assertEqual(launch_spec.ramdisk, None)
        self.assertEqual(launch_spec.monitored, False)
        self.assertEqual(launch_spec.subnet_id, None)
        self.assertEqual(launch_spec.block_device_mapping, None)
        self.assertEqual(launch_spec.instance_profile, None)
        self.assertEqual(launch_spec.ebs_optimized, False)
        status = spotrequest.status
        self.assertEqual(status.code, 'fulfilled')
        self.assertEqual(status.update_time, '2012-10-19T18:09:26.000Z')
        self.assertEqual(status.message, 'Your Spot request is fulfilled.')


class TestCopySnapshot(TestEC2ConnectionBase):
    def default_body(self):
        return """
        <CopySnapshotResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
            <requestId>request_id</requestId>
            <snapshotId>snap-copied-id</snapshotId>
        </CopySnapshotResponse>
        """

    def test_copy_snapshot(self):
        self.set_http_response(status_code=200)
        snapshot_id = self.ec2.copy_snapshot('us-west-2', 'snap-id',
                                             'description')
        self.assertEqual(snapshot_id, 'snap-copied-id')

        self.assert_request_parameters({
            'Action': 'CopySnapshot',
            'Description': 'description',
            'SourceRegion': 'us-west-2',
            'SourceSnapshotId': 'snap-id'},
             ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                   'SignatureVersion', 'Timestamp',
                                   'Version'])


class TestAccountAttributes(TestEC2ConnectionBase):
    def default_body(self):
        return """
        <DescribeAccountAttributesResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
            <requestId>6d042e8a-4bc3-43e8-8265-3cbc54753f14</requestId>
            <accountAttributeSet>
                <item>
                    <attributeName>vpc-max-security-groups-per-interface</attributeName>
                    <attributeValueSet>
                        <item>
                            <attributeValue>5</attributeValue>
                        </item>
                    </attributeValueSet>
                </item>
                <item>
                    <attributeName>max-instances</attributeName>
                    <attributeValueSet>
                        <item>
                            <attributeValue>50</attributeValue>
                        </item>
                    </attributeValueSet>
                </item>
                <item>
                    <attributeName>supported-platforms</attributeName>
                    <attributeValueSet>
                        <item>
                            <attributeValue>EC2</attributeValue>
                        </item>
                        <item>
                            <attributeValue>VPC</attributeValue>
                        </item>
                    </attributeValueSet>
                </item>
                <item>
                    <attributeName>default-vpc</attributeName>
                    <attributeValueSet>
                        <item>
                            <attributeValue>none</attributeValue>
                        </item>
                    </attributeValueSet>
                </item>
            </accountAttributeSet>
        </DescribeAccountAttributesResponse>
        """

    def test_describe_account_attributes(self):
        self.set_http_response(status_code=200)
        parsed = self.ec2.describe_account_attributes()
        self.assertEqual(len(parsed), 4)
        self.assertEqual(parsed[0].attribute_name,
                         'vpc-max-security-groups-per-interface')
        self.assertEqual(parsed[0].attribute_values,
                         ['5'])
        self.assertEqual(parsed[-1].attribute_name,
                         'default-vpc')
        self.assertEqual(parsed[-1].attribute_values,
                         ['none'])


class TestDescribeVPCAttribute(TestEC2ConnectionBase):
    def default_body(self):
        return """
        <DescribeVpcAttributeResponse xmlns="http://ec2.amazonaws.com/doc/2013-02-01/">
            <requestId>request_id</requestId>
            <vpcId>vpc-id</vpcId>
            <enableDnsHostnames>
                <value>false</value>
            </enableDnsHostnames>
        </DescribeVpcAttributeResponse>
        """

    def test_describe_vpc_attribute(self):
        self.set_http_response(status_code=200)
        parsed = self.ec2.describe_vpc_attribute('vpc-id',
                                                 'enableDnsHostnames')
        self.assertEqual(parsed.vpc_id, 'vpc-id')
        self.assertFalse(parsed.enable_dns_hostnames)
        self.assert_request_parameters({
            'Action': 'DescribeVpcAttribute',
            'VpcId': 'vpc-id',
            'Attribute': 'enableDnsHostnames',},
             ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                   'SignatureVersion', 'Timestamp',
                                   'Version'])


class TestGetAllNetworkInterfaces(TestEC2ConnectionBase):
    def default_body(self):
        return """
<DescribeNetworkInterfacesResponse xmlns="http://ec2.amazonaws.com/\
    doc/2013-06-15/">
    <requestId>fc45294c-006b-457b-bab9-012f5b3b0e40</requestId>
     <networkInterfaceSet>
       <item>
         <networkInterfaceId>eni-0f62d866</networkInterfaceId>
         <subnetId>subnet-c53c87ac</subnetId>
         <vpcId>vpc-cc3c87a5</vpcId>
         <availabilityZone>ap-southeast-1b</availabilityZone>
         <description/>
         <ownerId>053230519467</ownerId>
         <requesterManaged>false</requesterManaged>
         <status>in-use</status>
         <macAddress>02:81:60:cb:27:37</macAddress>
         <privateIpAddress>10.0.0.146</privateIpAddress>
         <sourceDestCheck>true</sourceDestCheck>
         <groupSet>
           <item>
             <groupId>sg-3f4b5653</groupId>
             <groupName>default</groupName>
           </item>
         </groupSet>
         <attachment>
           <attachmentId>eni-attach-6537fc0c</attachmentId>
           <instanceId>i-22197876</instanceId>
           <instanceOwnerId>053230519467</instanceOwnerId>
           <deviceIndex>5</deviceIndex>
           <status>attached</status>
           <attachTime>2012-07-01T21:45:27.000Z</attachTime>
           <deleteOnTermination>true</deleteOnTermination>
         </attachment>
         <tagSet/>
         <privateIpAddressesSet>
           <item>
             <privateIpAddress>10.0.0.146</privateIpAddress>
             <primary>true</primary>
           </item>
           <item>
             <privateIpAddress>10.0.0.148</privateIpAddress>
             <primary>false</primary>
           </item>
           <item>
             <privateIpAddress>10.0.0.150</privateIpAddress>
             <primary>false</primary>
           </item>
         </privateIpAddressesSet>
       </item>
    </networkInterfaceSet>
</DescribeNetworkInterfacesResponse>"""

    def test_attachment_has_device_index(self):
        self.set_http_response(status_code=200)
        parsed = self.ec2.get_all_network_interfaces()

        self.assertEqual(5, parsed[0].attachment.device_index)


class TestModifyInterfaceAttribute(TestEC2ConnectionBase):
    def default_body(self):
        return """
<ModifyNetworkInterfaceAttributeResponse \
    xmlns="http://ec2.amazonaws.com/doc/2013-06-15/">
    <requestId>657a4623-5620-4232-b03b-427e852d71cf</requestId>
    <return>true</return>
</ModifyNetworkInterfaceAttributeResponse>
"""

    def test_modify_description(self):
        self.set_http_response(status_code=200)
        self.ec2.modify_network_interface_attribute('id', 'description', 'foo')

        self.assert_request_parameters({
            'Action': 'ModifyNetworkInterfaceAttribute',
            'NetworkInterfaceId': 'id',
            'Description.Value': 'foo'},
             ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                   'SignatureVersion', 'Timestamp',
                                   'Version'])

    def test_modify_source_dest_check_bool(self):
        self.set_http_response(status_code=200)
        self.ec2.modify_network_interface_attribute('id', 'sourceDestCheck', True)

        self.assert_request_parameters({
            'Action': 'ModifyNetworkInterfaceAttribute',
            'NetworkInterfaceId': 'id',
            'SourceDestCheck.Value': 'true'},
             ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                   'SignatureVersion', 'Timestamp',
                                   'Version'])

    def test_modify_source_dest_check_str(self):
        self.set_http_response(status_code=200)
        self.ec2.modify_network_interface_attribute('id', 'sourceDestCheck',
                                                    'true')

        self.assert_request_parameters({
            'Action': 'ModifyNetworkInterfaceAttribute',
            'NetworkInterfaceId': 'id',
            'SourceDestCheck.Value': 'true'},
             ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                   'SignatureVersion', 'Timestamp',
                                   'Version'])

    def test_modify_source_dest_check_invalid(self):
        self.set_http_response(status_code=200)

        with self.assertRaises(ValueError):
            self.ec2.modify_network_interface_attribute('id', 'sourceDestCheck', 123)

    def test_modify_delete_on_termination_str(self):
        self.set_http_response(status_code=200)
        self.ec2.modify_network_interface_attribute('id', 'deleteOnTermination',
                                                    True, attachment_id='bar')

        self.assert_request_parameters({
            'Action': 'ModifyNetworkInterfaceAttribute',
            'NetworkInterfaceId': 'id',
            'Attachment.AttachmentId': 'bar',
            'Attachment.DeleteOnTermination': 'true'},
             ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                   'SignatureVersion', 'Timestamp',
                                   'Version'])

    def test_modify_delete_on_termination_bool(self):
        self.set_http_response(status_code=200)
        self.ec2.modify_network_interface_attribute('id', 'deleteOnTermination',
                                                    'false', attachment_id='bar')

        self.assert_request_parameters({
            'Action': 'ModifyNetworkInterfaceAttribute',
            'NetworkInterfaceId': 'id',
            'Attachment.AttachmentId': 'bar',
            'Attachment.DeleteOnTermination': 'false'},
             ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                   'SignatureVersion', 'Timestamp',
                                   'Version'])

    def test_modify_delete_on_termination_invalid(self):
        self.set_http_response(status_code=200)

        with self.assertRaises(ValueError):
            self.ec2.modify_network_interface_attribute('id', 'deleteOnTermination',
                                                    123, attachment_id='bar')

    def test_modify_group_set_list(self):
        self.set_http_response(status_code=200)
        self.ec2.modify_network_interface_attribute('id', 'groupSet',
                                                    ['sg-1', 'sg-2'])

        self.assert_request_parameters({
            'Action': 'ModifyNetworkInterfaceAttribute',
            'NetworkInterfaceId': 'id',
            'SecurityGroupId.1': 'sg-1',
            'SecurityGroupId.2': 'sg-2'},
             ignore_params_values=['AWSAccessKeyId', 'SignatureMethod',
                                   'SignatureVersion', 'Timestamp',
                                   'Version'])

    def test_modify_group_set_invalid(self):
        self.set_http_response(status_code=200)

        with self.assertRaisesRegexp(TypeError, 'iterable'):
            self.ec2.modify_network_interface_attribute('id', 'groupSet',
                                                        False)

    def test_modify_attr_invalid(self):
        self.set_http_response(status_code=200)

        with self.assertRaisesRegexp(ValueError, 'Unknown attribute'):
            self.ec2.modify_network_interface_attribute('id', 'invalid', 0)


class TestConnectToRegion(unittest.TestCase):
    def setUp(self):
        self.https_connection = Mock(spec=httplib.HTTPSConnection)
        self.https_connection_factory = (
            Mock(return_value=self.https_connection), ())

    def test_aws_region(self):
        region = boto.ec2.RegionData.keys()[0]
        self.ec2 = boto.ec2.connect_to_region(region,
            https_connection_factory=self.https_connection_factory,
            aws_access_key_id='aws_access_key_id',
            aws_secret_access_key='aws_secret_access_key'
        )
        self.assertEqual(boto.ec2.RegionData[region], self.ec2.host)

    def test_non_aws_region(self):
        self.ec2 = boto.ec2.connect_to_region('foo',
            https_connection_factory=self.https_connection_factory,
            aws_access_key_id='aws_access_key_id',
            aws_secret_access_key='aws_secret_access_key',
            region = RegionInfo(name='foo', endpoint='https://foo.com/bar')
        )
        self.assertEqual('https://foo.com/bar', self.ec2.host)

    def test_missing_region(self):
        self.ec2 = boto.ec2.connect_to_region('foo',
            https_connection_factory=self.https_connection_factory,
            aws_access_key_id='aws_access_key_id',
            aws_secret_access_key='aws_secret_access_key'
        )
        self.assertEqual(None, self.ec2)


if __name__ == '__main__':
    unittest.main()
