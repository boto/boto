import json
import copy
import tempfile

from tests.unit import AWSMockServiceTestCase
from boto.glacier.layer1 import Layer1


class GlacierLayer1ConnectionBase(AWSMockServiceTestCase):
    connection_class = Layer1

    def setUp(self):
        super(GlacierLayer1ConnectionBase, self).setUp()
        self.json_header = [('Content-Type', 'application/json')]
        self.vault_name = u'examplevault'
        self.vault_arn = 'arn:aws:glacier:us-east-1:012345678901:vaults/' + \
                          self.vault_name
        self.vault_info = {u'CreationDate': u'2012-03-16T22:22:47.214Z',
                           u'LastInventoryDate': u'2012-03-21T22:06:51.218Z',
                           u'NumberOfArchives': 2,
                           u'SizeInBytes': 12334,
                           u'VaultARN': self.vault_arn,
                           u'VaultName': self.vault_name}


class GlacierVaultsOperations(GlacierLayer1ConnectionBase):

    def test_create_vault_parameters(self):
        self.set_http_response(status_code=201)
        self.service_connection.create_vault(self.vault_name)

    def test_list_vaults(self):
        content = {u'Marker': None,
                   u'RequestId': None,
                   u'VaultList': [self.vault_info]}
        self.set_http_response(status_code=200, header=self.json_header,
                               body=json.dumps(content))
        api_response = self.service_connection.list_vaults()
        self.assertDictEqual(content, api_response)

    def test_describe_vaults(self):
        content = copy.copy(self.vault_info)
        content[u'RequestId'] = None
        self.set_http_response(status_code=200, header=self.json_header,
                               body=json.dumps(content))
        api_response = self.service_connection.describe_vault(self.vault_name)
        self.assertDictEqual(content, api_response)

    def test_delete_vault(self):
        self.set_http_response(status_code=204)
        self.service_connection.delete_vault(self.vault_name)


class GlacierJobOperations(GlacierLayer1ConnectionBase):

    def setUp(self):
        super(GlacierJobOperations, self).setUp()
        self.job_content = 'abc' * 1024

    def test_initiate_archive_job(self):
        content = {u'Type': u'archive-retrieval',
                   u'ArchiveId': u'AAABZpJrTyioDC_HsOmHae8EZp_uBSJr6cnGOLKp_XJCl-Q',
                   u'Description': u'Test Archive',
                   u'SNSTopic': u'Topic',
                   u'JobId': None,
                   u'Location': None,
                   u'RequestId': None}
        self.set_http_response(status_code=202, header=self.json_header,
                               body=json.dumps(content))
        api_response = self.service_connection.initiate_job(self.vault_name,
                                                            self.job_content)
        self.assertDictEqual(content, api_response)

    def test_get_archive_output(self):
        header = [('Content-Type', 'application/octet-stream')]
        self.set_http_response(status_code=200, header=header,
                               body=self.job_content)
        response = self.service_connection.get_job_output(self.vault_name,
                                                         'example-job-id')
        self.assertEqual(self.job_content, response.read())


class GlacierUploadArchiveResets(GlacierLayer1ConnectionBase):
    def test_upload_archive(self):
        fake_data = tempfile.NamedTemporaryFile()
        fake_data.write('foobarbaz')
        # First seek to a non zero offset.
        fake_data.seek(2)
        self.set_http_response(status_code=201)
        # Simulate reading the request body when we send the request.
        self.service_connection.connection.request.side_effect = \
                lambda *args: fake_data.read()
        self.service_connection.upload_archive('vault_name', fake_data, 'linear_hash',
                                               'tree_hash')
        # Verify that we seek back to the original offset after making
        # a request.  This ensures that if we need to resend the request we're
        # back at the correct location within the file.
        self.assertEqual(fake_data.tell(), 2)
