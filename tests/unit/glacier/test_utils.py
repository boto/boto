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
from hashlib import sha256
from tests.unit import unittest

from boto.glacier import utils


class TestPartSizeCalculations(unittest.TestCase):
    def test_small_values_still_use_default_part_size(self):
        self.assertEqual(utils.minimum_part_size(1), 4 * 1024 * 1024)

    def test_under_the_maximum_value(self):
        # If we're under the maximum, we can use 4MB part sizes.
        self.assertEqual(utils.minimum_part_size(8 * 1024 * 1024),
                         4 * 1024 * 1024)

    def test_gigabyte_size(self):
        # If we're over the maximum default part size, we go up to the next
        # power of two until we find a part size that keeps us under 10,000
        # parts.
        self.assertEqual(utils.minimum_part_size(8 * 1024 * 1024 * 10000),
                         8 * 1024 * 1024)

    def test_terabyte_size(self):
        # For a 4 TB file we need at least a 512 MB part size.
        self.assertEqual(utils.minimum_part_size(4 * 1024 * 1024 * 1024 * 1024),
                         512 * 1024 * 1024)

    def test_file_size_too_large(self):
        with self.assertRaises(ValueError):
            utils.minimum_part_size((40000 * 1024 * 1024 * 1024) + 1)


class TestChunking(unittest.TestCase):
    def test_chunk_hashes_exact(self):
        chunks = utils.chunk_hashes('a' * (2 * 1024 * 1024))
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], sha256('a' * 1024 * 1024).digest())

    def test_chunks_with_leftovers(self):
        bytestring = 'a' * (2 * 1024 * 1024 + 20)
        chunks = utils.chunk_hashes(bytestring)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], sha256('a' * 1024 * 1024).digest())
        self.assertEqual(chunks[1], sha256('a' * 1024 * 1024).digest())
        self.assertEqual(chunks[2], sha256('a' * 20).digest())

    def test_less_than_one_chunk(self):
        chunks = utils.chunk_hashes('aaaa')
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], sha256('aaaa').digest())
