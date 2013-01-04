# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
import mock

from boto.glacier.job import Job
from boto.glacier.layer1 import Layer1
from boto.glacier.response import GlacierResponse
from boto.glacier.exceptions import TreeHashDoesNotMatchError


class TestJob(unittest.TestCase):
    def setUp(self):
        self.api = mock.Mock(spec=Layer1)
        self.vault = mock.Mock()
        self.vault.layer1 = self.api
        self.job = Job(self.vault)

    def test_get_job_validate_checksum_success(self):
        response = GlacierResponse(mock.Mock(), None)
        response['TreeHash'] = 'tree_hash'
        self.api.get_job_output.return_value = response
        with mock.patch('boto.glacier.job.tree_hash_from_str') as t:
            t.return_value = 'tree_hash'
            self.job.get_output(byte_range=(1, 1024), validate_checksum=True)

    def test_get_job_validation_fails(self):
        response = GlacierResponse(mock.Mock(), None)
        response['TreeHash'] = 'tree_hash'
        self.api.get_job_output.return_value = response
        with mock.patch('boto.glacier.job.tree_hash_from_str') as t:
            t.return_value = 'BAD_TREE_HASH_VALUE'
            with self.assertRaises(TreeHashDoesNotMatchError):
                # With validate_checksum set to True, this call fails.
                self.job.get_output(byte_range=(1, 1024), validate_checksum=True)
            # With validate_checksum set to False, this call succeeds.
            self.job.get_output(byte_range=(1, 1024), validate_checksum=False)


if __name__ == '__main__':
    unittest.main()
