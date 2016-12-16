# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Resolves regions and endpoints.

This module implements endpoint resolution, including resolving endpoints for a
given service and region and resolving the available endpoints for a service
in a specific AWS partition.
"""
import logging
import re

from boto.exception import NoRegionError

LOG = logging.getLogger(__name__)
DEFAULT_URI_TEMPLATE = '{service}.{region}.{dnsSuffix}'
DEFAULT_SERVICE_DATA = {'endpoints': {}}


class BaseEndpointResolver(object):
    """Resolves regions and endpoints. Must be subclassed."""
    def construct_endpoint(self, service_name, region_name=None):
        """Resolves an endpoint for a service and region combination.

        :type service_name: string
        :param service_name: Name of the service to resolve an endpoint for
            (e.g., s3)

        :type region_name: string
        :param region_name: Region/endpoint name to resolve (e.g., us-east-1)
            if no region is provided, the first found partition-wide endpoint
            will be used if available.

        :rtype: dict
        :return: Returns a dict containing the following keys:
            - partition: (string, required) Resolved partition name
            - endpointName: (string, required) Resolved endpoint name
            - hostname: (string, required) Hostname to use for this endpoint
            - sslCommonName: (string) sslCommonName to use for this endpoint.
            - credentialScope: (dict) Signature version 4 credential scope
              - region: (string) region name override when signing.
              - service: (string) service name override when signing.
            - signatureVersions: (list<string>) A list of possible signature
              versions, including s3, v4, v2, and s3v4
            - protocols: (list<string>) A list of supported protocols
              (e.g., http, https)
            - ...: Other keys may be included as well based on the metadata
        """
        raise NotImplementedError

    def get_available_partitions(self):
        """Lists the partitions available to the endpoint resolver.

        :return: Returns a list of partition names (e.g., ["aws", "aws-cn"]).
        """
        raise NotImplementedError

    def get_available_endpoints(self, service_name, partition_name='aws',
                                allow_non_regional=False):
        """Lists the endpoint names of a particular partition.

        :type service_name: string
        :param service_name: Name of a service to list endpoint for (e.g., s3)

        :type partition_name: string
        :param partition_name: Name of the partition to limit endpoints to.
            (e.g., aws for the public AWS endpoints, aws-cn for AWS China
            endpoints, aws-us-gov for AWS GovCloud (US) Endpoints, etc.

        :type allow_non_regional: bool
        :param allow_non_regional: Set to True to include endpoints that are
             not regional endpoints (e.g., s3-external-1,
             fips-us-gov-west-1, etc).
        :return: Returns a list of endpoint names (e.g., ["us-east-1"]).
        """
        raise NotImplementedError


class EndpointResolver(BaseEndpointResolver):
    """Resolves endpoints based on partition endpoint metadata."""
    def __init__(self, endpoint_data):
        """
        :param endpoint_data: A dict of partition data.
        """
        if 'partitions' not in endpoint_data:
            raise ValueError('Missing "partitions" in endpoint data')
        self._endpoint_data = endpoint_data

    def get_available_partitions(self):
        result = []
        for partition in self._endpoint_data['partitions']:
            result.append(partition['partition'])
        return result

    def get_available_endpoints(self, service_name, partition_name='aws',
                                allow_non_regional=False):
        result = []
        for partition in self._endpoint_data['partitions']:
            if partition['partition'] != partition_name:
                continue
            services = partition['services']
            if service_name not in services:
                continue
            for endpoint_name in services[service_name]['endpoints']:
                if allow_non_regional or endpoint_name in partition['regions']:
                    result.append(endpoint_name)
        return result

    def construct_endpoint(self, service_name, region_name=None):
        # Iterate over each partition until a match is found.
        for partition in self._endpoint_data['partitions']:
            result = self._endpoint_for_partition(
                partition, service_name, region_name)
            if result:
                return result

    def _endpoint_for_partition(self, partition, service_name, region_name):
        # Get the service from the partition, or an empty template.
        service_data = partition['services'].get(
            service_name, DEFAULT_SERVICE_DATA)
        # Use the partition endpoint if no region is supplied.
        if region_name is None:
            if 'partitionEndpoint' in service_data:
                region_name = service_data['partitionEndpoint']
            else:
                raise NoRegionError()
        # Attempt to resolve the exact region for this partition.
        if region_name in service_data['endpoints']:
            return self._resolve(
                partition, service_name, service_data, region_name)
        # Check to see if the endpoint provided is valid for the partition.
        if self._region_match(partition, region_name):
            # Use the partition endpoint if set and not regionalized.
            partition_endpoint = service_data.get('partitionEndpoint')
            is_regionalized = service_data.get('isRegionalized', True)
            if partition_endpoint and not is_regionalized:
                LOG.debug('Using partition endpoint for %s, %s: %s',
                          service_name, region_name, partition_endpoint)
                return self._resolve(
                    partition, service_name, service_data, partition_endpoint)
            LOG.debug('Creating a regex based endpoint for %s, %s',
                      service_name, region_name)
            return self._resolve(
                partition, service_name, service_data, region_name)

    def _region_match(self, partition, region_name):
        if region_name in partition['regions']:
            return True
        if 'regionRegex' in partition:
            return re.compile(partition['regionRegex']).match(region_name)
        return False

    def _resolve(self, partition, service_name, service_data, endpoint_name):
        result = service_data['endpoints'].get(endpoint_name, {})
        result['partition'] = partition['partition']
        result['endpointName'] = endpoint_name
        # Merge in the service defaults then the partition defaults.
        self._merge_keys(service_data.get('defaults', {}), result)
        self._merge_keys(partition.get('defaults', {}), result)
        hostname = result.get('hostname', DEFAULT_URI_TEMPLATE)
        result['hostname'] = self._expand_template(
            partition, result['hostname'], service_name, endpoint_name)
        if 'sslCommonName' in result:
            result['sslCommonName'] = self._expand_template(
                partition, result['sslCommonName'], service_name,
                endpoint_name)
        result['dnsSuffix'] = partition['dnsSuffix']
        return result

    def _merge_keys(self, from_data, result):
        for key in from_data:
            if key not in result:
                result[key] = from_data[key]

    def _expand_template(self, partition, template, service_name,
                         endpoint_name):
        return template.format(
            service=service_name, region=endpoint_name,
            dnsSuffix=partition['dnsSuffix'])


class BotoEndpointResolver(EndpointResolver):
    """Endpoint resolver which handles boto2 compatibility concerns."""

    SERVICE_RENAMES = {
        # The botocore resolver is based on endpoint prefix.
        # These don't always sync up to the name that boto2 uses.
        # A mapping can be provided that handles the mapping between
        # "service names" and endpoint prefixes.
        'awslambda': 'lambda',
        'cloudwatch': 'monitoring',
        'ses': 'email',
        'ec2containerservice': 'ecs',
        'configservice': 'config',
    }

    def __init__(self, endpoint_data, boto_endpoint_data=None,
                 service_rename_map=None):
        """
        :type endpoint_data: dict
        :param endpoint_data: Regions and endpoints data in the same format
            as is used by botocore / boto3.

        :type boto_endpoint_data: dict
        :param boto_endpoint_data: Regions and endpoints data in the legacy
            boto2 format. This data takes precedence over any data found in
            `endpoint_data`.

        :type service_rename_map: dict
        :param service_rename_map: A mapping of boto2 service name to
            endpoint prefix.
        """
        super(BotoEndpointResolver, self).__init__(endpoint_data)
        self._boto_endpoint_data = boto_endpoint_data
        if service_rename_map is None:
            service_rename_map = self.SERVICE_RENAMES
        # Mapping of boto2 service name to endpoint prefix
        self._endpoint_prefix_map = service_rename_map
        # Mapping of endpoint prefix to boto2 service name
        self._service_name_map = dict(
            (v, k) for k, v in service_rename_map.items())

    def get_available_endpoints(self, service_name, partition_name='aws',
                                allow_non_regional=False):
        endpoint_prefix = self._endpoint_prefix(service_name)
        endpoints = super(BotoEndpointResolver, self).get_available_endpoints(
            endpoint_prefix, partition_name, allow_non_regional)
        boto_endpoints = self._get_available_boto_endpoints(service_name)
        return list(set(endpoints + boto_endpoints))

    def get_all_available_regions(self, service_name):
        """Retrieve every region across partitions for a service."""
        regions = set()
        endpoint_prefix = self._endpoint_prefix(service_name)

        # Get every region for every partition in the new endpoint format
        for partition_name in self.get_available_partitions():
            if self.is_global_service(service_name, partition_name):
                # Global services are available in every region in the
                # partition in which they are considered global.
                partition = self._get_partition_data(partition_name)
                regions.update(partition['regions'].keys())
            else:
                regions.update(
                    super(BotoEndpointResolver, self).get_available_endpoints(
                        endpoint_prefix, partition_name
                    )
                )

        # boto2 endpoint format has no partitions, so load them all.
        boto_endpoints = self._get_available_boto_endpoints(service_name)
        regions.update(boto_endpoints)
        return list(regions)

    def _get_available_boto_endpoints(self, service_name):
        """Get available regions from the boto format endpoints data.

        This does not make any assumptions about partition location or
        regionality.
        """
        if self._boto_endpoint_data is None:
            return []
        return list(self._boto_endpoint_data.get(service_name, {}).keys())

    def construct_endpoint(self, service_name, region_name=None):
        # Always prioritize the endpoint data in the boto format
        boto_endpoint = self._construct_boto_endpoint(
            service_name, region_name)
        if boto_endpoint is not None:
            return boto_endpoint

        # If there is no boto format data to be found, use the
        endpoint_prefix = self._endpoint_prefix(service_name)
        return super(BotoEndpointResolver, self).construct_endpoint(
            endpoint_prefix, region_name)

    def _construct_boto_endpoint(self, service_name, region_name):
        """Construct an endpoint from the boto format endpoints data."""
        if region_name is None or self._boto_endpoint_data is None:
            return None

        # Grab the hostname from the boto format endpoints data
        boto_endpoints = self._boto_endpoint_data.get(service_name, {})
        hostname = boto_endpoints.get(region_name, None)

        if hostname is None:
            return None

        # Put that data in the standard endpoint resolver format. The
        # partition is set as 'aws', but it ultimately doesn't matter what
        # it is set to since the boto data will always be returned.
        endpoint_data = {
            'partition': 'aws',
            'endpointName': region_name,
            'hostname': hostname,
        }

        return endpoint_data

    def resolve_hostname(self, service, region_name):
        """Resolve the hostname for a service in a particular region."""
        endpoint = self.construct_endpoint(service, region_name)
        return endpoint.get('sslCommonName', endpoint['hostname'])

    def get_available_services(self):
        """Get a list of all the available services in the endpoints file(s)"""
        services = set()

        if self._boto_endpoint_data is not None:
            services.update(self._boto_endpoint_data.keys())

        for partition in self._endpoint_data['partitions']:
            services.update(partition['services'].keys())

        return [self._service_name(s) for s in services]

    def is_global_service(self, service_name, partition_name='aws'):
        """Determines whether a service uses a global endpoint.

        In theory a service can be 'global' in one partition but regional in
        another. In practice, each service is all global or all regional.
        """
        endpoint_prefix = self._endpoint_prefix(service_name)
        partition = self._get_partition_data(partition_name)
        service = partition['services'].get(endpoint_prefix, {})
        return 'partitionEndpoint' in service

    def _get_partition_data(self, partition_name):
        """Get partition information for a particular partition.

        This should NOT be used to get service endpoint data because it only
        loads from the new endpoint format. It should only be used for
        partition metadata and partition specific service metadata.

        :type partition_name: str
        :param partition_name: The name of the partition to search for.

        :returns: Partition info from the new endpoints format.
        :rtype: dict or None
        """
        for partition in self._endpoint_data['partitions']:
            if partition['partition'] == partition_name:
                return partition
        raise ValueError(
            "Could not find partition data for: %s" % partition_name)

    def _endpoint_prefix(self, service_name):
        """Given a boto2 service name, get the endpoint prefix."""
        return self._endpoint_prefix_map.get(service_name, service_name)

    def _service_name(self, endpoint_prefix):
        """Given an endpoint prefix, get the boto2 service name."""
        return self._service_name_map.get(endpoint_prefix, endpoint_prefix)


class StaticEndpointBuilder(object):
    """Builds a static mapping of endpoints in the boto2 format."""

    def __init__(self, resolver):
        """
        :type resolver: BotoEndpointResolver
        :param resolver: An endpoint resolver.
        """
        self._resolver = resolver

    def build_static_endpoints(self, service_names=None):
        """Build a set of static endpoints in the legacy boto2 format.

        :param service_names: The names of the services to build. They must
            use the names that boto2 uses, not boto3, e.g "ec2containerservice"
            and not "ecs". If no service names are provided, all available
            services will be built.

        :return: A dict consisting of::
            {"service": {"region": "full.host.name"}}
        """
        if service_names is None:
            service_names = self._resolver.get_available_services()

        static_endpoints = {}
        for name in service_names:
            endpoints_for_service = self._build_endpoints_for_service(name)
            if endpoints_for_service:
                # It's possible that when we try to build endpoints for
                # services we get an empty hash.  In that case we don't
                # bother adding it to the final list of static endpoints.
                static_endpoints[name] = endpoints_for_service
        self._handle_special_cases(static_endpoints)
        return static_endpoints

    def _build_endpoints_for_service(self, service_name):
        # Given a service name, 'ec2', build a dict of
        # 'region' -> 'hostname'
        endpoints = {}
        regions = self._resolver.get_all_available_regions(service_name)
        for region_name in regions:
            endpoints[region_name] = self._resolver.resolve_hostname(
                service_name, region_name)
        return endpoints

    def _handle_special_cases(self, static_endpoints):
        # cloudsearchdomain endpoints use the exact same set of endpoints as
        # cloudsearch.
        if 'cloudsearch' in static_endpoints:
            cloudsearch_endpoints = static_endpoints['cloudsearch']
            static_endpoints['cloudsearchdomain'] = cloudsearch_endpoints
