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
from tests.unit import unittest

from boto.exception import NoRegionError
from boto.endpoints import EndpointResolver
from boto.endpoints import BotoEndpointResolver


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


class TestEndpointResolver(BaseEndpointResolverTest):

    def test_ensures_region_is_not_none(self):
        with self.assertRaises(NoRegionError):
            resolver = EndpointResolver(self._endpoint_data())
            resolver.construct_endpoint('foo', None)

    def test_ensures_required_keys_present(self):
        with self.assertRaises(ValueError):
            EndpointResolver({})

    def test_returns_empty_list_when_listing_for_different_partition(self):
        resolver = EndpointResolver(self._endpoint_data())
        self.assertEquals([], resolver.get_available_endpoints('ec2', 'bar'))

    def test_returns_empty_list_when_no_service_found(self):
        resolver = EndpointResolver(self._endpoint_data())
        self.assertEquals([], resolver.get_available_endpoints('what?'))

    def test_gets_endpoint_names(self):
        resolver = EndpointResolver(self._endpoint_data())
        result = resolver.get_available_endpoints(
            'ec2', allow_non_regional=True)
        self.assertEquals(['d', 'eu-baz', 'us-bar', 'us-foo'], sorted(result))

    def test_gets_endpoint_names_for_partition(self):
        resolver = EndpointResolver(self._endpoint_data())
        result = resolver.get_available_endpoints(
            'ec2', allow_non_regional=True, partition_name='foo')
        self.assertEquals(['foo-1', 'foo-2', 'foo-3'], sorted(result))

    def test_list_regional_endpoints_only(self):
        resolver = EndpointResolver(self._endpoint_data())
        result = resolver.get_available_endpoints(
            'ec2', allow_non_regional=False)
        self.assertEquals(['eu-baz', 'us-bar', 'us-foo'], sorted(result))

    def test_returns_none_when_no_match(self):
        resolver = EndpointResolver(self._endpoint_data())
        self.assertIsNone(resolver.construct_endpoint('foo', 'baz'))

    def test_constructs_regionalized_endpoints_for_exact_matches(self):
        resolver = EndpointResolver(self._endpoint_data())
        result = resolver.construct_endpoint('not-regionalized', 'eu-baz')
        self.assertEquals('not-regionalized.eu-baz.amazonaws.com',
                          result['hostname'])
        self.assertEquals('aws', result['partition'])
        self.assertEquals('eu-baz', result['endpointName'])

    def test_constructs_partition_endpoints_for_real_partition_region(self):
        resolver = EndpointResolver(self._endpoint_data())
        result = resolver.construct_endpoint('not-regionalized', 'us-bar')
        self.assertEquals('not-regionalized', result['hostname'])
        self.assertEquals('aws', result['partition'])
        self.assertEquals('aws', result['endpointName'])

    def test_constructs_partition_endpoints_for_regex_match(self):
        resolver = EndpointResolver(self._endpoint_data())
        result = resolver.construct_endpoint('not-regionalized', 'us-abc')
        self.assertEquals('not-regionalized', result['hostname'])

    def test_constructs_endpoints_for_regionalized_regex_match(self):
        resolver = EndpointResolver(self._endpoint_data())
        result = resolver.construct_endpoint('s3', 'us-abc')
        self.assertEquals('s3.us-abc.amazonaws.com', result['hostname'])

    def test_constructs_endpoints_for_unknown_service_but_known_region(self):
        resolver = EndpointResolver(self._endpoint_data())
        result = resolver.construct_endpoint('unknown', 'us-foo')
        self.assertEquals('unknown.us-foo.amazonaws.com', result['hostname'])

    def test_merges_service_keys(self):
        resolver = EndpointResolver(self._endpoint_data())
        us_foo = resolver.construct_endpoint('merge', 'us-foo')
        us_bar = resolver.construct_endpoint('merge', 'us-bar')
        self.assertEquals(['http'], us_foo['protocols'])
        self.assertEquals(['v4'], us_foo['signatureVersions'])
        self.assertEquals(['https'], us_bar['protocols'])
        self.assertEquals(['v2'], us_bar['signatureVersions'])

    def test_merges_partition_default_keys_with_no_overwrite(self):
        resolver = EndpointResolver(self._endpoint_data())
        resolved = resolver.construct_endpoint('ec2', 'foo-1')
        self.assertEquals('baz', resolved['foo'])
        self.assertEquals(['http'], resolved['protocols'])

    def test_merges_partition_default_keys_with_overwrite(self):
        resolver = EndpointResolver(self._endpoint_data())
        resolved = resolver.construct_endpoint('ec2', 'foo-2')
        self.assertEquals('bar', resolved['foo'])
        self.assertEquals(['http'], resolved['protocols'])

    def test_gives_hostname_and_common_name_unaltered(self):
        resolver = EndpointResolver(self._endpoint_data())
        result = resolver.construct_endpoint('s3', 'eu-baz')
        self.assertEquals('s3.eu-baz.amazonaws.com', result['sslCommonName'])
        self.assertEquals('foo', result['hostname'])

    def tests_uses_partition_endpoint_when_no_region_provided(self):
        resolver = EndpointResolver(self._endpoint_data())
        result = resolver.construct_endpoint('not-regionalized')
        self.assertEquals('not-regionalized', result['hostname'])
        self.assertEquals('aws', result['endpointName'])

    def test_returns_dns_suffix_if_available(self):
        resolver = EndpointResolver(self._endpoint_data())
        result = resolver.construct_endpoint('not-regionalized')
        self.assertEqual(result['dnsSuffix'], 'amazonaws.com')


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

    def test_get_endpoints_with_boto_format_data(self):
        boto_endpoints = {
            'ec2': {'mars-west-1': 'ec2.mars-west-1.amazonaws.com'}
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            boto_endpoint_data=boto_endpoints
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

    def test_get_all_regions_with_boto_format_data(self):
        boto_endpoints = {
            'ec2': {'mars-west-1': 'ec2.mars-west-1.amazonaws.com'}
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            boto_endpoint_data=boto_endpoints
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

    def test_construct_endpoint_with_boto_format_data(self):
        boto_endpoints = {
            'ec2': {'mars-west-1': 'ec2.mars-west-1.amazonaws.com'}
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            boto_endpoint_data=boto_endpoints
        )
        constructed_endpoint = resolver.construct_endpoint(
            'ec2', 'mars-west-1')
        expected_endpoint = {
            'endpointName': 'mars-west-1',
            'hostname': 'ec2.mars-west-1.amazonaws.com',
            'partition': 'aws'
        }
        self.assertEqual(constructed_endpoint, expected_endpoint)

    def test_boto_format_data_has_priority_in_construct_endpoint(self):
        boto_endpoints = {
            'ec2': {'us-foo': 'ec2.us-foo-3.amazonaws.com'}
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            boto_endpoint_data=boto_endpoints
        )
        constructed_endpoint = resolver.construct_endpoint('ec2', 'us-foo')
        expected_endpoint = {
            'endpointName': 'us-foo',
            'hostname': 'ec2.us-foo-3.amazonaws.com',
            'partition': 'aws'
        }
        self.assertEqual(constructed_endpoint, expected_endpoint)

    def test_get_available_services(self):
        resolver = BotoEndpointResolver(self._endpoint_data())
        services = sorted(resolver.get_available_services())
        expected_services = sorted([
            'ec2', 's3', 'not-regionalized', 'non-partition', 'merge'])
        self.assertEqual(services, expected_services)

    def test_get_available_services_with_extra_data(self):
        boto_endpoints = {
            'new-service': {
                'moon-darkside-1': 'new-service.moon-darkside-1.amazonaws.com'
            }
        }
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            boto_endpoint_data=boto_endpoints
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

    def test_is_global_endpoint(self):
        resolver = BotoEndpointResolver(self._endpoint_data())
        self.assertFalse(resolver.is_global_service('ec2'))
        self.assertFalse(resolver.is_global_service(
            'ec2', partition_name='foo'))
        self.assertTrue(resolver.is_global_service('not-regionalized'))
        self.assertTrue(resolver.is_global_service('non-partition'))

    def test_is_global_endpoint_with_renames(self):
        rename_map = {'ec3': 'ec2', 'nr': 'not-regionalized'}
        resolver = BotoEndpointResolver(
            endpoint_data=self._endpoint_data(),
            service_rename_map=rename_map
        )
        self.assertFalse(resolver.is_global_service('ec3'))
        self.assertTrue(resolver.is_global_service('nr'))

    def test_is_global_endpoint_in_invalid_partition(self):
        resolver = BotoEndpointResolver(self._endpoint_data())
        with self.assertRaises(ValueError):
            resolver.is_global_service('ec2', 'fake-partition')
