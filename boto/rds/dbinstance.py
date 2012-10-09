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
    Represents a RDS DBInstance

    Properties reference available from the AWS documentation at
    http://goo.gl/sC2Kn

    :ivar connection: connection
    :ivar id: The name and identifier of the DBInstance
    :ivar create_time: The date and time of creation
    :ivar engine: The database engine being used
    :ivar status: The status of the database in a string. e.g. "available"
    :ivar allocated_storage: The size of the disk in gigabytes (int).
    :ivar endpoint: A tuple that describes the hostname and port of
        the instance. This is only available when the database is
        in status "available".
    :ivar instance_class: Contains the name of the compute and memory
        capacity class of the DB Instance.
    :ivar master_username: The username that is set as master username
        at creation time.
    :ivar parameter_group: Provides the list of DB Parameter Groups
        applied to this DB Instance.
    :ivar security_group: Provides List of DB Security Group elements
        containing only DBSecurityGroup.Name and DBSecurityGroup.Status
        subelements.
    :ivar availability_zone: Specifies the name of the Availability Zone
        the DB Instance is located in.
    :ivar backup_retention_period: Specifies the number of days for
        which automatic DB Snapshots are retained.
    :ivar preferred_backup_window: Specifies the daily time range during
        which automated backups are created if automated backups are
        enabled, as determined by the backup_retention_period.
    :ivar preferred_maintenance_window: Specifies the weekly time
        range (in UTC) during which system maintenance can occur. (string)
    :ivar latest_restorable_time: Specifies the latest time to which
        a database can be restored with point-in-time restore. TODO: type?
    :ivar multi_az: Boolean that specifies if the DB Instance is a
        Multi-AZ deployment.
    :ivar pending_modified_values: Specifies that changes to the
        DB Instance are pending. This element is only included when changes
        are pending. Specific changes are identified by subelements.
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
        self.multi_az = False
        self.pending_modified_values = None
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
        elif name == 'PendingModifiedValues':
            self.pending_modified_values = PendingModifiedValues()
            return self.pending_modified_values
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
        elif name == 'MultiAZ':
            if value.lower() == 'true':
                self.multi_az = True
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

    def update(self, validate=False):
        """
        Update the DB instance's status information by making a call to fetch
        the current instance attributes from the service.

        :type validate: bool
        :param validate: By default, if EC2 returns no data about the
            instance the update method returns quietly.  If the
            validate param is True, however, it will raise a
            ValueError exception if no data is returned from EC2.
        """
        rs = self.connection.get_all_dbinstances(self.id)
        if len(rs) > 0:
            for i in rs:
                if i.id == self.id:
                    self.__dict__.update(i.__dict__)
        elif validate:
            raise ValueError('%s is not a valid Instance ID' % self.id)
        return self.status

    def stop(self, skip_final_snapshot=False, final_snapshot_id=''):
        """
        Delete this DBInstance.

        :type skip_final_snapshot: bool
        :param skip_final_snapshot: This parameter determines whether
            a final db snapshot is created before the instance is
            deleted.  If True, no snapshot is created.  If False, a
            snapshot is created before deleting the instance.

        :type final_snapshot_id: str
        :param final_snapshot_id: If a final snapshot is requested, this
            is the identifier used for that snapshot.

        :rtype: :class:`boto.rds.dbinstance.DBInstance`
        :return: The deleted db instance.
        """
        return self.connection.delete_dbinstance(self.id,
                                                 skip_final_snapshot,
                                                 final_snapshot_id)

    def modify(self, param_group=None, security_groups=None,
               preferred_maintenance_window=None,
               master_password=None, allocated_storage=None,
               instance_class=None,
               backup_retention_period=None,
               preferred_backup_window=None,
               multi_az=False,
               apply_immediately=False):
        """
        Modify this DBInstance.

        :type security_groups: list of str or list of DBSecurityGroup objects
        :param security_groups: List of names of DBSecurityGroup to
            authorize on this DBInstance.

        :type preferred_maintenance_window: str
        :param preferred_maintenance_window: The weekly time range (in
            UTC) during which maintenance can occur.  Default is
            Sun:05:00-Sun:09:00

        :type master_password: str
        :param master_password: Password of master user for the DBInstance.
            Must be 4-15 alphanumeric characters.

        :type allocated_storage: int
        :param allocated_storage: The new allocated storage size, in GBs.
            Valid values are [5-1024]

        :type instance_class: str
        :param instance_class: The compute and memory capacity of the
            DBInstance.  Changes will be applied at next maintenance
            window unless apply_immediately is True.

            Valid values are:

            * db.m1.small
            * db.m1.large
            * db.m1.xlarge
            * db.m2.xlarge
            * db.m2.2xlarge
            * db.m2.4xlarge

        :type apply_immediately: bool
        :param apply_immediately: If true, the modifications will be
            applied as soon as possible rather than waiting for the
            next preferred maintenance window.

        :type backup_retention_period: int
        :param backup_retention_period: The number of days for which
            automated backups are retained.  Setting this to zero
            disables automated backups.

        :type preferred_backup_window: str
        :param preferred_backup_window: The daily time range during
            which automated backups are created (if enabled).  Must be
            in h24:mi-hh24:mi format (UTC).

        :type multi_az: bool
        :param multi_az: If True, specifies the DB Instance will be
            deployed in multiple availability zones.

        :rtype: :class:`boto.rds.dbinstance.DBInstance`
        :return: The modified db instance.
        """
        return self.connection.modify_dbinstance(self.id,
                                                 param_group,
                                                 security_groups,
                                                 preferred_maintenance_window,
                                                 master_password,
                                                 allocated_storage,
                                                 instance_class,
                                                 backup_retention_period,
                                                 preferred_backup_window,
                                                 multi_az,
                                                 apply_immediately)


class PendingModifiedValues(dict):

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name != 'PendingModifiedValues':
            self[name] = value
