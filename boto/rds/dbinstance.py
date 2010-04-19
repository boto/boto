# Copyright (c) 2006-2009 Mitch Garnaat http://garnaat.org/
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

from boto.rds.dbsecuritygroup import DBSecurityGroup
from boto.rds.parametergroup import ParameterGroup

class DBInstance(object):
    """
    Represents a RDS  DBInstance
    """
    
    def __init__(self, connection=None, id=None):
        self.connection = connection
        self.id = id
        self.create_time = None
        self.engine = None
        self.status = None
        self.allocated_storage = None
        self.endpoint = None
        self.instance_class = None
        self.master_username = None
        self.parameter_group = None
        self.security_group = None
        self.availability_zone = None
        self.backup_retention_period = None
        self.preferred_backup_window = None
        self.preferred_maintenance_window = None
        self.latest_restorable_time = None
        self._in_endpoint = False
        self._port = None
        self._address = None

    def __repr__(self):
        return 'DBInstance:%s' % self.id

    def startElement(self, name, attrs, connection):
        if name == 'Endpoint':
            self._in_endpoint = True
        elif name == 'DBParameterGroup':
            self.parameter_group = ParameterGroup(self.connection)
            return self.parameter_group
        elif name == 'DBSecurityGroup':
            self.security_group = DBSecurityGroup(self.connection)
            return self.security_group
        return None

    def endElement(self, name, value, connection):
        if name == 'DBInstanceIdentifier':
            self.id = value
        elif name == 'DBInstanceStatus':
            self.status = value
        elif name == 'InstanceCreateTime':
            self.create_time = value
        elif name == 'Engine':
            self.engine = value
        elif name == 'DBInstanceStatus':
            self.status = value
        elif name == 'AllocatedStorage':
            self.allocated_storage = int(value)
        elif name == 'DBInstanceClass':
            self.instance_class = value
        elif name == 'MasterUsername':
            self.master_username = value
        elif name == 'Port':
            if self._in_endpoint:
                self._port = int(value)
        elif name == 'Address':
            if self._in_endpoint:
                self._address = value
        elif name == 'Endpoint':
            self.endpoint = (self._address, self._port)
            self._in_endpoint = False
        elif name == 'AvailabilityZone':
            self.availability_zone = value
        elif name == 'BackupRetentionPeriod':
            self.backup_retention_period = value
        elif name == 'LatestRestorableTime':
            self.latest_restorable_time = value
        elif name == 'PreferredMaintenanceWindow':
            self.preferred_maintenance_window = value
        elif name == 'PreferredBackupWindow':
            self.preferred_backup_window = value
        else:
            setattr(self, name, value)

    def snapshot(self, snapshot_id):
        """
        Create a new DB snapshot of this DBInstance.
        
        :type identifier: string
        :param identifier: The identifier for the DBSnapshot
        
        :rtype: :class:`boto.rds.dbsnapshot.DBSnapshot`
        :return: The newly created DBSnapshot
        """
        return self.connection.create_dbsnapshot(snapshot_id, self.id)

    def reboot(self):
        """
        Reboot this DBInstance
        
        :rtype: :class:`boto.rds.dbsnapshot.DBSnapshot`
        :return: The newly created DBSnapshot
        """
        return self.connection.reboot_dbinstance(self.id)

    def stop(self, skip_final_snapshot, final_snapshot_id):
        """
        Delete this DBInstance.

        :type skip_final_snapshot: bool
        :param skip_final_snapshot: This parameter determines whether a final
                                    db snapshot is created before the instance
                                    is deleted.  If True, no snapshot is created.
                                    If False, a snapshot is created before
                                    deleting the instance.

        :type final_snapshot_id: str
        :param final_snapshot_id: If a final snapshot is requested, this
                                  is the identifier used for that snapshot.

        :rtype: :class:`boto.rds.dbinstance.DBInstance`
        :return: The deleted db instance.
        """
        return self.connection.delete_dbinstance(self.id,
                                                 skip_final_snapshot,
                                                 final_snapshot_id)
