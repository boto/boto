import mock
from boto.compat import json
from tests.unit import unittest

from .test_search import HOSTNAME, CloudSearchSearchBaseTest
from boto.cloudsearch.search import SearchConnection, SearchServiceException


def fake_loads_value_error(content, *args, **kwargs):
    """Callable to generate a fake ValueError"""
    raise ValueError("HAHAHA! Totally not simplejson & you gave me bad JSON.")


def fake_loads_json_error(content, *args, **kwargs):
    """Callable to generate a fake JSONDecodeError"""
    raise json.JSONDecodeError('Using simplejson & you gave me bad JSON.',
                               '', 0)


class CloudSearchJSONExceptionTest(CloudSearchSearchBaseTest):
    response = '{}'

    def test_no_simplejson_value_error(self):
        with mock.patch.object(json, 'loads', fake_loads_value_error):
            search = SearchConnection(endpoint=HOSTNAME)

            try:
                search.search(q='test')
                self.fail('This should never run!')
            except SearchServiceException, err:
                self.assertTrue('non-json' in str(err))

    @unittest.skipUnless(hasattr(json, 'JSONDecodeError'),
                         'requires simplejson')
    def test_simplejson_jsondecodeerror(self):
        with mock.patch.object(json, 'loads', fake_loads_json_error):
            search = SearchConnection(endpoint=HOSTNAME)

            try:
                search.search(q='test')
                self.fail('This should never run!')
            except SearchServiceException, err:
                self.assertTrue('non-json' in str(err))
