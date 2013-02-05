#!/usr/bin/env python
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
import unittest
from cStringIO import StringIO

import mock
from mock import ANY

from boto.glacier import vault


class TestVault(unittest.TestCase):
    def setUp(self):
        self.size_patch = mock.patch('os.path.getsize')
        self.getsize = self.size_patch.start()
        self.api = mock.Mock()
        self.vault = vault.Vault(self.api, None)
        self.vault.name = 'myvault'
        self.mock_open = mock.mock_open()
        stringio = StringIO('content')
        self.mock_open.return_value.read = stringio.read

    def tearDown(self):
        self.size_patch.stop()

    def test_upload_archive_small_file(self):
        self.getsize.return_value = 1

        self.api.upload_archive.return_value = {'ArchiveId': 'archive_id'}
        with mock.patch('boto.glacier.vault.open', self.mock_open,
                        create=True):
            archive_id = self.vault.upload_archive(
                'filename', 'my description')
        self.assertEqual(archive_id, 'archive_id')
        self.api.upload_archive.assert_called_with(
            'myvault', self.mock_open.return_value,
            mock.ANY, mock.ANY, 'my description')

    def test_small_part_size_is_obeyed(self):
        self.vault.DefaultPartSize = 2 * 1024 * 1024
        self.vault.create_archive_writer = mock.Mock()

        self.getsize.return_value = 1

        with mock.patch('boto.glacier.vault.open', self.mock_open,
                        create=True):
            self.vault.create_archive_from_file('myfile')
        # The write should be created with the default part size of the
        # instance (2 MB).
        self.vault.create_archive_writer.assert_called_with(
                description=mock.ANY, part_size=self.vault.DefaultPartSize)

    def test_large_part_size_is_obeyed(self):
        self.vault.DefaultPartSize = 8 * 1024 * 1024
        self.vault.create_archive_writer = mock.Mock()
        self.getsize.return_value = 1
        with mock.patch('boto.glacier.vault.open', self.mock_open,
                        create=True):
            self.vault.create_archive_from_file('myfile')
        # The write should be created with the default part size of the
        # instance (8 MB).
        self.vault.create_archive_writer.assert_called_with(
            description=mock.ANY, part_size=self.vault.DefaultPartSize)


class TestConcurrentUploads(unittest.TestCase):

    def test_concurrent_upload_file(self):
        v = vault.Vault(None, None)
        with mock.patch('boto.glacier.vault.ConcurrentUploader') as c:
            c.return_value.upload.return_value = 'archive_id'
            archive_id = v.concurrent_create_archive_from_file(
                'filename', 'my description')
            c.return_value.upload.assert_called_with('filename',
                                                     'my description')
        self.assertEqual(archive_id, 'archive_id')


if __name__ == '__main__':
    unittest.main()
