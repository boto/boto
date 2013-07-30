# Author: Bruce Pennypacker
#
# Create a temporary RDS database instance, then create a read-replica of the
# instance. Once the replica is available, promote it and verify that the 
# promotion succeeds. Delete the databases upon completion of the tests.
#
# For each step (creating the databases, promoting, etc) we loop for up
# to 15 minutes to wait for the instance to become available.  It should
# never take that long for any of the steps to complete.

"""
Check that promotion of read replicas works as expected
"""

import unittest
import time
from boto.rds import RDSConnection

class PromoteReadReplicaTest(unittest.TestCase):
    rds = True

    def setUp(self):
        self.conn = RDSConnection()
        self.masterDB_name = "boto-db-%s" % str(int(time.time()))
        self.replicaDB_name = "replica-%s" % self.masterDB_name

  
    def tearDown(self):
        if self.replicaDB:
            db = self.conn.delete_dbinstance(self.replicaDB_name, skip_final_snapshot=True)

        if self.masterDB:
            db = self.conn.delete_dbinstance(self.masterDB_name, skip_final_snapshot=True)

    def test_promote(self):
        print '--- running RDS promotion tests ---'
        self.masterDB = self.conn.create_dbinstance(self.masterDB_name, 5, 'db.t1.micro', 'root', 'bototestpw')
        
        # Wait up to 15 minutes for the masterDB to become available
        print '--- waiting for %s to become available  ---' % self.masterDB_name
        wait_timeout = time.time() + (15 * 60)
        time.sleep(10)
 
        instances = self.conn.get_all_dbinstances(self.masterDB_name)
        inst = instances[0]

        while wait_timeout > time.time() and inst.status != 'available':
            time.sleep(5)        
            instances = self.conn.get_all_dbinstances(self.masterDB_name)
            inst = instances[0]

        self.assertTrue(inst.status == 'available')

        self.replicaDB = self.conn.create_dbinstance_read_replica(self.replicaDB_name, self.masterDB_name)

        # Wait up to 15 minutes for the replicaDB to become available
        print '--- waiting for %s to become available  ---' % self.replicaDB_name
        wait_timeout = time.time() + (15 * 60)
        time.sleep(10)
        
        instances = self.conn.get_all_dbinstances(self.replicaDB_name)
        inst = instances[0]

        while wait_timeout > time.time() and inst.status != 'available':
            time.sleep(5)        
            instances = self.conn.get_all_dbinstances(self.replicaDB_name)
            inst = instances[0]

        self.assertTrue(inst.status == 'available')
        
        # Promote the replicaDB and wait for it to become available
        self.replicaDB = self.conn.promote_read_replica(self.replicaDB_name)

        # Wait up to 15 minutes for the replicaDB to become available
        print '--- waiting for %s to be promoted and available  ---' % self.replicaDB_name
        wait_timeout = time.time() + (15 * 60)
        time.sleep(10)
        
        instances = self.conn.get_all_dbinstances(self.replicaDB_name)
        inst = instances[0]

        while wait_timeout > time.time() and inst.status != 'available':
            time.sleep(5)        
            instances = self.conn.get_all_dbinstances(self.replicaDB_name)
            inst = instances[0]

        # Verify that the replica is now a standalone instance and no longer
        # functioning as a read replica
        self.assertTrue(inst)
        self.assertTrue(inst.status == 'available')
        self.assertFalse(inst.status_infos)

        # Verify that the master no longer has any read replicas
        instances = self.conn.get_all_dbinstances(self.masterDB_name)
        inst = instances[0]
        self.assertFalse(inst.read_replica_dbinstance_identifiers)

        print '--- tests completed ---'
