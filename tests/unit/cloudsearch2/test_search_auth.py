#!/usr/bin env python

from tests.unit import AWSMockServiceTestCase

import json

from boto.cloudsearch2.layer1 import CloudSearchConnection
from boto.cloudsearch2.domain import Domain
from httpretty import HTTPretty

from boto.cloudsearch2.search import SearchConnection


SEARCH_SERVICE = "search-demo-userdomain.us-east-1.cloudsearch.amazonaws.com"
FULL_URL = 'http://%s/2013-01-01/search' % SEARCH_SERVICE


class CloudSearchSearchAuthTest(AWSMockServiceTestCase):
    connection_class = CloudSearchConnection

    domain = b"""{
        "SearchInstanceType": null,
        "DomainId": "1234567890/demo",
        "DomainName": "demo",
        "Deleted": false,
        "SearchInstanceCount": 0,
        "Created": true,
        "SearchService": {
          "Endpoint": "%s"
        },
        "RequiresIndexDocuments": false,
        "Processing": false,
        "DocService": {
          "Endpoint": "doc-demo.us-east-1.cloudsearch.amazonaws.com"
        },
        "ARN": "arn:aws:cs:us-east-1:1234567890:domain/demo",
        "SearchPartitionCount": 0
    }""" % SEARCH_SERVICE

    response = {
        'rank': '-text_relevance',
        'match-expr': "Test",
        'hits': {
            'found': 30,
            'start': 0,
            'hit': [
                {
                    'id': '12341',
                    'fields': {
                        'title': 'Document 1',
                        'rank': 1
                    }
                }
            ]
        },
        'status': {
            'rid': 'b7c167f6c2da6d93531b9a7b314ad030b3a74803b4b7797edb905ba5a6a08',
            'time-ms': 2,
            'cpu-time-ms': 0
        }
    }

    def setUp(self):
        HTTPretty.enable()
        HTTPretty.register_uri(
            HTTPretty.GET,
            FULL_URL,
            body=json.dumps(self.response).encode('utf-8'),
            content_type="application/json",
            status=200)
        super(CloudSearchSearchAuthTest, self).setUp()

    def tearDown(self):
        HTTPretty.disable()
        super(CloudSearchSearchAuthTest, self).tearDown()

    def test_search_with_auth(self):
        conn = self.service_connection
        domain = Domain(conn, json.loads(self.domain))
        search_service = domain.get_search_service()

        self.set_http_response(status_code=200, body=json.dumps(self.response))
        search_service.search(q='Test', options='TestOptions')

        headers = None
        if self.actual_request is not None:
            headers = self.actual_request.headers
        if headers is None:
            headers = HTTPretty.last_request.headers

        self.assertIsNotNone(headers.get('Authorization'))