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

from boto.glacier import connect_to_region
import uuid
import unittest

class GlaicerTest (unittest.TestCase):
    glacier = True

    def setUp(self):
        self.conn = connect_to_region("us-east-1")
        self.vault_name = 'boto-test-vault-%s' % (uuid.uuid1(),)
        self.conn.create_vault(self.vault_name)
        self.vault = self.conn.get_vault(self.vault_name)

    def tearDown(self):
        self.vault.delete()


    def test_vault_name(self):
        assert self.vault.name == self.vault_name

    ## Once you write to a vault you can't delete it for a few hours,
    ## so this test doesn't work so well.
    # def test_upload_vault(self):
    #     writer = self.vault.create_archive_writer(description="Hello world")
    #     # Would be nicer to write enough to splill over into a second
    #     # part, but that takes ages!
    #     for i in range(12):
    #         writer.write("X" * 1024)
    #     writer.close()
    #     archive_id = writer.get_archive_id()

    #     job_id = self.vault.retrieve_archive(archive_id, description="my job")

    #     # Usually at this point you;d wait for the notification via
    #     # SNS (which takes about 5 hours)

    #     job = self.vault.get_job(job_id)
    #     assert job.description == "my job"
    #     assert job.archive_size == 1024*12

    #     self.vault.delete_archive(archive_id)
