# -*- coding: utf-8 -*-
# Copyright (c) 2012 Thomas Parslow http://almostobsolete.net/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#

from tests.unit import unittest

from mock import Mock

from boto.glacier.layer1 import Layer1
from boto.glacier.layer2 import Layer2
from boto.glacier.vault import Vault
from boto.glacier.vault import Job

# Some fixture data from the Glacier docs
FIXTURE_VAULT = {
  "CreationDate" : "2012-02-20T17:01:45.198Z",
  "LastInventoryDate" : "2012-03-20T17:03:43.221Z",
  "NumberOfArchives" : 192,
  "SizeInBytes" : 78088912,
  "VaultARN" : "arn:aws:glacier:us-east-1:012345678901:vaults/examplevault",
  "VaultName" : "examplevault"
}

FIXTURE_ARCHIVE_JOB = {
  "Action": "ArchiveRetrieval",
  "ArchiveId": ("NkbByEejwEggmBz2fTHgJrg0XBoDfjP4q6iu87-TjhqG6eGoOY9Z8i1_AUyUs"
                "uhPAdTqLHy8pTl5nfCFJmDl2yEZONi5L26Omw12vcs01MNGntHEQL8MBfGlqr"
                "EXAMPLEArchiveId"),
  "ArchiveSizeInBytes": 16777216,
  "Completed": False,
  "CreationDate": "2012-05-15T17:21:39.339Z",
  "CompletionDate": "2012-05-15T17:21:43.561Z",
  "InventorySizeInBytes": None,
  "JobDescription": "My ArchiveRetrieval Job",
  "JobId": ("HkF9p6o7yjhFx-K3CGl6fuSm6VzW9T7esGQfco8nUXVYwS0jlb5gq1JZ55yHgt5v"
            "P54ZShjoQzQVVh7vEXAMPLEjobID"),
  "SHA256TreeHash": ("beb0fe31a1c7ca8c6c04d574ea906e3f97b31fdca7571defb5b44dc"
                     "a89b5af60"),
  "SNSTopic": "arn:aws:sns:us-east-1:012345678901:mytopic",
  "StatusCode": "InProgress",
  "StatusMessage": "Operation in progress.",
  "VaultARN": "arn:aws:glacier:us-east-1:012345678901:vaults/examplevault"
}


class GlacierLayer2Base(unittest.TestCase):
    def setUp(self):
        self.mock_layer1 = Mock(spec=Layer1)


class TestGlacierLayer2Connection(GlacierLayer2Base):
    def setUp(self):
        GlacierLayer2Base.setUp(self)
        self.layer2 = Layer2(layer1=self.mock_layer1)

    def test_create_vault(self):
        self.mock_layer1.describe_vault.return_value = FIXTURE_VAULT
        self.layer2.create_vault("My Vault")
        self.mock_layer1.create_vault.assert_called_with("My Vault")

    def test_get_vault(self):
        self.mock_layer1.describe_vault.return_value = FIXTURE_VAULT
        vault = self.layer2.get_vault("examplevault")
        self.assertEqual(vault.layer1, self.mock_layer1)
        self.assertEqual(vault.name, "examplevault")
        self.assertEqual(vault.size, 78088912)
        self.assertEqual(vault.number_of_archives, 192)

    def list_vaults(self):
        self.mock_layer1.list_vaults.return_value = [FIXTURE_VAULT]
        vaults = self.layer2.list_vaults()
        self.assertEqual(vaults[0].name, "examplevault")


class TestVault(GlacierLayer2Base):
    def setUp(self):
        GlacierLayer2Base.setUp(self)
        self.vault = Vault(self.mock_layer1, FIXTURE_VAULT)

    # TODO: Tests for the other methods of uploading

    def test_create_archive_writer(self):
        self.mock_layer1.initiate_multipart_upload.return_value = {
            "UploadId": "UPLOADID"}
        writer = self.vault.create_archive_writer(description="stuff")
        self.mock_layer1.initiate_multipart_upload.assert_called_with(
            "examplevault", self.vault.DefaultPartSize, "stuff")
        self.assertEqual(writer.vault, self.vault)
        self.assertEqual(writer.upload_id, "UPLOADID")

    def test_delete_vault(self):
        self.vault.delete_archive("archive")
        self.mock_layer1.delete_archive.assert_called_with("examplevault",
                                                           "archive")

    def test_get_job(self):
        self.mock_layer1.describe_job.return_value = FIXTURE_ARCHIVE_JOB
        job = self.vault.get_job(
            "NkbByEejwEggmBz2fTHgJrg0XBoDfjP4q6iu87-TjhqG6eGoOY9Z8i1_AUyUsuhPA"
            "dTqLHy8pTl5nfCFJmDl2yEZONi5L26Omw12vcs01MNGntHEQL8MBfGlqrEXAMPLEA"
            "rchiveId")
        self.assertEqual(job.action, "ArchiveRetrieval")

    def test_list_jobs(self):
        self.mock_layer1.list_jobs.return_value = {
            "JobList": [FIXTURE_ARCHIVE_JOB]}
        jobs = self.vault.list_jobs(False, "InProgress")
        self.mock_layer1.list_jobs.assert_called_with("examplevault",
                                                      False, "InProgress")
        self.assertEqual(jobs[0].archive_id,
                         "NkbByEejwEggmBz2fTHgJrg0XBoDfjP4q6iu87-TjhqG6eGoOY9Z"
                         "8i1_AUyUsuhPAdTqLHy8pTl5nfCFJmDl2yEZONi5L26Omw12vcs0"
                         "1MNGntHEQL8MBfGlqrEXAMPLEArchiveId")


class TestJob(GlacierLayer2Base):
    def setUp(self):
        GlacierLayer2Base.setUp(self)
        self.vault = Vault(self.mock_layer1, FIXTURE_VAULT)
        self.job = Job(self.vault, FIXTURE_ARCHIVE_JOB)

    def test_get_job_output(self):
        self.mock_layer1.get_job_output.return_value = "TEST_OUTPUT"
        self.job.get_output((0,100))
        self.mock_layer1.get_job_output.assert_called_with(
            "examplevault",
            "HkF9p6o7yjhFx-K3CGl6fuSm6VzW9T7esGQfco8nUXVYwS0jlb5gq1JZ55yHgt5vP"
            "54ZShjoQzQVVh7vEXAMPLEjobID", (0,100))
