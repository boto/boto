# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock
import os
import json

from nose.tools import assert_equal

from tests.unit import unittest
from boto.endpoints import BotoEndpointResolver
from boto.endpoints import StaticEndpointBuilder


class BaseEndpointResolverTest(unittest.TestCase):
    def _endpoint_data(self):
        return {
            'partitions': [
                {
                    'partition': 'aws',
                    'dnsSuffix': 'amazonaws.com',
                    'regionRegex': '^(us|eu)\-\w+$',
                    'defaults': {
                        'hostname': '{service}.{region}.{dnsSuffix}'
                    },
                    'regions': {
                        'us-foo': {'regionName': 'a'},
                        'us-bar': {'regionName': 'b'},
                        'eu-baz': {'regionName': 'd'}
                    },
                    'services': {
                        'ec2': {
                            'endpoints': {
                                'us-foo': {},
                                'us-bar': {},
                                'eu-baz': {},
                                'd': {}
                            }
                        },
                        's3': {
                            'defaults': {
                                'sslCommonName': \
                                    '{service}.{region}.{dnsSuffix}'
                            },
                            'endpoints': {
                                'us-foo': {
                                    'sslCommonName': \
                                        '{region}.{service}.{dnsSuffix}'
                                },
                                'us-bar': {},
                                'eu-baz': {'hostname': 'foo'}
                            }
                        },
                        'not-regionalized': {
                            'isRegionalized': False,
                            'partitionEndpoint': 'aws',
                            'endpoints': {
                                'aws': {'hostname': 'not-regionalized'},
                                'us-foo': {},
                                'eu-baz': {}
                            }
                        },
                        'non-partition': {
                            'partitionEndpoint': 'aws',
                            'endpoints': {
                                'aws': {'hostname': 'host'},
                                'us-foo': {}
                            }
                        },
                        'merge': {
                            'defaults': {
                                'signatureVersions': ['v2'],
                                'protocols': ['http']
                            },
                            'endpoints': {
                                'us-foo': {'signatureVersions': ['v4']},
                                'us-bar': {'protocols': ['https']}
                            }
                        }
                    }
                },
                {
                    'partition': 'foo',
                    'dnsSuffix': 'foo.com',
                    'regionRegex': '^(foo)\-\w+$',
                    'defaults': {
                        'hostname': '{service}.{region}.{dnsSuffix}',
                        'protocols': ['http'],
                        'foo': 'bar'
                    },
                    'regions': {
                        'foo-1': {'regionName': '1'},
                        'foo-2': {'regionName': '2'},
                        'foo-3': {'regionName': '3'}
                    },
                    'services': {
                        'ec2': {
                            'endpoints': {
                                'foo-1': {
                                    'foo': 'baz'
                                },
                                'foo-2': {},
                                'foo-3': {}
                            }
                        }
                    }
                }
            ]
        }


class TestBotoEndpointResolver(BaseEndpointResolverTest):
    def test_get_endpoints_with_rename(self):
        rename_map = {'ec3': 'ec2'}
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            service_rename_map=rename_map
        )
        endpoints = sorted(resolver.get_available_endpoints('ec3'))
        expected_endpoints = sorted(['us-bar', 'eu-baz', 'us-foo'])
        self.assertEqual(endpoints, expected_endpoints)

    def test_get_endpoints_with_legacy_format_data(self):
        legacy_endpoints = {
            'ec2': {'mars-west-1': 'ec2.mars-west-1.amazonaws.com'}
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            legacy_endpoint_data=legacy_endpoints
        )
        endpoints = sorted(resolver.get_available_endpoints('ec2'))
        expected_endpoints = sorted([
            'us-bar', 'eu-baz', 'us-foo', 'mars-west-1'])
        self.assertEqual(endpoints, expected_endpoints)

    def test_get_all_available_regions(self):
        resolver = BotoEndpointResolver(self._endpoint_data())
        regions = sorted(resolver.get_all_available_regions('ec2'))
        expected_regions = sorted([
            'us-bar', 'eu-baz', 'us-foo', 'foo-1', 'foo-2', 'foo-3'])
        self.assertEqual(regions, expected_regions)

    def test_get_all_regions_on_non_regional_service(self):
        resolver = BotoEndpointResolver(self._endpoint_data())
        regions = sorted(
            resolver.get_all_available_regions('not-regionalized'))
        expected_regions = sorted(['us-foo', 'us-bar', 'eu-baz'])
        self.assertEqual(regions, expected_regions)

    def test_get_all_regions_with_legacy_format_data(self):
        legacy_endpoints = {
            'ec2': {'mars-west-1': 'ec2.mars-west-1.amazonaws.com'}
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            legacy_endpoint_data=legacy_endpoints
        )
        regions = sorted(resolver.get_all_available_regions('ec2'))
        expected_regions = sorted([
            'us-bar', 'eu-baz', 'us-foo', 'foo-1', 'foo-2', 'foo-3',
            'mars-west-1'
        ])
        self.assertEqual(regions, expected_regions)

    def test_get_all_regions_with_renames(self):
        rename_map = {'ec3': 'ec2'}
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            service_rename_map=rename_map
        )
        regions = sorted(resolver.get_all_available_regions('ec2'))
        expected_regions = sorted([
            'us-bar', 'eu-baz', 'us-foo', 'foo-1', 'foo-2', 'foo-3'])
        self.assertEqual(regions, expected_regions)

    def test_construct_endpoint_with_rename(self):
        rename_map = {'ec3': 'ec2'}
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            service_rename_map=rename_map
        )
        endpoint = resolver.construct_endpoint('ec3', 'us-foo')
        expected_endpoint = {
            'dnsSuffix': 'amazonaws.com',
            'endpointName': 'us-foo',
            'hostname': 'ec2.us-foo.amazonaws.com',
            'partition': 'aws'
        }
        self.assertEqual(endpoint, expected_endpoint)

    def test_construct_endpoint_with_legacy_format_data(self):
        legacy_endpoints = {
            'ec2': {'mars-west-1': 'ec2.mars-west-1.amazonaws.com'}
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            legacy_endpoint_data=legacy_endpoints
        )
        constructed_endpoint = resolver.construct_endpoint(
            'ec2', 'mars-west-1')
        expected_endpoint = {
            'endpointName': 'mars-west-1',
            'hostname': 'ec2.mars-west-1.amazonaws.com',
            'partition': 'aws'
        }
        self.assertEqual(constructed_endpoint, expected_endpoint)

    def test_legacy_format_data_has_priority_in_construct_endpoint(self):
        legacy_endpoints = {
            'ec2': {'us-foo': 'ec2.us-foo-3.amazonaws.com'}
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            legacy_endpoint_data=legacy_endpoints
        )
        constructed_endpoint = resolver.construct_endpoint('ec2', 'us-foo')
        expected_endpoint = {
            'endpointName': 'us-foo',
            'hostname': 'ec2.us-foo-3.amazonaws.com',
            'partition': 'aws'
        }
        self.assertEqual(constructed_endpoint, expected_endpoint)

    def test_resolve_hostname(self):
        resolver = BotoEndpointResolver(self._endpoint_data())
        hostname = resolver.resolve_hostname('ec2', 'us-foo')
        expected_hostname = 'ec2.us-foo.amazonaws.com'
        self.assertEqual(hostname, expected_hostname)

    def test_resolve_hostname_with_rename(self):
        rename_map = {'ec3': 'ec2'}
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            service_rename_map=rename_map
        )
        hostname = resolver.resolve_hostname('ec3', 'us-foo')
        expected_hostname = 'ec2.us-foo.amazonaws.com'
        self.assertEqual(hostname, expected_hostname)

    def test_resolve_hostname_with_legacy_format_data(self):
        legacy_endpoints = {
            'ec2': {'mars-west-1': 'ec2.mars-west-1.amazonaws.com'}
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            legacy_endpoint_data=legacy_endpoints
        )
        hostname = resolver.resolve_hostname('ec2', 'mars-west-1')
        expected_hostname = 'ec2.mars-west-1.amazonaws.com'
        self.assertEqual(hostname, expected_hostname)

    def test_legacy_format_data_has_priority_in_resolve_hostname(self):
        legacy_endpoints = {
            'ec2': {'us-foo': 'ec2.us-foo-3.amazonaws.com'}
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            legacy_endpoint_data=legacy_endpoints
        )
        hostname = resolver.resolve_hostname('ec2', 'us-foo')
        expected_hostname = 'ec2.us-foo-3.amazonaws.com'
        self.assertEqual(hostname, expected_hostname)

    def test_resolve_hostname_with_ssl_common_name(self):
        resolver = BotoEndpointResolver(self._endpoint_data())
        hostname = resolver.resolve_hostname('s3', 'us-foo')
        expected_hostname = 'us-foo.s3.amazonaws.com'
        self.assertEqual(hostname, expected_hostname)

    def test_get_available_services(self):
        resolver = BotoEndpointResolver(self._endpoint_data())
        services = sorted(resolver.get_available_services())
        expected_services = sorted([
            'ec2', 's3', 'not-regionalized', 'non-partition', 'merge'])
        self.assertEqual(services, expected_services)

    def test_get_available_services_with_extra_data(self):
        legacy_endpoints = {
            'new-service': {
                'moon-darkside-1': 'new-service.moon-darkside-1.amazonaws.com'
            }
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            legacy_endpoint_data=legacy_endpoints
        )
        services = sorted(resolver.get_available_services())
        expected_services = sorted([
            'ec2', 's3', 'not-regionalized', 'non-partition', 'merge',
            'new-service'
        ])
        self.assertEqual(services, expected_services)

    def test_get_available_services_with_renames(self):
        rename_map = {'ec3': 'ec2'}
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            service_rename_map=rename_map
        )
        services = sorted(resolver.get_available_services())
        expected_services = sorted([
            'ec3', 's3', 'not-regionalized', 'non-partition', 'merge'])
        self.assertEqual(services, expected_services)


class TestStaticEndpointBuilder(unittest.TestCase):
    def setUp(self):
        self.resolver = mock.Mock(spec=BotoEndpointResolver)
        self.builder = StaticEndpointBuilder(self.resolver)

    def test_build_single_service(self):
        regions = ['mars-west-1', 'moon-darkside-1']
        self.resolver.get_all_available_regions.return_value = regions
        self.resolver.resolve_hostname.side_effect = [
            'fake-service.mars-west-1.amazonaws.com',
            'fake-service.moon-darkside-1.amazonaws.com'
        ]
        endpoints = self.builder.build_static_endpoints(['fake-service'])
        expected_endpoints = {'fake-service': {
            'mars-west-1': 'fake-service.mars-west-1.amazonaws.com',
            'moon-darkside-1': 'fake-service.moon-darkside-1.amazonaws.com'
        }}
        self.assertEqual(endpoints, expected_endpoints)

    def test_build_multiple_services(self):
        regions = [['mars-west-1', 'moon-darkside-1'], ['mars-west-1']]
        self.resolver.get_all_available_regions.side_effect = regions
        self.resolver.resolve_hostname.side_effect = [
            'fake-service.mars-west-1.amazonaws.com',
            'fake-service.moon-darkside-1.amazonaws.com',
            'sample-service.mars-west-1.amazonaws.com'
        ]
        services = ['fake-service', 'sample-service']
        endpoints = self.builder.build_static_endpoints(services)
        expected_endpoints = {
            'fake-service': {
                'mars-west-1': 'fake-service.mars-west-1.amazonaws.com',
                'moon-darkside-1': 'fake-service.moon-darkside-1.amazonaws.com'
            },
            'sample-service': {
                'mars-west-1': 'sample-service.mars-west-1.amazonaws.com'
            }
        }
        self.assertEqual(endpoints, expected_endpoints)

    def test_build_all_services(self):
        regions = [['mars-west-1', 'moon-darkside-1'], ['mars-west-1']]
        self.resolver.get_all_available_regions.side_effect = regions
        self.resolver.resolve_hostname.side_effect = [
            'fake-service.mars-west-1.amazonaws.com',
            'fake-service.moon-darkside-1.amazonaws.com',
            'sample-service.mars-west-1.amazonaws.com'
        ]
        
        # Set the list of available services on the resolver so it doesn't
        # have to be specified on the call to build_static_endpoints
        services = ['fake-service', 'sample-service']
        self.resolver.get_available_services.return_value = services

        endpoints = self.builder.build_static_endpoints()
        expected_endpoints = {
            'fake-service': {
                'mars-west-1': 'fake-service.mars-west-1.amazonaws.com',
                'moon-darkside-1': 'fake-service.moon-darkside-1.amazonaws.com'
            },
            'sample-service': {
                'mars-west-1': 'sample-service.mars-west-1.amazonaws.com'
            }
        }
        self.assertEqual(endpoints, expected_endpoints)


def test_backwards_compatibility():
    # Tests backwards compatibility with the old endpoint generation tooling.
    # There are snapshots of the two endpoint formats at a single point in
    # time. Given the snapshot of the new endpoint file, this asserts that
    # we can generate the exact data in the snapshot of the old endpoints file.
    # A single 'test' is generated for each service.
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    old_endpoints_file = os.path.join(data_dir, 'old_endpoints.json')
    new_endpoints_file = os.path.join(data_dir, 'new_endpoints.json')

    with open(old_endpoints_file) as f:
        old_endpoints = json.load(f)

    with open(new_endpoints_file) as f:
        new_endpoints = json.load(f)

    resolver = BotoEndpointResolver(new_endpoints)
    builder = StaticEndpointBuilder(resolver)
    services = resolver.get_available_services()
    built = builder.build_static_endpoints(services)

    for service in services:
        old = old_endpoints[service]
        new = built[service]
        case = EndpointTestCase(service, old, new)
        yield case.run


class EndpointTestCase(object):
    def __init__(self, service, old_endpoints, new_endpoints):
        self.service = service
        self.old_endpoints = old_endpoints
        self.new_endpoints = new_endpoints

    def run(self):
        assert_equal(self.old_endpoints, self.new_endpoints)
