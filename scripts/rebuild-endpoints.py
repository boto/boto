"""Rebuild endpoint config.

Final format looks like this::
{
    "autoscaling": {
        "ap-northeast-1": "autoscaling.ap-northeast-1.amazonaws.com",
        "ap-northeast-2": "autoscaling.ap-northeast-2.amazonaws.com",
        "ap-southeast-1": "autoscaling.ap-southeast-1.amazonaws.com",
        ...
    },
    "service-name": {
        "region": "hostname"
    }
}

This will use the EndpointResolver from botocore to regenerate
endpoints.  To regen the latest static endpoints, ensure you have
the latest version of botocore installed before running this script.

Usage
=====

To print the newly gen'd endpoints to stdout::

    python rebuild-endpoints.py

To overwrite the existing endpoints.json file in boto:

    python rebuild-endpoints.py --overwrite

If you have a custom upstream endpoints.json file you'd like
to use, you can provide the ``--endpoints-file``:

    python rebuild-endpoints.py --endpoints-json custom-endpoints.json

"""
import sys
import os
import json
import argparse


try:
    import botocore.session
    from botocore.regions import EndpointResolver
except ImportError:
    print("Couldn't import botocore, make sure it's installed in order "
          "to regen endpoint data.")
    sys.exit(1)


EXISTING_ENDPOINTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'boto', 'endpoints.json')


def _load_endpoint_services(filename):
    with open(filename) as f:
        return list(json.load(f))


class StrictEndpointResolver(object):
    """Endpoint Resolver that verifies services in a partition."""

    # It's worth seeing if any of the stuff in this class makes sense
    # to move back into botocore.  This might be too specific to boto2's
    # usage.  The intent was to try to make the StaticEndpointBuilder
    # as easy to follow as possible, so this class wraps an existing
    # botocore endpoint and provides some extension methods.  The main
    # extension points are:
    #
    # * Introspection about known services in a partition.
    # * Chaining partition iteration (for boto2 we just need to create
    #   a list of region->endpoints across all known partitions so this
    #   class provides iterators that allow you to iterate over all known
    #   regions for all known partitions).
    # * Helper method for static hostname lookup by abstracting the
    #   sslCommonName checks into a "get_hostname" method.
    # * Allowing you to use "service names" specific to boto2 when
    #   generating endpoints.  Internally this has a mapping of which endpoint
    #   prefixes to use.

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

    def __init__(self, resolver, endpoint_data,
                 service_name_map=None):
        #: An instance of botocore.regions.EndpointResolver.
        self._resolver = resolver
        self._endpoint_data = endpoint_data
        if service_name_map is None:
            service_name_map = self.SERVICE_RENAMES
        self._service_map = service_name_map

    def regions_for_service(self, service_name):
        # "What are all the regions EC2 is in across all known partitions?"
        endpoint_prefix = self._endpoint_prefix(service_name)
        for partition_name in self.get_available_partitions():
            if self.is_service_in_partition(service_name, partition_name):
                for region_name in self._resolver.get_available_endpoints(
                        endpoint_prefix, partition_name):
                    yield region_name

    def regions_for_partition(self, partition_name):
        # "What are all the known regions in a given partition?"
        # This is used in boto to create entries for "cloudfront"
        # for every region:
        # us-east-1: cloudfront.amazonaws.com
        # us-west-2: cloudfront.amazonaws.com
        # ...
        partition_data = self._get_partition_data(partition_name)
        return [r for r in list(partition_data['regions'])
                if 'global' not in r]

    def partitions_for_service(self, service_name):
        # "In which partitions is 'cloudfront' available?"
        # This is used because we should *not* generate entries
        # for cn-north-1 for cloudfront, it's not available in China.
        # This can be accomplished by using this method and
        # regions_for_partition. See the _special_case_global_service
        # method in StaticEndpointBuilder.
        for partition_name in self.get_available_partitions():
            if self.is_service_in_partition(service_name, partition_name):
                yield partition_name

    def get_available_partitions(self):
        return self._resolver.get_available_partitions()

    def get_hostname(self, service_name, region_name):
        # Static hostname given a service_name/region_name
        # We'll map the service_name to the endpoint_prefix
        # and validate that the service is in the partition.
        partition = self._partition_for_region(region_name)
        if not self.is_service_in_partition(service_name, partition):
            raise ValueError("Unknown service '%s' in partition '%s'" % (
                service_name, partition))
        endpoint_prefix = self._endpoint_prefix(service_name)
        endpoint_config = self._resolver.construct_endpoint(
            endpoint_prefix, region_name)
        hostname = endpoint_config.get('sslCommonName',
                                       endpoint_config.get('hostname'))
        return hostname

    def is_service_in_partition(self, service_name, partition_name):
        # Is iam in aws-cn? Yes
        # Is cloudfront in aws-cn? No
        endpoint_prefix = self._endpoint_prefix(service_name)
        partition_data = self._get_partition_data(partition_name)
        return endpoint_prefix in partition_data['services']

    def _partition_for_region(self, region_name):
        # us-east-1 -> aws
        # us-west-2 -> aws
        # cn-north-1 -> aws-cn
        for partition in self._endpoint_data['partitions']:
            if region_name in partition['regions']:
                return partition['partition']
        raise ValueError("Unknown region name: %s" % region_name)

    def _get_partition_data(self, partition_name):
        for partition in self._endpoint_data['partitions']:
            if partition['partition'] == partition_name:
                return partition
        raise ValueError("Could not find partition data for: %s"
                         % partition_name)

    def _endpoint_prefix(self, service_name):
        endpoint_prefix = self._service_map.get(
            service_name, service_name)
        return endpoint_prefix

    def is_global_service(self, service_name):
        # This is making the assumption that if a service is
        # a partitionEndpoint for one partition, it will be that
        # way for *all* partitions.  Technically possible to be
        # different, but in practice it's not.
        # We need this because this is how we know to trigger
        # special case behavior with services like iam, cloudfront.
        return (
            'partitionEndpoint' in
            self._endpoint_data['partitions'][0]['services'].get(
                service_name, {}))


class StaticEndpointBuilder(object):

    def __init__(self, resolver):
        self._resolver = resolver

    def build_static_endpoints(self, service_names):
        """Build a set of static endpoints.

        :param service_names: The name of services to build.
            These are the service names they are supported by
            boto2.  They also must use the names that boto2
            uses, not boto3, e.g "ec2containerservice" and not "ecs".

        :return: A dict consisting of::
            {"service": {"region": "full.host.name"}}

        """
        static_endpoints = {}
        for name in service_names:
            endpoints_for_service = self._build_endpoints_for_service(name)
            if endpoints_for_service:
                # It's possible that when we try to build endpoints for services
                # we get an empty hash.  In that case we don't bother adding
                # it to the final list of static endpoints.
                static_endpoints[name] = endpoints_for_service
        self._deal_with_special_cases(static_endpoints)
        return static_endpoints

    def _build_endpoints_for_service(self, service_name):
        # Given a service name, 'ec2', build a dict of
        # 'region' -> 'hostname'
        if self._resolver.is_global_service(service_name):
            return self._special_case_global_service(service_name)
        endpoints = {}
        for region_name in self._resolver.regions_for_service(service_name):
            endpoints[region_name] = self._resolver.get_hostname(service_name,
                                                                  region_name)
        return endpoints

    def _special_case_global_service(self, service_name):
        # In boto2, an entry for each known region is added with the same
        # partition wide endpoint for every partition the service is available
        # in.  This method implements this special cased behavior.
        endpoints = {}
        for partition in self._resolver.partitions_for_service(service_name):
            region_names = self._resolver.regions_for_partition(
                partition)
            for region_name in region_names:
                endpoints[region_name] = self._resolver.get_hostname(
                    service_name, region_name)
        return endpoints

    def _deal_with_special_cases(self, static_endpoints):
        # I'm not sure why we do this, but cloudsearchdomain endpoints
        # use the exact same set of endpoints as cloudsearch.
        if 'cloudsearch' in static_endpoints:
            static_endpoints['cloudsearchdomain'] = static_endpoints['cloudsearch']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--endpoints-file',
                        help=('Path to endpoints.json.  If this argument '
                              'is not given, then the endpoints.json file '
                              'bundled with botocore will be used.'))
    args = parser.parse_args()
    known_services_in_existing_endpoints = _load_endpoint_services(
        EXISTING_ENDPOINTS_FILE)
    session = botocore.session.get_session()
    if args.endpoints_file:
        with open(args.endpoints_file) as f:
            endpoint_data = json.load(f)
    else:
        endpoint_data = session.get_data('endpoints')
    resolver = EndpointResolver(endpoint_data)
    strict_resolver = StrictEndpointResolver(resolver, endpoint_data)
    builder = StaticEndpointBuilder(strict_resolver)
    static_endpoints = builder.build_static_endpoints(
        known_services_in_existing_endpoints)
    json_data = json.dumps(static_endpoints, indent=4, sort_keys=True)
    if args.overwrite:
        with open(EXISTING_ENDPOINTS_FILE, 'w') as f:
            f.write(json_data)
    else:
        print(json_data)


if __name__ == '__main__':
    main()
