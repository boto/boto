from boto.elasticache.layer1 import ElastiCacheConnection
from tests.compat import mock
from tests.unit import unittest


MOCK_CREATE_CROSS_AZ_MEMCACHED_CLUSTER = b"""{
    "CreateCacheClusterResponse": {
        "CreateCacheClusterResult": {
            "CacheCluster": {
                "CacheClusterId": "boto-test",
                "ReplicationGroupId": null,
                "CacheClusterStatus": "creating",
                "SnapshotRetentionLimit": null,
                "ClientDownloadLandingPage": "https://console.aws.amazon.com/elasticache/home#client-download:",
                "PendingModifiedValues": {
                    "NumCacheNodes": null,
                    "EngineVersion": null,
                    "CacheNodeIdsToRemove": null
                },
                "Engine": "memcached",
                "CacheSecurityGroups": [],
                "NumCacheNodes": 3,
                "AutoMinorVersionUpgrade": true,
                "SecurityGroups": null,
                "CacheNodeType": "cache.t1.micro",
                "PreferredMaintenanceWindow": "thu:03:30-thu:04:30",
                "CacheSubnetGroupName": "subnet-cross-az",
                "EngineVersion": "1.4.14",
                "CacheNodes": null,
                "ConfigurationEndpoint": null,
                "CacheClusterCreateTime": null,
                "PreferredAvailabilityZone": "Multiple",
                "SnapshotWindow": null,
                "NotificationConfiguration": null,
                "CacheParameterGroup": {
                    "CacheNodeIdsToReboot": [],
                    "CacheParameterGroupName": "default.memcached1.4",
                    "ParameterApplyStatus": "in-sync"
                }
            }
        },
        "ResponseMetadata": {
            "RequestId": "e64feaa5-2871-11e4-99b6-51f400a84b74"
        }
    }
}
"""

MOCK_DESCRIBE_CROSS_AZ_MEMCACHED_CLUSTER = b"""{
    "DescribeCacheClustersResponse": {
        "DescribeCacheClustersResult": {
            "CacheClusters": [{
                "AutoMinorVersionUpgrade": true,
                "CacheClusterCreateTime": 1.408543382879E9,
                "CacheClusterId": "boto-test",
                "CacheClusterStatus": "available",
                "CacheNodeType": "cache.t1.micro",
                "CacheNodes": [{
                    "CacheNodeCreateTime": 1.408543382879E9,
                    "CacheNodeId": "0001",
                    "CacheNodeStatus": "available",
                    "CustomerAvailabilityZone": "us-west-2a",
                    "Endpoint": {
                        "Address": "boto-test.fwbzkf.0001.usw2.cache.amazonaws.com",
                        "Port": 11211
                    },
                    "ParameterGroupStatus": "in-sync",
                    "SourceCacheNodeId": null
                }, {
                    "CacheNodeCreateTime": 1.408543382879E9,
                    "CacheNodeId": "0002",
                    "CacheNodeStatus": "available",
                    "CustomerAvailabilityZone": "us-west-2b",
                    "Endpoint": {
                        "Address": "boto-test.fwbzkf.0002.usw2.cache.amazonaws.com",
                        "Port": 11211
                    },
                    "ParameterGroupStatus": "in-sync",
                    "SourceCacheNodeId": null
                }, {
                    "CacheNodeCreateTime": 1.408543382879E9,
                    "CacheNodeId": "0003",
                    "CacheNodeStatus": "available",
                    "CustomerAvailabilityZone": "us-west-2c",
                    "Endpoint": {
                        "Address": "boto-test.fwbzkf.0003.usw2.cache.amazonaws.com",
                        "Port": 11211
                    },
                    "ParameterGroupStatus": "in-sync",
                    "SourceCacheNodeId": null
                }],
                "CacheParameterGroup": {
                    "CacheNodeIdsToReboot": [],
                    "CacheParameterGroupName": "default.memcached1.4",
                    "ParameterApplyStatus": "in-sync"
                },
                "CacheSecurityGroups": [],
                "CacheSubnetGroupName": "subnet-cross-az",
                "ClientDownloadLandingPage": "https://console.aws.amazon.com/elasticache/home#client-download:",
                "ConfigurationEndpoint": {
                    "Address": "boto-test.fwbzkf.cfg.usw2.cache.amazonaws.com",
                    "Port": 11211
                },
                "Engine": "memcached",
                "EngineVersion": "1.4.14",
                "NotificationConfiguration": null,
                "NumCacheNodes": 3,
                "PendingModifiedValues": {
                    "CacheNodeIdsToRemove": null,
                    "EngineVersion": null,
                    "NumCacheNodes": null
                },
                "PreferredAvailabilityZone": "Multiple",
                "PreferredMaintenanceWindow": "thu:03:30-thu:04:30",
                "ReplicationGroupId": null,
                "SecurityGroups": null,
                "SnapshotRetentionLimit": null,
                "SnapshotWindow": null
            }],
            "Marker": null
        },
        "ResponseMetadata": {
            "RequestId": "a6a54156-2875-11e4-b426-ff0bf83e250f"
        }
    }
}
"""

class TestCreateCrossAZCacheCluster(unittest.TestCase):
    def test_create_cross_az_cache_cluster(self):
        connection = ElastiCacheConnection(aws_access_key_id='aws_access_key_id',
                                           aws_secret_access_key='aws_secret_access_key')

        mock_create_response = mock.Mock()
        mock_create_response.read.return_value = MOCK_CREATE_CROSS_AZ_MEMCACHED_CLUSTER
        mock_create_response.status = 200
        connection.make_request = mock.Mock(return_value=mock_create_response)
        response = connection.create_cache_cluster(
            cache_cluster_id='boto-test',
            num_cache_nodes=3,
            cache_node_type='cache.t1.micro',
            engine='memcached',
            engine_version='1.4.14',
            port=11211,
            cache_subnet_group_name='subnet-cross-az',
            auto_minor_version_upgrade=True,
            az_mode='cross-az',
            preferred_availability_zones=['us-west-2a','us-west-2b','us-west-2c'])
        cluster = response['CreateCacheClusterResponse']['CreateCacheClusterResult']['CacheCluster']
        self.assertEqual(cluster['CacheClusterId'], 'boto-test')
        self.assertEqual(cluster['CacheClusterStatus'], 'creating')
        self.assertEqual(cluster['CacheSubnetGroupName'], 'subnet-cross-az')
        # test zone is multiple
        self.assertEqual(cluster['PreferredAvailabilityZone'], 'Multiple')

        mock_describe_response = mock.Mock()
        mock_describe_response.read.return_value = MOCK_DESCRIBE_CROSS_AZ_MEMCACHED_CLUSTER
        mock_describe_response.status = 200
        connection.make_request = mock.Mock(return_value=mock_describe_response)
        response = connection.describe_cache_clusters(cache_cluster_id='boto-test',
                                                     show_cache_node_info=True)
        clusters = response['DescribeCacheClustersResponse']['DescribeCacheClustersResult']['CacheClusters']
        self.assertEqual(len(clusters), 1)
        cluster = clusters[0]
        self.assertEqual(cluster['CacheClusterId'], 'boto-test')
        self.assertEqual(cluster['CacheSubnetGroupName'], 'subnet-cross-az')
        # test zone is multiple
        self.assertEqual(cluster['PreferredAvailabilityZone'], 'Multiple')
        # test nodes are spreaded across zones
        self.assertEqual(len(cluster['CacheNodes']), 3)
        node_zones = [node['CustomerAvailabilityZone'] for node in cluster['CacheNodes']]
        self.assertTrue('us-west-2a' in node_zones)
        self.assertTrue('us-west-2b' in node_zones)
        self.assertTrue('us-west-2c' in node_zones)
