#!/usr/bin env python

from tests.unit import unittest
from httpretty import HTTPretty
import urlparse

import boto.cloudsearch
from boto.cloudsearch.domain import Domain

class CloudSearchConnectionTest(unittest.TestCase):

    def setUp(self):
        HTTPretty.enable()
        HTTPretty.register_uri(HTTPretty.POST, "https://cloudsearch.us-east-1.amazonaws.com/",
            body=CREATE_DOMAIN_XML,
            content_type="text/xml")

    def tearDown(self):
        HTTPretty.disable()

    def test_cloudsearch_connection(self):
        """Check that the correct arguments are sent to AWS when creating a cloudsearch connection"""
        conn = boto.cloudsearch.connect_to_region("us-east-1", aws_access_key_id='key_id', aws_secret_access_key='access_key')
        domain = Domain(conn, conn.create_domain('demo'))

        args = urlparse.parse_qs(HTTPretty.last_request.body)
        
        self.assertEqual(args['AWSAccessKeyId'], ['key_id'])
        self.assertEqual(args['Action'], ['CreateDomain'])
        self.assertEqual(args['DomainName'], ['demo'])

    def test_cloudsearch_connect_result_endpoints(self):
        """Check that endpoints & ARNs are correctly returned from AWS"""
        conn = boto.cloudsearch.connect_to_region("us-east-1", aws_access_key_id='key_id', aws_secret_access_key='access_key')
        domain = Domain(conn, conn.create_domain('demo'))

        self.assertEqual(domain.doc_service_arn, "arn:aws:cs:us-east-1:1234567890:doc/demo")
        self.assertEqual(domain.doc_service_endpoint, "doc-demo-userdomain.us-east-1.cloudsearch.amazonaws.com")
        self.assertEqual(domain.search_service_arn, "arn:aws:cs:us-east-1:1234567890:search/demo")
        self.assertEqual(domain.search_service_endpoint, "search-demo-userdomain.us-east-1.cloudsearch.amazonaws.com")

    def test_cloudsearch_connect_result_statuses(self):
        """Check that domain statuses are correctly returned from AWS"""
        conn = boto.cloudsearch.connect_to_region("us-east-1", aws_access_key_id='key_id', aws_secret_access_key='access_key')
        domain = Domain(conn, conn.create_domain('demo'))

        self.assertEqual(domain.created, True)
        self.assertEqual(domain.processing, False)
        self.assertEqual(domain.requires_index_documents, False)

    def test_cloudsearch_connect_result_details(self):
        """Check that the domain information is correctly returned from AWS"""
        conn = boto.cloudsearch.connect_to_region("us-east-1", aws_access_key_id='key_id', aws_secret_access_key='access_key')
        domain = Domain(conn, conn.create_domain('demo'))

        self.assertEqual(domain.id, "1234567890/demo")
        self.assertEqual(domain.name, "demo")

    def test_cloudsearch_connect_to_invalid_region(self):
        conn = boto.cloudsearch.connect_to_region("missing-region", aws_access_key_id='key_id', aws_secret_access_key='access_key')

        self.assertEqual(conn, None)

    def test_cloudsearch_documentservice_creation(self):
        conn = boto.cloudsearch.connect_to_region("us-east-1", aws_access_key_id='key_id', aws_secret_access_key='access_key')
        domain = Domain(conn, conn.create_domain('demo'))

        document = domain.get_document_service()

        self.assertEqual(document.endpoint, "doc-demo-userdomain.us-east-1.cloudsearch.amazonaws.com")

    def test_cloudsearch_searchservice_creation(self):
        conn = boto.cloudsearch.connect_to_region("us-east-1", aws_access_key_id='key_id', aws_secret_access_key='access_key')
        domain = Domain(conn, conn.create_domain('demo'))

        search = domain.get_search_service()

        self.assertEqual(search.endpoint, "search-demo-userdomain.us-east-1.cloudsearch.amazonaws.com")



# Sample dummy reply used to mock the standard AWS reply
CREATE_DOMAIN_XML="""
<CreateDomainResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
  <CreateDomainResult>
    <DomainStatus>
      <SearchPartitionCount>0</SearchPartitionCount>
      <SearchService>
        <Arn>arn:aws:cs:us-east-1:1234567890:search/demo</Arn>
        <Endpoint>search-demo-userdomain.us-east-1.cloudsearch.amazonaws.com</Endpoint>
      </SearchService>
      <NumSearchableDocs>0</NumSearchableDocs>
      <Created>true</Created>
      <DomainId>1234567890/demo</DomainId>
      <Processing>false</Processing>
      <SearchInstanceCount>0</SearchInstanceCount>
      <DomainName>demo</DomainName>
      <RequiresIndexDocuments>false</RequiresIndexDocuments>
      <Deleted>false</Deleted>
      <DocService>
        <Arn>arn:aws:cs:us-east-1:1234567890:doc/demo</Arn>
        <Endpoint>doc-demo-userdomain.us-east-1.cloudsearch.amazonaws.com</Endpoint>
      </DocService>
    </DomainStatus>
  </CreateDomainResult>
  <ResponseMetadata>
    <RequestId>00000000-0000-0000-0000-000000000000</RequestId>
  </ResponseMetadata>
</CreateDomainResponse>
"""

