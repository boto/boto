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
        }, ignore_params_values=['AWSAccessKeyId', 'Timestamp', 'Version',
                                 'SignatureVersion', 'SignatureMethod'])
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


if __name__ == '__main__':
    unittest.main()

