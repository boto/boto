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

from boto.rds import *


class TestInstanceRename(AWSMockServiceTestCase):
    connection_class = RDSConnection

    def setUp(self):
        super(TestInstanceRename, self).setUp()

    def default_body(self):
        return """
        <ModifyDBInstanceResponse xmlns="http://rds.amazonaws.com/doc/2013-05-15/">
          <ModifyDBInstanceResult>
            <DBInstance>
              <ReadReplicaDBInstanceIdentifiers/>
              <LatestRestorableTime>2011-05-23T08:00:00Z</LatestRestorableTime>
              <Engine>mysql</Engine>
              <PendingModifiedValues>
                <AllocatedStorage>50</AllocatedStorage>
              </PendingModifiedValues>
              <BackupRetentionPeriod>1</BackupRetentionPeriod>
              <MultiAZ>false</MultiAZ>
              <LicenseModel>general-public-license</LicenseModel>
              <DBInstanceStatus>available</DBInstanceStatus>
              <EngineVersion>5.1.50</EngineVersion>
              <Endpoint>
                <Port>3306</Port>
                <Address>simcoprod01.cu7u2t4uz396.us-east-1.rds.amazonaws.com</Address>
              </Endpoint>
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
              <AvailabilityZone>us-east-1a</AvailabilityZone>
              <InstanceCreateTime>2011-05-23T06:06:43.110Z</InstanceCreateTime>
              <AllocatedStorage>10</AllocatedStorage>
              <DBInstanceClass>db.m1.large</DBInstanceClass>
              <MasterUsername>master</MasterUsername>
            </DBInstance>
          </ModifyDBInstanceResult>
        </ModifyDBInstanceResponse>
        """

    def test_modify_db_instance(self):
        self.set_http_response(status_code=200)
        response = self.service_connection.modify_dbinstance(
            id='simcoprod01',
            new_id='simcoprod01',
        )
        self.assert_request_parameters({
            'Action': 'ModifyDBInstance',
            'DBInstanceIdentifier': 'simcoprod01',
            'NewDBInstanceIdentifier': 'simcoprod01',
        }, ignore_params_values=['AWSAccessKeyId', 'Timestamp', 'Version',
                                 'SignatureVersion', 'SignatureMethod'])
        db = response
        self.assertEqual(db.id, 'simcoprod01')

if __name__ == '__main__':
    unittest.main()

