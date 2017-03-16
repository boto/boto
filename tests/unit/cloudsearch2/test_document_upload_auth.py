#!/usr/bin env python

from tests.unit import AWSMockServiceTestCase

import json

from boto.cloudsearch2.layer1 import CloudSearchConnection
from boto.cloudsearch2.domain import Domain
from httpretty import HTTPretty


DOC_SERVICE = "doc-demo-userdomain.us-east-1.cloudsearch.amazonaws.com"
FULL_URL = "http://%s/2013-01-01/documents/batch" % DOC_SERVICE


class CloudSearchDocumentUploadAuthTest(AWSMockServiceTestCase):
    connection_class = CloudSearchConnection

    domain = b"""{
        "SearchInstanceType": null,
        "DomainId": "1234567890/demo",
        "DomainName": "demo",
        "Deleted": false,
        "SearchInstanceCount": 0,
        "Created": true,
        "SearchService": {
          "Endpoint": "search-demo.us-east-1.cloudsearch.amazonaws.com"
        },
        "RequiresIndexDocuments": false,
        "Processing": false,
        "DocService": {
          "Endpoint": "%s"
        },
        "ARN": "arn:aws:cs:us-east-1:1234567890:domain/demo",
        "SearchPartitionCount": 0
    }""" % DOC_SERVICE

    response = {'status': 'success',
                'adds': 1,
                'deletes': 0,
                }

    def setUp(self):
        HTTPretty.enable()
        HTTPretty.register_uri(
            HTTPretty.POST,
            FULL_URL,
            body=json.dumps(self.response).encode('utf-8'),
            content_type="application/json",
            status=200)
        super(CloudSearchDocumentUploadAuthTest, self).setUp()

    def tearDown(self):
        HTTPretty.disable()
        super(CloudSearchDocumentUploadAuthTest, self).setUp()

    def test_upload_document_with_auth(self):
        conn = self.service_connection
        domain = Domain(conn, json.loads(self.domain))
        document_service = domain.get_document_service()
        document_service.add("1234", {"id": "1234", "title": "Title 1",
                              "category": ["cat_a", "cat_b", "cat_c"]})

        self.set_http_response(status_code=200, body=json.dumps(self.response))
        document_service.commit()

        headers = None
        if self.actual_request is not None:
            headers = self.actual_request.headers
        if headers is None:
            headers = HTTPretty.last_request.headers

        self.assertIsNotNone(headers.get('Authorization'))