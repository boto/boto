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

    def tearDown(self):
        self.size_patch.stop()

    def test_upload_archive_small_file(self):
        api = mock.Mock()
        v = vault.Vault(api, None)
        v.name = 'myvault'
        self.getsize.return_value = 1
        stringio = StringIO('content')
        m = mock.mock_open()
        m.return_value.read = stringio.read

        api.upload_archive.return_value = {'ArchiveId': 'archive_id'}
        with mock.patch('boto.glacier.vault.open', m, create=True):
            archive_id = v.upload_archive('filename', 'my description')
        self.assertEqual(archive_id, 'archive_id')
        api.upload_archive.assert_called_with('myvault', m.return_value, ANY,
                                              ANY, 'my description')


if __name__ == '__main__':
    unittest.main()
