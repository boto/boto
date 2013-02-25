# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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


import boto
from boto.compat import json
from boto.connection import AWSQueryConnection
from boto.regioninfo import RegionInfo


class ElastiCacheConnection(AWSQueryConnection):
    """
    Amazon ElastiCache
    Amazon ElastiCache is a web service that makes it easier to set
    up, operate, and scale a distributed cache in the cloud.

    With Amazon ElastiCache, customers gain all of the benefits of a
    high-performance, in-memory cache with far less of the
    administrative burden of launching and managing a distributed
    cache. The service makes set-up, scaling, and cluster failure
    handling much simpler than in a self-managed cache deployment.

    In addition, through integration with Amazon CloudWatch, customers
    get enhanced visibility into the key performance statistics
    associated with their cache and can receive alarms if a part of
    their cache runs hot.
    """
    APIVersion = "2012-11-15"
    DefaultRegionName = "us-east-1"
    DefaultRegionEndpoint = "elasticache.us-east-1.amazonaws.com"

    def __init__(self, **kwargs):
        region = kwargs.get('region')
        if not region:
            region = RegionInfo(self, self.DefaultRegionName,
                                self.DefaultRegionEndpoint)
        else:
            del kwargs['region']
        kwargs['host'] = region.endpoint
        AWSQueryConnection.__init__(self, **kwargs)
        self.region = region


    def _required_auth_capability(self):
        return ['sign-v2']

    def authorize_cache_security_group_ingress(self,
                                               cache_security_group_name,
                                               ec2_security_group_name,
                                               ec2_security_group_owner_id):
        """
        Authorizes ingress to a CacheSecurityGroup using EC2 Security
        Groups as authorization (therefore the application using the
        cache must be running on EC2 clusters). This API requires the
        following parameters: EC2SecurityGroupName and
        EC2SecurityGroupOwnerId.
        You cannot authorize ingress from an EC2 security group in one
        Region to an Amazon Cache Cluster in another.

        :type cache_security_group_name: string
        :param cache_security_group_name: The name of the Cache Security Group
            to authorize.

        :type ec2_security_group_name: string
        :param ec2_security_group_name: Name of the EC2 Security Group to
            include in the authorization.

        :type ec2_security_group_owner_id: string
        :param ec2_security_group_owner_id: AWS Account Number of the owner of
            the security group specified in the EC2SecurityGroupName parameter.
            The AWS Access Key ID is not an acceptable value.

        """
        params = {
            'CacheSecurityGroupName': cache_security_group_name,
            'EC2SecurityGroupName': ec2_security_group_name,
            'EC2SecurityGroupOwnerId': ec2_security_group_owner_id,
        }
        return self._make_request(
            action='AuthorizeCacheSecurityGroupIngress',
            verb='POST',
            path='/', params=params)

    def create_cache_cluster(self, cache_cluster_id, num_cache_nodes,
                             cache_node_type, engine, engine_version=None,
                             cache_parameter_group_name=None,
                             cache_subnet_group_name=None,
                             cache_security_group_names=None,
                             security_group_ids=None,
                             preferred_availability_zone=None,
                             preferred_maintenance_window=None, port=None,
                             notification_topic_arn=None,
                             auto_minor_version_upgrade=None):
        """
        Creates a new Cache Cluster.

        :type cache_cluster_id: string
        :param cache_cluster_id: The Cache Cluster identifier. This parameter
            is stored as a lowercase string.

        :type num_cache_nodes: integer
        :param num_cache_nodes: The number of Cache Nodes the Cache Cluster
            should have.

        :type cache_node_type: string
        :param cache_node_type: The compute and memory capacity of nodes in a
            Cache Cluster.

        :type engine: string
        :param engine: The name of the cache engine to be used for this Cache
            Cluster.  Currently, memcached is the only cache engine supported
            by the service.

        :type engine_version: string
        :param engine_version: The version of the cache engine to be used for
            this cluster.

        :type cache_parameter_group_name: string
        :param cache_parameter_group_name: The name of the cache parameter
            group to associate with this Cache cluster. If this argument is
            omitted, the default CacheParameterGroup for the specified engine
            will be used.

        :type cache_subnet_group_name: string
        :param cache_subnet_group_name: The name of the Cache Subnet Group to
            be used for the Cache Cluster.  Use this parameter only when you
            are creating a cluster in an Amazon Virtual Private Cloud (VPC).

        :type cache_security_group_names: list
        :param cache_security_group_names: A list of Cache Security Group Names
            to associate with this Cache Cluster.  Use this parameter only when
            you are creating a cluster outside of an Amazon Virtual Private
            Cloud (VPC).

        :type security_group_ids: list
        :param security_group_ids: Specifies the VPC Security Groups associated
            with the Cache Cluster.  Use this parameter only when you are
            creating a cluster in an Amazon Virtual Private Cloud (VPC).

        :type preferred_availability_zone: string
        :param preferred_availability_zone: The EC2 Availability Zone that the
            Cache Cluster will be created in.  All cache nodes belonging to a
            cache cluster are placed in the preferred availability zone.
            Default: System chosen (random) availability zone.

        :type preferred_maintenance_window: string
        :param preferred_maintenance_window: The weekly time range (in UTC)
            during which system maintenance can occur.  Example:
            `sun:05:00-sun:09:00`

        :type port: integer
        :param port: The port number on which each of the Cache Nodes will
            accept connections.

        :type notification_topic_arn: string
        :param notification_topic_arn: The Amazon Resource Name (ARN) of the
            Amazon Simple Notification Service (SNS) topic to which
            notifications will be sent.  The Amazon SNS topic owner must be the
            same as the Cache Cluster owner.

        :type auto_minor_version_upgrade: boolean
        :param auto_minor_version_upgrade: Indicates that minor engine upgrades
            will be applied automatically to the Cache Cluster during the
            maintenance window.  Default: `True`

        """
        params = {
            'CacheClusterId': cache_cluster_id,
            'NumCacheNodes': num_cache_nodes,
            'CacheNodeType': cache_node_type,
            'Engine': engine,
        }
        if engine_version is not None:
            params['EngineVersion'] = engine_version
        if cache_parameter_group_name is not None:
            params['CacheParameterGroupName'] = cache_parameter_group_name
        if cache_subnet_group_name is not None:
            params['CacheSubnetGroupName'] = cache_subnet_group_name
        if cache_security_group_names is not None:
            self.build_list_params(params,
                                   cache_security_group_names,
                                   'CacheSecurityGroupNames.member')
        if security_group_ids is not None:
            self.build_list_params(params,
                                   security_group_ids,
                                   'SecurityGroupIds.member')
        if preferred_availability_zone is not None:
            params['PreferredAvailabilityZone'] = preferred_availability_zone
        if preferred_maintenance_window is not None:
            params['PreferredMaintenanceWindow'] = preferred_maintenance_window
        if port is not None:
            params['Port'] = port
        if notification_topic_arn is not None:
            params['NotificationTopicArn'] = notification_topic_arn
        if auto_minor_version_upgrade is not None:
            params['AutoMinorVersionUpgrade'] = str(
                auto_minor_version_upgrade).lower()
        return self._make_request(
            action='CreateCacheCluster',
            verb='POST',
            path='/', params=params)

    def create_cache_parameter_group(self, cache_parameter_group_name,
                                     cache_parameter_group_family,
                                     description):
        """
        Creates a new Cache Parameter Group. Cache Parameter groups
        control the parameters for a Cache Cluster.

        :type cache_parameter_group_name: string
        :param cache_parameter_group_name: The name of the Cache Parameter
            Group.

        :type cache_parameter_group_family: string
        :param cache_parameter_group_family: The name of the Cache Parameter
            Group Family the Cache Parameter Group can be used with.
            Currently, memcached1.4 is the only cache parameter group family
            supported by the service.

        :type description: string
        :param description: The description for the Cache Parameter Group.

        """
        params = {
            'CacheParameterGroupName': cache_parameter_group_name,
            'CacheParameterGroupFamily': cache_parameter_group_family,
            'Description': description,
        }
        return self._make_request(
            action='CreateCacheParameterGroup',
            verb='POST',
            path='/', params=params)

    def create_cache_security_group(self, cache_security_group_name,
                                    description):
        """
        Creates a new Cache Security Group. Cache Security groups
        control access to one or more Cache Clusters.

        Only use cache security groups when you are creating a cluster
        outside of an Amazon Virtual Private Cloud (VPC). Inside of a
        VPC, use VPC security groups.

        :type cache_security_group_name: string
        :param cache_security_group_name: The name for the Cache Security
            Group. This value is stored as a lowercase string.  Constraints:
            Must contain no more than 255 alphanumeric characters. Must not be
            "Default".  Example: `mysecuritygroup`

        :type description: string
        :param description: The description for the Cache Security Group.

        """
        params = {
            'CacheSecurityGroupName': cache_security_group_name,
            'Description': description,
        }
        return self._make_request(
            action='CreateCacheSecurityGroup',
            verb='POST',
            path='/', params=params)

    def create_cache_subnet_group(self, cache_subnet_group_name,
                                  cache_subnet_group_description, subnet_ids):
        """
        Creates a new Cache Subnet Group.

        :type cache_subnet_group_name: string
        :param cache_subnet_group_name: The name for the Cache Subnet Group.
            This value is stored as a lowercase string.  Constraints: Must
            contain no more than 255 alphanumeric characters or hyphens.
            Example: `mysubnetgroup`

        :type cache_subnet_group_description: string
        :param cache_subnet_group_description: The description for the Cache
            Subnet Group.

        :type subnet_ids: list
        :param subnet_ids: The EC2 Subnet IDs for the Cache Subnet Group.

        """
        params = {
            'CacheSubnetGroupName': cache_subnet_group_name,
            'CacheSubnetGroupDescription': cache_subnet_group_description,
        }
        self.build_list_params(params,
                               subnet_ids,
                               'SubnetIds.member')
        return self._make_request(
            action='CreateCacheSubnetGroup',
            verb='POST',
            path='/', params=params)

    def delete_cache_cluster(self, cache_cluster_id):
        """
        Deletes a previously provisioned Cache Cluster. A successful
        response from the web service indicates the request was
        received correctly. This action cannot be canceled or
        reverted. DeleteCacheCluster deletes all associated Cache
        Nodes, node endpoints and the Cache Cluster itself.

        :type cache_cluster_id: string
        :param cache_cluster_id: The Cache Cluster identifier for the Cache
            Cluster to be deleted. This parameter isn't case sensitive.

        """
        params = {'CacheClusterId': cache_cluster_id, }
        return self._make_request(
            action='DeleteCacheCluster',
            verb='POST',
            path='/', params=params)

    def delete_cache_parameter_group(self, cache_parameter_group_name):
        """
        Deletes the specified CacheParameterGroup. The
        CacheParameterGroup cannot be deleted if it is associated with
        any cache clusters.

        :type cache_parameter_group_name: string
        :param cache_parameter_group_name: The name of the Cache Parameter
            Group to delete.  The specified cache security group must not be
            associated with any Cache clusters.

        """
        params = {
            'CacheParameterGroupName': cache_parameter_group_name,
        }
        return self._make_request(
            action='DeleteCacheParameterGroup',
            verb='POST',
            path='/', params=params)

    def delete_cache_security_group(self, cache_security_group_name):
        """
        Deletes a Cache Security Group.
        The specified Cache Security Group must not be associated with
        any Cache Clusters.

        :type cache_security_group_name: string
        :param cache_security_group_name: The name of the Cache Security Group
            to delete.  You cannot delete the default security group.

        """
        params = {
            'CacheSecurityGroupName': cache_security_group_name,
        }
        return self._make_request(
            action='DeleteCacheSecurityGroup',
            verb='POST',
            path='/', params=params)

    def delete_cache_subnet_group(self, cache_subnet_group_name):
        """
        Deletes a Cache Subnet Group.
        The specified Cache Subnet Group must not be associated with
        any Cache Clusters.

        :type cache_subnet_group_name: string
        :param cache_subnet_group_name: The name of the Cache Subnet Group to
            delete.  Constraints: Must contain no more than 255 alphanumeric
            characters or hyphens.

        """
        params = {'CacheSubnetGroupName': cache_subnet_group_name, }
        return self._make_request(
            action='DeleteCacheSubnetGroup',
            verb='POST',
            path='/', params=params)

    def describe_cache_clusters(self, cache_cluster_id=None,
                                max_records=None, marker=None,
                                show_cache_node_info=None):
        """
        Returns information about all provisioned Cache Clusters if no
        Cache Cluster identifier is specified, or about a specific
        Cache Cluster if a Cache Cluster identifier is supplied.

        Cluster information will be returned by default. An optional
        ShowDetails flag can be used to retrieve detailed information
        about the Cache Nodes associated with the Cache Cluster.
        Details include the DNS address and port for the Cache Node
        endpoint.

        If the cluster is in the CREATING state, only cluster level
        information will be displayed until all of the nodes are
        successfully provisioned.

        If the cluster is in the DELETING state, only cluster level
        information will be displayed.

        While adding Cache Nodes, node endpoint information and
        creation time for the additional nodes will not be displayed
        until they are completely provisioned. The cluster lifecycle
        tells the customer when new nodes are AVAILABLE.

        While removing existing Cache Nodes from an cluster, endpoint
        information for the removed nodes will not be displayed.

        DescribeCacheClusters supports pagination.

        :type cache_cluster_id: string
        :param cache_cluster_id: The user-supplied cluster identifier. If this
            parameter is specified, only information about that specific Cache
            Cluster is returned. This parameter isn't case sensitive.

        :type max_records: integer
        :param max_records: The maximum number of records to include in the
            response. If more records exist than the specified MaxRecords
            value, a marker is included in the response so that the remaining
            results may be retrieved.

        :type marker: string
        :param marker: An optional marker provided in the previous
            DescribeCacheClusters request. If this parameter is specified, the
            response includes only records beyond the marker, up to the value
            specified by MaxRecords .

        :type show_cache_node_info: boolean
        :param show_cache_node_info: An optional flag that can be included in
            the DescribeCacheCluster request to retrieve Cache Nodes
            information.

        """
        params = {}
        if cache_cluster_id is not None:
            params['CacheClusterId'] = cache_cluster_id
        if max_records is not None:
            params['MaxRecords'] = max_records
        if marker is not None:
            params['Marker'] = marker
        if show_cache_node_info is not None:
            params['ShowCacheNodeInfo'] = str(
                show_cache_node_info).lower()
        return self._make_request(
            action='DescribeCacheClusters',
            verb='POST',
            path='/', params=params)

    def describe_cache_engine_versions(self, engine=None,
                                       engine_version=None,
                                       cache_parameter_group_family=None,
                                       max_records=None, marker=None,
                                       default_only=None):
        """
        Returns a list of the available cache engines and their
        versions.

        :type engine: string
        :param engine: The cache engine to return.

        :type engine_version: string
        :param engine_version: The cache engine version to return.  Example:
            `1.4.14`

        :type cache_parameter_group_family: string
        :param cache_parameter_group_family: The name of a specific Cache
            Parameter Group family to return details for.  Constraints:   +
            Must be 1 to 255 alphanumeric characters + First character must be
            a letter + Cannot end with a hyphen or contain two consecutive
            hyphens

        :type max_records: integer
        :param max_records: The maximum number of records to include in the
            response. If more records exist than the specified MaxRecords
            value, a marker is included in the response so that the remaining
            results may be retrieved.

        :type marker: string
        :param marker: An optional marker provided in the previous
            DescribeCacheParameterGroups request. If this parameter is
            specified, the response includes only records beyond the marker, up
            to the value specified by MaxRecords .

        :type default_only: boolean
        :param default_only: Indicates that only the default version of the
            specified engine or engine and major version combination is
            returned.

        """
        params = {}
        if engine is not None:
            params['Engine'] = engine
        if engine_version is not None:
            params['EngineVersion'] = engine_version
        if cache_parameter_group_family is not None:
            params['CacheParameterGroupFamily'] = cache_parameter_group_family
        if max_records is not None:
            params['MaxRecords'] = max_records
        if marker is not None:
            params['Marker'] = marker
        if default_only is not None:
            params['DefaultOnly'] = str(
                default_only).lower()
        return self._make_request(
            action='DescribeCacheEngineVersions',
            verb='POST',
            path='/', params=params)

    def describe_cache_parameter_groups(self,
                                        cache_parameter_group_name=None,
                                        max_records=None, marker=None):
        """
        Returns a list of CacheParameterGroup descriptions. If a
        CacheParameterGroupName is specified, the list will contain
        only the descriptions of the specified CacheParameterGroup.

        :type cache_parameter_group_name: string
        :param cache_parameter_group_name: The name of a specific cache
            parameter group to return details for.

        :type max_records: integer
        :param max_records: The maximum number of records to include in the
            response. If more records exist than the specified MaxRecords
            value, a marker is included in the response so that the remaining
            results may be retrieved.

        :type marker: string
        :param marker: An optional marker provided in the previous
            DescribeCacheParameterGroups request. If this parameter is
            specified, the response includes only records beyond the marker, up
            to the value specified by MaxRecords .

        """
        params = {}
        if cache_parameter_group_name is not None:
            params['CacheParameterGroupName'] = cache_parameter_group_name
        if max_records is not None:
            params['MaxRecords'] = max_records
        if marker is not None:
            params['Marker'] = marker
        return self._make_request(
            action='DescribeCacheParameterGroups',
            verb='POST',
            path='/', params=params)

    def describe_cache_parameters(self, cache_parameter_group_name,
                                  source=None, max_records=None, marker=None):
        """
        Returns the detailed parameter list for a particular
        CacheParameterGroup.

        :type cache_parameter_group_name: string
        :param cache_parameter_group_name: The name of a specific cache
            parameter group to return details for.

        :type source: string
        :param source: The parameter types to return.  Valid values: `user` |
            `system` | `engine-default`

        :type max_records: integer
        :param max_records: The maximum number of records to include in the
            response. If more records exist than the specified MaxRecords
            value, a marker is included in the response so that the remaining
            results may be retrieved.

        :type marker: string
        :param marker: An optional marker provided in the previous
            DescribeCacheClusters request. If this parameter is specified, the
            response includes only records beyond the marker, up to the value
            specified by MaxRecords .

        """
        params = {
            'CacheParameterGroupName': cache_parameter_group_name,
        }
        if source is not None:
            params['Source'] = source
        if max_records is not None:
            params['MaxRecords'] = max_records
        if marker is not None:
            params['Marker'] = marker
        return self._make_request(
            action='DescribeCacheParameters',
            verb='POST',
            path='/', params=params)

    def describe_cache_security_groups(self, cache_security_group_name=None,
                                       max_records=None, marker=None):
        """
        Returns a list of CacheSecurityGroup descriptions. If a
        CacheSecurityGroupName is specified, the list will contain
        only the description of the specified CacheSecurityGroup.

        :type cache_security_group_name: string
        :param cache_security_group_name: The name of the Cache Security Group
            to return details for.

        :type max_records: integer
        :param max_records: The maximum number of records to include in the
            response. If more records exist than the specified MaxRecords
            value, a marker is included in the response so that the remaining
            results may be retrieved.

        :type marker: string
        :param marker: An optional marker provided in the previous
            DescribeCacheClusters request. If this parameter is specified, the
            response includes only records beyond the marker, up to the value
            specified by MaxRecords .

        """
        params = {}
        if cache_security_group_name is not None:
            params['CacheSecurityGroupName'] = cache_security_group_name
        if max_records is not None:
            params['MaxRecords'] = max_records
        if marker is not None:
            params['Marker'] = marker
        return self._make_request(
            action='DescribeCacheSecurityGroups',
            verb='POST',
            path='/', params=params)

    def describe_cache_subnet_groups(self, cache_subnet_group_name=None,
                                     max_records=None, marker=None):
        """
        Returns a list of CacheSubnetGroup descriptions. If a
        CacheSubnetGroupName is specified, the list will contain only
        the description of the specified Cache Subnet Group.

        :type cache_subnet_group_name: string
        :param cache_subnet_group_name: The name of the Cache Subnet Group to
            return details for.

        :type max_records: integer
        :param max_records: The maximum number of records to include in the
            response. If more records exist than the specified `MaxRecords`
            value, a marker is included in the response so that the remaining
            results may be retrieved.  Default: 100  Constraints: minimum 20,
            maximum 100

        :type marker: string
        :param marker: An optional marker provided in the previous
            DescribeCacheSubnetGroups request. If this parameter is specified,
            the response includes only records beyond the marker, up to the
            value specified by `MaxRecords`.

        """
        params = {}
        if cache_subnet_group_name is not None:
            params['CacheSubnetGroupName'] = cache_subnet_group_name
        if max_records is not None:
            params['MaxRecords'] = max_records
        if marker is not None:
            params['Marker'] = marker
        return self._make_request(
            action='DescribeCacheSubnetGroups',
            verb='POST',
            path='/', params=params)

    def describe_engine_default_parameters(self,
                                           cache_parameter_group_family,
                                           max_records=None, marker=None):
        """
        Returns the default engine and system parameter information
        for the specified cache engine.

        :type cache_parameter_group_family: string
        :param cache_parameter_group_family: The name of the Cache Parameter
            Group Family.  Currently, memcached1.4 is the only cache parameter
            group family supported by the service.

        :type max_records: integer
        :param max_records: The maximum number of records to include in the
            response. If more records exist than the specified MaxRecords
            value, a marker is included in the response so that the remaining
            results may be retrieved.

        :type marker: string
        :param marker: An optional marker provided in the previous
            DescribeCacheClusters request. If this parameter is specified, the
            response includes only records beyond the marker, up to the value
            specified by MaxRecords .

        """
        params = {
            'CacheParameterGroupFamily': cache_parameter_group_family,
        }
        if max_records is not None:
            params['MaxRecords'] = max_records
        if marker is not None:
            params['Marker'] = marker
        return self._make_request(
            action='DescribeEngineDefaultParameters',
            verb='POST',
            path='/', params=params)

    def describe_events(self, source_identifier=None, source_type=None,
                        start_time=None, end_time=None, duration=None,
                        max_records=None, marker=None):
        """
        Returns events related to Cache Clusters, Cache Security
        Groups, and Cache Parameter Groups for the past 14 days.
        Events specific to a particular Cache Cluster, Cache Security
        Group, or Cache Parameter Group can be obtained by providing
        the name as a parameter. By default, the past hour of events
        are returned.

        :type source_identifier: string
        :param source_identifier: The identifier of the event source for which
            events will be returned. If not specified, then all sources are
            included in the response.

        :type source_type: string
        :param source_type: The event source to retrieve events for. If no
            value is specified, all events are returned.

        :type start_time: string
        :param start_time: The beginning of the time interval to retrieve
            events for, specified in ISO 8601 format.

        :type end_time: string
        :param end_time: The end of the time interval for which to retrieve
            events, specified in ISO 8601 format.

        :type duration: integer
        :param duration: The number of minutes to retrieve events for.

        :type max_records: integer
        :param max_records: The maximum number of records to include in the
            response. If more records exist than the specified MaxRecords
            value, a marker is included in the response so that the remaining
            results may be retrieved.

        :type marker: string
        :param marker: An optional marker provided in the previous
            DescribeCacheClusters request. If this parameter is specified, the
            response includes only records beyond the marker, up to the value
            specified by MaxRecords .

        """
        params = {}
        if source_identifier is not None:
            params['SourceIdentifier'] = source_identifier
        if source_type is not None:
            params['SourceType'] = source_type
        if start_time is not None:
            params['StartTime'] = start_time
        if end_time is not None:
            params['EndTime'] = end_time
        if duration is not None:
            params['Duration'] = duration
        if max_records is not None:
            params['MaxRecords'] = max_records
        if marker is not None:
            params['Marker'] = marker
        return self._make_request(
            action='DescribeEvents',
            verb='POST',
            path='/', params=params)

    def describe_reserved_cache_nodes(self, reserved_cache_node_id=None,
                                      reserved_cache_nodes_offering_id=None,
                                      cache_node_type=None, duration=None,
                                      product_description=None,
                                      offering_type=None, max_records=None,
                                      marker=None):
        """
        Returns information about reserved Cache Nodes for this
        account, or about a specified reserved Cache Node.

        :type reserved_cache_node_id: string
        :param reserved_cache_node_id: The reserved Cache Node identifier
            filter value. Specify this parameter to show only the reservation
            that matches the specified reservation ID.

        :type reserved_cache_nodes_offering_id: string
        :param reserved_cache_nodes_offering_id: The offering identifier filter
            value. Specify this parameter to show only purchased reservations
            matching the specified offering identifier.

        :type cache_node_type: string
        :param cache_node_type: The Cache Node type filter value. Specify this
            parameter to show only those reservations matching the specified
            Cache Nodes type.

        :type duration: string
        :param duration: The duration filter value, specified in years or
            seconds. Specify this parameter to show only reservations for this
            duration.  Valid Values: `1 | 3 | 31536000 | 94608000`

        :type product_description: string
        :param product_description: The product description filter value.
            Specify this parameter to show only those reservations matching the
            specified product description.

        :type offering_type: string
        :param offering_type: The offering type filter value. Specify this
            parameter to show only the available offerings matching the
            specified offering type.  Valid Values: `"Light Utilization" |
            "Medium Utilization" | "Heavy Utilization"`

        :type max_records: integer
        :param max_records: The maximum number of records to include in the
            response. If more than the `MaxRecords` value is available, a
            marker is included in the response so that the following results
            can be retrieved.  Default: 100  Constraints: minimum 20, maximum
            100

        :type marker: string
        :param marker: The marker provided in the previous request. If this
            parameter is specified, the response includes records beyond the
            marker only, up to `MaxRecords`.

        """
        params = {}
        if reserved_cache_node_id is not None:
            params['ReservedCacheNodeId'] = reserved_cache_node_id
        if reserved_cache_nodes_offering_id is not None:
            params['ReservedCacheNodesOfferingId'] = reserved_cache_nodes_offering_id
        if cache_node_type is not None:
            params['CacheNodeType'] = cache_node_type
        if duration is not None:
            params['Duration'] = duration
        if product_description is not None:
            params['ProductDescription'] = product_description
        if offering_type is not None:
            params['OfferingType'] = offering_type
        if max_records is not None:
            params['MaxRecords'] = max_records
        if marker is not None:
            params['Marker'] = marker
        return self._make_request(
            action='DescribeReservedCacheNodes',
            verb='POST',
            path='/', params=params)

    def describe_reserved_cache_nodes_offerings(self,
                                                reserved_cache_nodes_offering_id=None,
                                                cache_node_type=None,
                                                duration=None,
                                                product_description=None,
                                                offering_type=None,
                                                max_records=None,
                                                marker=None):
        """
        Lists available reserved Cache Node offerings.

        :type reserved_cache_nodes_offering_id: string
        :param reserved_cache_nodes_offering_id: The offering identifier filter
            value. Specify this parameter to show only the available offering
            that matches the specified reservation identifier.  Example:
            `438012d3-4052-4cc7-b2e3-8d3372e0e706`

        :type cache_node_type: string
        :param cache_node_type: The Cache Node type filter value. Specify this
            parameter to show only the available offerings matching the
            specified Cache Node type.

        :type duration: string
        :param duration: Duration filter value, specified in years or seconds.
            Specify this parameter to show only reservations for this duration.
            Valid Values: `1 | 3 | 31536000 | 94608000`

        :type product_description: string
        :param product_description: Product description filter value. Specify
            this parameter to show only the available offerings matching the
            specified product description.

        :type offering_type: string
        :param offering_type: The offering type filter value. Specify this
            parameter to show only the available offerings matching the
            specified offering type.  Valid Values: `"Light Utilization" |
            "Medium Utilization" | "Heavy Utilization"`

        :type max_records: integer
        :param max_records: The maximum number of records to include in the
            response. If more than the `MaxRecords` value is available, a
            marker is included in the response so that the following results
            can be retrieved.  Default: 100  Constraints: minimum 20, maximum
            100

        :type marker: string
        :param marker: The marker provided in the previous request. If this
            parameter is specified, the response includes records beyond the
            marker only, up to `MaxRecords`.

        """
        params = {}
        if reserved_cache_nodes_offering_id is not None:
            params['ReservedCacheNodesOfferingId'] = reserved_cache_nodes_offering_id
        if cache_node_type is not None:
            params['CacheNodeType'] = cache_node_type
        if duration is not None:
            params['Duration'] = duration
        if product_description is not None:
            params['ProductDescription'] = product_description
        if offering_type is not None:
            params['OfferingType'] = offering_type
        if max_records is not None:
            params['MaxRecords'] = max_records
        if marker is not None:
            params['Marker'] = marker
        return self._make_request(
            action='DescribeReservedCacheNodesOfferings',
            verb='POST',
            path='/', params=params)

    def modify_cache_cluster(self, cache_cluster_id, num_cache_nodes=None,
                             cache_node_ids_to_remove=None,
                             cache_security_group_names=None,
                             security_group_ids=None,
                             preferred_maintenance_window=None,
                             notification_topic_arn=None,
                             cache_parameter_group_name=None,
                             notification_topic_status=None,
                             apply_immediately=None, engine_version=None,
                             auto_minor_version_upgrade=None):
        """
        Modifies the Cache Cluster settings. You can change one or
        more Cache Cluster configuration parameters by specifying the
        parameters and the new values in the request.

        :type cache_cluster_id: string
        :param cache_cluster_id: The Cache Cluster identifier. This value is
            stored as a lowercase string.

        :type num_cache_nodes: integer
        :param num_cache_nodes: The number of Cache Nodes the Cache Cluster
            should have. If NumCacheNodes is greater than the existing number
            of Cache Nodes, Cache Nodes will be added. If NumCacheNodes is less
            than the existing number of Cache Nodes, Cache Nodes will be
            removed. When removing Cache Nodes, the Ids of the specific Cache
            Nodes to be removed must be supplied using the CacheNodeIdsToRemove
            parameter.

        :type cache_node_ids_to_remove: list
        :param cache_node_ids_to_remove: The list of Cache Node IDs to be
            removed. This parameter is only valid when NumCacheNodes is less
            than the existing number of Cache Nodes. The number of Cache Node
            Ids supplied in this parameter must match the difference between
            the existing number of Cache Nodes in the cluster and the new
            NumCacheNodes requested.

        :type cache_security_group_names: list
        :param cache_security_group_names: A list of Cache Security Group Names
            to authorize on this Cache Cluster. This change is asynchronously
            applied as soon as possible.  This parameter can be used only with
            clusters that are created outside of an Amazon Virtual Private
            Cloud (VPC).  Constraints: Must contain no more than 255
            alphanumeric characters. Must not be "Default".

        :type security_group_ids: list
        :param security_group_ids: Specifies the VPC Security Groups associated
            with the Cache Cluster.  This parameter can be used only with
            clusters that are created in an Amazon Virtual Private Cloud (VPC).

        :type preferred_maintenance_window: string
        :param preferred_maintenance_window: The weekly time range (in UTC)
            during which system maintenance can occur, which may result in an
            outage. This change is made immediately. If moving this window to
            the current time, there must be at least 120 minutes between the
            current time and end of the window to ensure pending changes are
            applied.

        :type notification_topic_arn: string
        :param notification_topic_arn: The Amazon Resource Name (ARN) of the
            SNS topic to which notifications will be sent.  The SNS topic owner
            must be same as the Cache Cluster owner.

        :type cache_parameter_group_name: string
        :param cache_parameter_group_name: The name of the Cache Parameter
            Group to apply to this Cache Cluster. This change is asynchronously
            applied as soon as possible for parameters when the
            ApplyImmediately parameter is specified as true for this request.

        :type notification_topic_status: string
        :param notification_topic_status: The status of the Amazon SNS
            notification topic. The value can be active or inactive .
            Notifications are sent only if the status is active .

        :type apply_immediately: boolean
        :param apply_immediately: Specifies whether or not the modifications in
            this request and any pending modifications are asynchronously
            applied as soon as possible, regardless of the
            PreferredMaintenanceWindow setting for the Cache Cluster.  If this
            parameter is passed as `False`, changes to the Cache Cluster are
            applied on the next maintenance reboot, or the next failure reboot,
            whichever occurs first.  Default: `False`

        :type engine_version: string
        :param engine_version: The version of the cache engine to upgrade this
            cluster to.

        :type auto_minor_version_upgrade: boolean
        :param auto_minor_version_upgrade: Indicates that minor engine upgrades
            will be applied automatically to the Cache Cluster during the
            maintenance window.  Default: `True`

        """
        params = {'CacheClusterId': cache_cluster_id, }
        if num_cache_nodes is not None:
            params['NumCacheNodes'] = num_cache_nodes
        if cache_node_ids_to_remove is not None:
            self.build_list_params(params,
                                   cache_node_ids_to_remove,
                                   'CacheNodeIdsToRemove.member')
        if cache_security_group_names is not None:
            self.build_list_params(params,
                                   cache_security_group_names,
                                   'CacheSecurityGroupNames.member')
        if security_group_ids is not None:
            self.build_list_params(params,
                                   security_group_ids,
                                   'SecurityGroupIds.member')
        if preferred_maintenance_window is not None:
            params['PreferredMaintenanceWindow'] = preferred_maintenance_window
        if notification_topic_arn is not None:
            params['NotificationTopicArn'] = notification_topic_arn
        if cache_parameter_group_name is not None:
            params['CacheParameterGroupName'] = cache_parameter_group_name
        if notification_topic_status is not None:
            params['NotificationTopicStatus'] = notification_topic_status
        if apply_immediately is not None:
            params['ApplyImmediately'] = str(
                apply_immediately).lower()
        if engine_version is not None:
            params['EngineVersion'] = engine_version
        if auto_minor_version_upgrade is not None:
            params['AutoMinorVersionUpgrade'] = str(
                auto_minor_version_upgrade).lower()
        return self._make_request(
            action='ModifyCacheCluster',
            verb='POST',
            path='/', params=params)

    def modify_cache_parameter_group(self, cache_parameter_group_name,
                                     parameter_name_values):
        """
        Modifies the parameters of a CacheParameterGroup. To modify
        more than one parameter, submit a list of ParameterName and
        ParameterValue parameters. A maximum of 20 parameters can be
        modified in a single request.

        :type cache_parameter_group_name: string
        :param cache_parameter_group_name: The name of the cache parameter
            group to modify.

        :type parameter_name_values: list
        :param parameter_name_values: An array of parameter names and values
            for the parameter update. At least one parameter name and value
            must be supplied; subsequent arguments are optional. A maximum of
            20 parameters may be modified in a single request.

        """
        params = {
            'CacheParameterGroupName': cache_parameter_group_name,
        }
        self.build_complex_list_params(
            params, parameter_name_values,
            'ParameterNameValues.member',
            ('ParameterName', 'ParameterValue'))
        return self._make_request(
            action='ModifyCacheParameterGroup',
            verb='POST',
            path='/', params=params)

    def modify_cache_subnet_group(self, cache_subnet_group_name,
                                  cache_subnet_group_description=None,
                                  subnet_ids=None):
        """
        Modifies an existing Cache Subnet Group.

        :type cache_subnet_group_name: string
        :param cache_subnet_group_name: The name for the Cache Subnet Group.
            This value is stored as a lowercase string.  Constraints: Must
            contain no more than 255 alphanumeric characters or hyphens.
            Example: `mysubnetgroup`

        :type cache_subnet_group_description: string
        :param cache_subnet_group_description: The description for the Cache
            Subnet Group.

        :type subnet_ids: list
        :param subnet_ids: The EC2 Subnet IDs for the Cache Subnet Group.

        """
        params = {'CacheSubnetGroupName': cache_subnet_group_name, }
        if cache_subnet_group_description is not None:
            params['CacheSubnetGroupDescription'] = cache_subnet_group_description
        if subnet_ids is not None:
            self.build_list_params(params,
                                   subnet_ids,
                                   'SubnetIds.member')
        return self._make_request(
            action='ModifyCacheSubnetGroup',
            verb='POST',
            path='/', params=params)

    def purchase_reserved_cache_nodes_offering(self,
                                               reserved_cache_nodes_offering_id,
                                               reserved_cache_node_id=None,
                                               cache_node_count=None):
        """
        Purchases a reserved Cache Node offering.

        :type reserved_cache_nodes_offering_id: string
        :param reserved_cache_nodes_offering_id: The ID of the Reserved Cache
            Node offering to purchase.  Example:
            438012d3-4052-4cc7-b2e3-8d3372e0e706

        :type reserved_cache_node_id: string
        :param reserved_cache_node_id: Customer-specified identifier to track
            this reservation.  Example: myreservationID

        :type cache_node_count: integer
        :param cache_node_count: The number of instances to reserve.  Default:
            `1`

        """
        params = {
            'ReservedCacheNodesOfferingId': reserved_cache_nodes_offering_id,
        }
        if reserved_cache_node_id is not None:
            params['ReservedCacheNodeId'] = reserved_cache_node_id
        if cache_node_count is not None:
            params['CacheNodeCount'] = cache_node_count
        return self._make_request(
            action='PurchaseReservedCacheNodesOffering',
            verb='POST',
            path='/', params=params)

    def reboot_cache_cluster(self, cache_cluster_id,
                             cache_node_ids_to_reboot):
        """
        Reboots some (or all) of the cache cluster nodes within a
        previously provisioned ElastiCache cluster. This API results
        in the application of modified CacheParameterGroup parameters
        to the cache cluster. This action is taken as soon as
        possible, and results in a momentary outage to the cache
        cluster during which the cache cluster status is set to
        rebooting. During that momentary outage, the contents of the
        cache (for each cache cluster node being rebooted) are lost. A
        CacheCluster event is created when the reboot is completed.

        :type cache_cluster_id: string
        :param cache_cluster_id: The Cache Cluster identifier. This parameter
            is stored as a lowercase string.

        :type cache_node_ids_to_reboot: list
        :param cache_node_ids_to_reboot: A list of Cache Cluster Node Ids to
            reboot. To reboot an entire cache cluster, specify all cache
            cluster node Ids.

        """
        params = {'CacheClusterId': cache_cluster_id, }
        self.build_list_params(params,
                               cache_node_ids_to_reboot,
                               'CacheNodeIdsToReboot.member')
        return self._make_request(
            action='RebootCacheCluster',
            verb='POST',
            path='/', params=params)

    def reset_cache_parameter_group(self, cache_parameter_group_name,
                                    parameter_name_values,
                                    reset_all_parameters=None):
        """
        Modifies the parameters of a CacheParameterGroup to the engine
        or system default value. To reset specific parameters submit a
        list of the parameter names. To reset the entire
        CacheParameterGroup, specify the CacheParameterGroup name and
        ResetAllParameters parameters.

        :type cache_parameter_group_name: string
        :param cache_parameter_group_name: The name of the Cache Parameter
            Group.

        :type reset_all_parameters: boolean
        :param reset_all_parameters: Specifies whether ( true ) or not ( false
            ) to reset all parameters in the Cache Parameter Group to default
            values.

        :type parameter_name_values: list
        :param parameter_name_values: An array of parameter names which should
            be reset. If not resetting the entire CacheParameterGroup, at least
            one parameter name must be supplied.

        """
        params = {
            'CacheParameterGroupName': cache_parameter_group_name,
        }
        self.build_complex_list_params(
            params, parameter_name_values,
            'ParameterNameValues.member',
            ('ParameterName', 'ParameterValue'))
        if reset_all_parameters is not None:
            params['ResetAllParameters'] = str(
                reset_all_parameters).lower()
        return self._make_request(
            action='ResetCacheParameterGroup',
            verb='POST',
            path='/', params=params)

    def revoke_cache_security_group_ingress(self, cache_security_group_name,
                                            ec2_security_group_name,
                                            ec2_security_group_owner_id):
        """
        Revokes ingress from a CacheSecurityGroup for previously
        authorized EC2 Security Groups.

        :type cache_security_group_name: string
        :param cache_security_group_name: The name of the Cache Security Group
            to revoke ingress from.

        :type ec2_security_group_name: string
        :param ec2_security_group_name: The name of the EC2 Security Group to
            revoke access from.

        :type ec2_security_group_owner_id: string
        :param ec2_security_group_owner_id: The AWS Account Number of the owner
            of the security group specified in the EC2SecurityGroupName
            parameter. The AWS Access Key ID is not an acceptable value.

        """
        params = {
            'CacheSecurityGroupName': cache_security_group_name,
            'EC2SecurityGroupName': ec2_security_group_name,
            'EC2SecurityGroupOwnerId': ec2_security_group_owner_id,
        }
        return self._make_request(
            action='RevokeCacheSecurityGroupIngress',
            verb='POST',
            path='/', params=params)

    def _make_request(self, action, verb, path, params):
        params['ContentType'] = 'JSON'
        response = self.make_request(action=action, verb='POST',
                                     path='/', params=params)
        body = response.read()
        boto.log.debug(body)
        if response.status == 200:
            return json.loads(body)
        else:
            raise self.ResponseError(response.status, response.reason, body)
