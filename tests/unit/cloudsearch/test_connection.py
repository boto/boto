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
            body=self.response,
            content_type="text/xml")

    def tearDown(self):
        HTTPretty.disable()

class CloudSearchConnectionCreationTest(CloudSearchConnectionTest):
    response = """
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
        self.assertEqual(domain.deleted, False)

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

class CloudSearchConnectionDeletionTest(CloudSearchConnectionTest):
    response = """
<DeleteDomainResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
  <DeleteDomainResult>
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
  </DeleteDomainResult>
  <ResponseMetadata>
    <RequestId>00000000-0000-0000-0000-000000000000</RequestId>
  </ResponseMetadata>
</DeleteDomainResponse>
"""

    def test_cloudsearch_deletion(self):
        """Check that the correct arguments are sent to AWS when creating a cloudsearch connection"""
        conn = boto.cloudsearch.connect_to_region("us-east-1", aws_access_key_id='key_id', aws_secret_access_key='access_key')
        conn.delete_domain('demo')

        args = urlparse.parse_qs(HTTPretty.last_request.body)
        
        self.assertEqual(args['AWSAccessKeyId'], ['key_id'])
        self.assertEqual(args['Action'], ['DeleteDomain'])
        self.assertEqual(args['DomainName'], ['demo'])

class CloudSearchConnectionIndexDocumentTest(CloudSearchConnectionTest):
    response = """
<IndexDocumentsResponse xmlns="http://cloudsearch.amazonaws.com/doc/2011-02-01">
  <IndexDocumentsResult>
    <FieldNames>
      <member>average_score</member>
      <member>brand_id</member>
      <member>colors</member>
      <member>context</member>
      <member>context_owner</member>
      <member>created_at</member>
      <member>creator_id</member>
      <member>description</member>
      <member>file_size</member>
      <member>format</member>
      <member>has_logo</member>
      <member>has_messaging</member>
      <member>height</member>
      <member>image_id</member>
      <member>ingested_from</member>
      <member>is_advertising</member>
      <member>is_photo</member>
      <member>is_reviewed</member>
      <member>modified_at</member>
      <member>subject_date</member>
      <member>tags</member>
      <member>title</member>
      <member>width</member>
    </FieldNames>
  </IndexDocumentsResult>
  <ResponseMetadata>
    <RequestId>eb2b2390-6bbd-11e2-ab66-93f3a90dcf2a</RequestId>
  </ResponseMetadata>
</IndexDocumentsResponse>
"""

    def test_cloudsearch_index_documents(self):
        """Check that the correct arguments are sent to AWS when indexing a domain"""
        conn = boto.cloudsearch.connect_to_region("us-east-1", aws_access_key_id='key_id', aws_secret_access_key='access_key')
        conn.index_documents('demo')

        args = urlparse.parse_qs(HTTPretty.last_request.body)
        
        self.assertEqual(args['AWSAccessKeyId'], ['key_id'])
        self.assertEqual(args['Action'], ['IndexDocuments'])
        self.assertEqual(args['DomainName'], ['demo'])

    def test_cloudsearch_index_documents_resp(self):
        """Check that the AWS response is being parsed correctly when indexing a domain"""
        conn = boto.cloudsearch.connect_to_region("us-east-1", aws_access_key_id='key_id', aws_secret_access_key='access_key')
        results = conn.index_documents('demo')

        self.assertEqual(results, ['average_score', 'brand_id', 'colors', 'context', 'context_owner', 'created_at', 'creator_id', 'description', 'file_size', 'format', 'has_logo', 'has_messaging', 'height', 'image_id', 'ingested_from', 'is_advertising', 'is_photo', 'is_reviewed', 'modified_at', 'subject_date', 'tags', 'title', 'width'])

