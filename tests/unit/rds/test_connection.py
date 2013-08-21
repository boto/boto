#!/usr/bin/env python
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

from tests.unit import unittest
from tests.unit import AWSMockServiceTestCase

from boto.rds import RDSConnection
from boto.rds.parametergroup import ParameterGroup


class TestRDSConnection(AWSMockServiceTestCase):
    connection_class = RDSConnection

    def setUp(self):
        super(TestRDSConnection, self).setUp()

    def default_body(self):
        return """
        <DescribeDBInstancesResponse>
          <DescribeDBInstancesResult>
            <DBInstances>
                <DBInstance>
                  <Iops>2000</Iops>
                  <BackupRetentionPeriod>1</BackupRetentionPeriod>
                  <MultiAZ>false</MultiAZ>
                  <DBInstanceStatus>backing-up</DBInstanceStatus>
                  <DBInstanceIdentifier>mydbinstance2</DBInstanceIdentifier>
                  <PreferredBackupWindow>10:30-11:00</PreferredBackupWindow>
                  <PreferredMaintenanceWindow>wed:06:30-wed:07:00</PreferredMaintenanceWindow>
                  <OptionGroupMembership>
                    <OptionGroupName>default:mysql-5-5</OptionGroupName>
                    <Status>in-sync</Status>
                  </OptionGroupMembership>
                  <AvailabilityZone>us-west-2b</AvailabilityZone>
                  <ReadReplicaDBInstanceIdentifiers/>
                  <Engine>mysql</Engine>
                  <PendingModifiedValues/>
                  <LicenseModel>general-public-license</LicenseModel>
                  <DBParameterGroups>
                    <DBParameterGroup>
                      <ParameterApplyStatus>in-sync</ParameterApplyStatus>
                      <DBParameterGroupName>default.mysql5.5</DBParameterGroupName>
                    </DBParameterGroup>
                  </DBParameterGroups>
                  <Endpoint>
                    <Port>3306</Port>
                    <Address>mydbinstance2.c0hjqouvn9mf.us-west-2.rds.amazonaws.com</Address>
                  </Endpoint>
                  <EngineVersion>5.5.27</EngineVersion>
                  <DBSecurityGroups>
                    <DBSecurityGroup>
                      <Status>active</Status>
                      <DBSecurityGroupName>default</DBSecurityGroupName>
                    </DBSecurityGroup>
                  </DBSecurityGroups>
                  <DBName>mydb2</DBName>
                  <AutoMinorVersionUpgrade>true</AutoMinorVersionUpgrade>
                  <InstanceCreateTime>2012-10-03T22:01:51.047Z</InstanceCreateTime>
                  <AllocatedStorage>200</AllocatedStorage>
                  <DBInstanceClass>db.m1.large</DBInstanceClass>
                  <MasterUsername>awsuser</MasterUsername>
                  <StatusInfos>
                    <DBInstanceStatusInfo>
                      <Message></Message>
                      <Normal>true</Normal>
                      <Status>replicating</Status>
                      <StatusType>read replication</StatusType>
                    </DBInstanceStatusInfo>
                  </StatusInfos>
                </DBInstance>
            </DBInstances>
          </DescribeDBInstancesResult>
        </DescribeDBInstancesResponse>
        """

    def test_get_all_db_instances(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.get_all_dbinstances('instance_id')
        self.assertEqual(len(response), 1)
        self.assert_request_parameters({
            'Action': 'DescribeDBInstances',
            'DBInstanceIdentifier': 'instance_id',
        }, ignore_params_values=['Version'])
        db = response[0]
        self.assertEqual(db.id, 'mydbinstance2')
        self.assertEqual(db.create_time, '2012-10-03T22:01:51.047Z')
        self.assertEqual(db.engine, 'mysql')
        self.assertEqual(db.status, 'backing-up')
        self.assertEqual(db.allocated_storage, 200)
        self.assertEqual(
            db.endpoint,
            (u'mydbinstance2.c0hjqouvn9mf.us-west-2.rds.amazonaws.com', 3306))
        self.assertEqual(db.instance_class, 'db.m1.large')
        self.assertEqual(db.master_username, 'awsuser')
        self.assertEqual(db.availability_zone, 'us-west-2b')
        self.assertEqual(db.backup_retention_period, '1')
        self.assertEqual(db.preferred_backup_window, '10:30-11:00')
        self.assertEqual(db.preferred_maintenance_window,
                         'wed:06:30-wed:07:00')
        self.assertEqual(db.latest_restorable_time, None)
        self.assertEqual(db.multi_az, False)
        self.assertEqual(db.iops, 2000)
        self.assertEqual(db.pending_modified_values, {})

        self.assertEqual(db.parameter_group.name,
                         'default.mysql5.5')
        self.assertEqual(db.parameter_group.description, None)
        self.assertEqual(db.parameter_group.engine, None)

        self.assertEqual(db.security_group.owner_id, None)
        self.assertEqual(db.security_group.name, 'default')
        self.assertEqual(db.security_group.description, None)
        self.assertEqual(db.security_group.ec2_groups, [])
        self.assertEqual(db.security_group.ip_ranges, [])
        self.assertEqual(len(db.status_infos), 1)
        self.assertEqual(db.status_infos[0].message, '')
        self.assertEqual(db.status_infos[0].normal, True)
        self.assertEqual(db.status_infos[0].status, 'replicating')
        self.assertEqual(db.status_infos[0].status_type, 'read replication')


class TestRDSCCreateDBInstance(AWSMockServiceTestCase):
    connection_class = RDSConnection

    def setUp(self):
        super(TestRDSCCreateDBInstance, self).setUp()

    def default_body(self):
        return """
        <CreateDBInstanceResponse xmlns="http://rds.amazonaws.com/doc/2013-05-15/">
            <CreateDBInstanceResult>
                <DBInstance>
                    <ReadReplicaDBInstanceIdentifiers/>
                    <Engine>mysql</Engine>
                    <PendingModifiedValues>
                        <MasterUserPassword>****</MasterUserPassword>
                    </PendingModifiedValues>
                    <BackupRetentionPeriod>1</BackupRetentionPeriod>
                    <MultiAZ>false</MultiAZ>
                    <LicenseModel>general-public-license</LicenseModel>
                    <DBSubnetGroup>
                        <VpcId>990524496922</VpcId>
                        <SubnetGroupStatus>Complete</SubnetGroupStatus>
                        <DBSubnetGroupDescription>description</DBSubnetGroupDescription>
                        <DBSubnetGroupName>subnet_grp1</DBSubnetGroupName>
                        <Subnets>
                            <Subnet>
                                <SubnetStatus>Active</SubnetStatus>
                                <SubnetIdentifier>subnet-7c5b4115</SubnetIdentifier>
                                <SubnetAvailabilityZone>
                                    <Name>us-east-1c</Name>
                                </SubnetAvailabilityZone>
                            </Subnet>
                            <Subnet>
                                <SubnetStatus>Active</SubnetStatus>
                                <SubnetIdentifier>subnet-7b5b4112</SubnetIdentifier>
                                <SubnetAvailabilityZone>
                                    <Name>us-east-1b</Name>
                                </SubnetAvailabilityZone>
                            </Subnet>
                            <Subnet>
                                <SubnetStatus>Active</SubnetStatus>
                                <SubnetIdentifier>subnet-3ea6bd57</SubnetIdentifier>
                                <SubnetAvailabilityZone>
                                    <Name>us-east-1d</Name>
                                </SubnetAvailabilityZone>
                            </Subnet>
                        </Subnets>
                    </DBSubnetGroup>
                    <DBInstanceStatus>creating</DBInstanceStatus>
                    <EngineVersion>5.1.50</EngineVersion>
                    <DBInstanceIdentifier>simcoprod01</DBInstanceIdentifier>
                    <DBParameterGroups>
                        <DBParameterGroup>
                            <ParameterApplyStatus>in-sync</ParameterApplyStatus>
                            <DBParameterGroupName>default.mysql5.1</DBParameterGroupName>
                        </DBParameterGroup>
                    </DBParameterGroups>
                    <DBSecurityGroups>
                        <DBSecurityGroup>
                            <Status>active</Status>
                            <DBSecurityGroupName>default</DBSecurityGroupName>
                        </DBSecurityGroup>
                    </DBSecurityGroups>
                    <PreferredBackupWindow>00:00-00:30</PreferredBackupWindow>
                    <AutoMinorVersionUpgrade>true</AutoMinorVersionUpgrade>
                    <PreferredMaintenanceWindow>sat:07:30-sat:08:00</PreferredMaintenanceWindow>
                        <AllocatedStorage>10</AllocatedStorage>
                        <DBInstanceClass>db.m1.large</DBInstanceClass>
                        <MasterUsername>master</MasterUsername>
                </DBInstance>
            </CreateDBInstanceResult>
            <ResponseMetadata>
                <RequestId>2e5d4270-8501-11e0-bd9b-a7b1ece36d51</RequestId>
            </ResponseMetadata>
        </CreateDBInstanceResponse>
        """

    def test_create_db_instance_param_group_name(self):
        self.set_http_response(status_code=200)
        db = self.service_connection.create_dbinstance(
            'SimCoProd01',
            10,
            'db.m1.large',
            'master',
            'Password01',
            param_group='default.mysql5.1',
            db_subnet_group_name='dbSubnetgroup01')

        self.assert_request_parameters({
            'Action': 'CreateDBInstance',
            'AllocatedStorage': 10,
            'AutoMinorVersionUpgrade': 'true',
            'DBInstanceClass': 'db.m1.large',
            'DBInstanceIdentifier': 'SimCoProd01',
            'DBParameterGroupName': 'default.mysql5.1',
            'DBSubnetGroupName': 'dbSubnetgroup01',
            'Engine': 'MySQL5.1',
            'MasterUsername': 'master',
            'MasterUserPassword': 'Password01',
            'Port': 3306,
        }, ignore_params_values=['Version'])

        self.assertEqual(db.id, 'simcoprod01')
        self.assertEqual(db.engine, 'mysql')
        self.assertEqual(db.status, 'creating')
        self.assertEqual(db.allocated_storage, 10)
        self.assertEqual(db.instance_class, 'db.m1.large')
        self.assertEqual(db.master_username, 'master')
        self.assertEqual(db.multi_az, False)
        self.assertEqual(db.pending_modified_values,
            {'MasterUserPassword': '****'})

        self.assertEqual(db.parameter_group.name,
                         'default.mysql5.1')
        self.assertEqual(db.parameter_group.description, None)
        self.assertEqual(db.parameter_group.engine, None)

    def test_create_db_instance_param_group_instance(self):
        self.set_http_response(status_code=200)
        param_group = ParameterGroup()
        param_group.name = 'default.mysql5.1'
        db = self.service_connection.create_dbinstance(
            'SimCoProd01',
            10,
            'db.m1.large',
            'master',
            'Password01',
            param_group=param_group,
            db_subnet_group_name='dbSubnetgroup01')

        self.assert_request_parameters({
            'Action': 'CreateDBInstance',
            'AllocatedStorage': 10,
            'AutoMinorVersionUpgrade': 'true',
            'DBInstanceClass': 'db.m1.large',
            'DBInstanceIdentifier': 'SimCoProd01',
            'DBParameterGroupName': 'default.mysql5.1',
            'DBSubnetGroupName': 'dbSubnetgroup01',
            'Engine': 'MySQL5.1',
            'MasterUsername': 'master',
            'MasterUserPassword': 'Password01',
            'Port': 3306,
        }, ignore_params_values=['Version'])

        self.assertEqual(db.id, 'simcoprod01')
        self.assertEqual(db.engine, 'mysql')
        self.assertEqual(db.status, 'creating')
        self.assertEqual(db.allocated_storage, 10)
        self.assertEqual(db.instance_class, 'db.m1.large')
        self.assertEqual(db.master_username, 'master')
        self.assertEqual(db.multi_az, False)
        self.assertEqual(db.pending_modified_values,
            {'MasterUserPassword': '****'})
        self.assertEqual(db.parameter_group.name,
                         'default.mysql5.1')
        self.assertEqual(db.parameter_group.description, None)
        self.assertEqual(db.parameter_group.engine, None)


class TestRDSConnectionRestoreDBInstanceFromPointInTime(AWSMockServiceTestCase):
    connection_class = RDSConnection

    def setUp(self):
        super(TestRDSConnectionRestoreDBInstanceFromPointInTime, self).setUp()

    def default_body(self):
        return """
        <RestoreDBInstanceToPointInTimeResponse xmlns="http://rds.amazonaws.com/doc/2013-05-15/">
          <RestoreDBInstanceToPointInTimeResult>
            <DBInstance>
              <ReadReplicaDBInstanceIdentifiers/>
              <Engine>mysql</Engine>
              <PendingModifiedValues/>
              <BackupRetentionPeriod>1</BackupRetentionPeriod>
              <MultiAZ>false</MultiAZ>
              <LicenseModel>general-public-license</LicenseModel>
              <DBInstanceStatus>creating</DBInstanceStatus>
              <EngineVersion>5.1.50</EngineVersion>
              <DBInstanceIdentifier>restored-db</DBInstanceIdentifier>
              <DBParameterGroups>
                <DBParameterGroup>
                  <ParameterApplyStatus>in-sync</ParameterApplyStatus>
                  <DBParameterGroupName>default.mysql5.1</DBParameterGroupName>
                </DBParameterGroup>
              </DBParameterGroups>
              <DBSecurityGroups>
                <DBSecurityGroup>
                  <Status>active</Status>
                  <DBSecurityGroupName>default</DBSecurityGroupName>
                </DBSecurityGroup>
              </DBSecurityGroups>
              <PreferredBackupWindow>00:00-00:30</PreferredBackupWindow>
              <AutoMinorVersionUpgrade>true</AutoMinorVersionUpgrade>
              <PreferredMaintenanceWindow>sat:07:30-sat:08:00</PreferredMaintenanceWindow>
              <AllocatedStorage>10</AllocatedStorage>
              <DBInstanceClass>db.m1.large</DBInstanceClass>
              <MasterUsername>master</MasterUsername>
            </DBInstance>
          </RestoreDBInstanceToPointInTimeResult>
          <ResponseMetadata>
            <RequestId>1ef546bc-850b-11e0-90aa-eb648410240d</RequestId>
          </ResponseMetadata>
        </RestoreDBInstanceToPointInTimeResponse>
        """

    def test_restore_dbinstance_from_point_in_time(self):
        self.set_http_response(status_code=200)
        db = self.service_connection.restore_dbinstance_from_point_in_time(
            'simcoprod01',
            'restored-db',
            True)

        self.assert_request_parameters({
            'Action': 'RestoreDBInstanceToPointInTime',
            'SourceDBInstanceIdentifier': 'simcoprod01',
            'TargetDBInstanceIdentifier': 'restored-db',
            'UseLatestRestorableTime': 'true',
        }, ignore_params_values=['Version'])

        self.assertEqual(db.id, 'restored-db')
        self.assertEqual(db.engine, 'mysql')
        self.assertEqual(db.status, 'creating')
        self.assertEqual(db.allocated_storage, 10)
        self.assertEqual(db.instance_class, 'db.m1.large')
        self.assertEqual(db.master_username, 'master')
        self.assertEqual(db.multi_az, False)

        self.assertEqual(db.parameter_group.name,
                         'default.mysql5.1')
        self.assertEqual(db.parameter_group.description, None)
        self.assertEqual(db.parameter_group.engine, None)

    def test_restore_dbinstance_from_point_in_time__db_subnet_group_name(self):
        self.set_http_response(status_code=200)
        db = self.service_connection.restore_dbinstance_from_point_in_time(
            'simcoprod01',
            'restored-db',
            True,
            db_subnet_group_name='dbsubnetgroup')

        self.assert_request_parameters({
            'Action': 'RestoreDBInstanceToPointInTime',
            'SourceDBInstanceIdentifier': 'simcoprod01',
            'TargetDBInstanceIdentifier': 'restored-db',
            'UseLatestRestorableTime': 'true',
            'DBSubnetGroupName': 'dbsubnetgroup',
        }, ignore_params_values=['Version'])


class TestRDSOptionGroups(AWSMockServiceTestCase):
    connection_class = RDSConnection

    def setUp(self):
        super(TestRDSOptionGroups, self).setUp()

    def default_body(self):
        return """
        <DescribeOptionGroupsResponse xmlns="http://rds.amazonaws.com/doc/2013-05-15/">
          <DescribeOptionGroupsResult>
            <OptionGroupsList>
              <OptionGroup>
                <MajorEngineVersion>11.2</MajorEngineVersion>
                <OptionGroupName>myoptiongroup</OptionGroupName>
                <EngineName>oracle-se1</EngineName>
                <OptionGroupDescription>Test option group</OptionGroupDescription>
                <Options/>
              </OptionGroup>
              <OptionGroup>
                <MajorEngineVersion>11.2</MajorEngineVersion>
                <OptionGroupName>default:oracle-se1-11-2</OptionGroupName>
                <EngineName>oracle-se1</EngineName>
                <OptionGroupDescription>Default Option Group.</OptionGroupDescription>
                <Options/>
              </OptionGroup>
            </OptionGroupsList>
          </DescribeOptionGroupsResult>
          <ResponseMetadata>
            <RequestId>e4b234d9-84d5-11e1-87a6-71059839a52b</RequestId>
          </ResponseMetadata>
        </DescribeOptionGroupsResponse>
        """

    def test_describe_option_groups(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.describe_option_groups()
        self.assertEqual(len(response), 2)
        options = response[0]
        self.assertEqual(options.name, 'myoptiongroup')
        self.assertEqual(options.description, 'Test option group')
        self.assertEqual(options.engine_name, 'oracle-se1')
        self.assertEqual(options.major_engine_version, '11.2')
        options = response[1]
        self.assertEqual(options.name, 'default:oracle-se1-11-2')
        self.assertEqual(options.description, 'Default Option Group.')
        self.assertEqual(options.engine_name, 'oracle-se1')
        self.assertEqual(options.major_engine_version, '11.2')


class TestRDSOptionGroupOptions(AWSMockServiceTestCase):
    connection_class = RDSConnection

    def setUp(self):
        super(TestRDSOptionGroupOptions, self).setUp()

    def default_body(self):
        return """
        <DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2013-05-15/">
          <DescribeOptionGroupOptionsResult>
            <OptionGroupOptions>
              <OptionGroupOption>
                <MajorEngineVersion>11.2</MajorEngineVersion>
                <PortRequired>true</PortRequired>
                <OptionsDependedOn/>
                <Description>Oracle Enterprise Manager</Description>
                <DefaultPort>1158</DefaultPort>
                <Name>OEM</Name>
                <EngineName>oracle-se1</EngineName>
                <MinimumRequiredMinorEngineVersion>0.2.v3</MinimumRequiredMinorEngineVersion>
                <Persistent>false</Persistent>
                <Permanent>false</Permanent>
              </OptionGroupOption>
            </OptionGroupOptions>
          </DescribeOptionGroupOptionsResult>
          <ResponseMetadata>
            <RequestId>d9c8f6a1-84c7-11e1-a264-0b23c28bc344</RequestId>
          </ResponseMetadata>
        </DescribeOptionGroupOptionsResponse>
        """

    def test_describe_option_group_options(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.describe_option_group_options()
        self.assertEqual(len(response), 1)
        options = response[0]
        self.assertEqual(options.name, 'OEM')
        self.assertEqual(options.description, 'Oracle Enterprise Manager')
        self.assertEqual(options.engine_name, 'oracle-se1')
        self.assertEqual(options.major_engine_version, '11.2')
        self.assertEqual(options.min_minor_engine_version, '0.2.v3')
        self.assertEqual(options.port_required, True)
        self.assertEqual(options.default_port, 1158)
        self.assertEqual(options.permanent, False)
        self.assertEqual(options.persistent, False)
        self.assertEqual(options.depends_on, [])


class TestRDSAddTagsToResource(AWSMockServiceTestCase):
    connection_class = RDSConnection

    def setUp(self):
        super(TestRDSAddTagsToResource, self).setUp()

    def default_body(self):
        return """
        <AddTagsToResourceResponse xmlns="http://rds.amazonaws.com/doc/2012-09-17/">
          <ResponseMetadata>
            <RequestId>ecb24baa-0078-11e3-beb6-359de664aec1</RequestId>
          </ResponseMetadata>
        </AddTagsToResourceResponse>
        """

    def test_add_tags_to_resource(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.add_tags_to_resource('arn:dbinstance',
            {'key1': 'value1', 'key2': 'value2'})
        self.assertTrue(response)
        self.assert_request_parameters({
            'Action': 'AddTagsToResource',
            'ResourceName': 'arn:dbinstance',
            'Tags.member.1.Key': 'key1',
            'Tags.member.1.Value': 'value1',
            'Tags.member.2.Key': 'key2',
            'Tags.member.2.Value': 'value2',
        }, ignore_params_values=['Version'])


class TestRDSRemoveTagsFromResource(AWSMockServiceTestCase):
    connection_class = RDSConnection

    def setUp(self):
        super(TestRDSRemoveTagsFromResource, self).setUp()

    def default_body(self):
        return """
        <RemoveTagsFromResourceResponse xmlns="http://rds.amazonaws.com/doc/2012-09-17/">
          <ResponseMetadata>
            <RequestId>b551e528-007a-11e3-a97a-6b9f172d256a</RequestId>
          </ResponseMetadata>
        </RemoveTagsFromResourceResponse>
        """

    def test_remove_tags_from_resource(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.remove_tags_from_resource('arn:dbinstance',
            ['key1', 'key2'])
        self.assertTrue(response)
        self.assert_request_parameters({
            'Action': 'RemoveTagsFromResource',
            'ResourceName': 'arn:dbinstance',
            'TagKeys.member.1': 'key1',
            'TagKeys.member.2': 'key2',
        }, ignore_params_values=['Version'])


class TestRDSListTagsForResource(AWSMockServiceTestCase):
    connection_class = RDSConnection

    def setUp(self):
        super(TestRDSListTagsForResource, self).setUp()

    def default_body(self):
        return """
        <ListTagsForResourceResponse xmlns="http://rds.amazonaws.com/doc/2012-09-17/">
          <ListTagsForResourceResult>
            <TagList>
              <Tag>
                <Value>value1</Value>
                <Key>key1</Key>
              </Tag>
              <Tag>
                <Value>value2</Value>
                <Key>key2</Key>
              </Tag>
            </TagList>
          </ListTagsForResourceResult>
          <ResponseMetadata>
            <RequestId>58de55b0-007b-11e3-829f-f3097299cddf</RequestId>
          </ResponseMetadata>
        </ListTagsForResourceResponse>
        """

    def test_remove_tags_from_resource(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.list_tags_for_resource('arn:dbinstance')
        self.assert_request_parameters({
            'Action': 'ListTagsForResource',
            'ResourceName': 'arn:dbinstance',
        }, ignore_params_values=['Version'])
        self.assertEqual(len(response), 2)
        self.assertTrue('key1' in response)
        self.assertTrue('key2' in response)
        self.assertEqual(response['key1'], 'value1')
        self.assertEqual(response['key2'], 'value2')


if __name__ == '__main__':
    unittest.main()

