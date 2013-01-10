from hashlib import sha256

from tests.unit import unittest
import mock

from boto.glacier.writer import Writer, chunk_hashes


class TestChunking(unittest.TestCase):
    def test_chunk_hashes_exact(self):
        chunks = chunk_hashes('a' * (2 * 1024 * 1024))
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], sha256('a' * 1024 * 1024).digest())

    def test_chunks_with_leftovers(self):
        bytestring = 'a' * (2 * 1024 * 1024 + 20)
        chunks = chunk_hashes(bytestring)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], sha256('a' * 1024 * 1024).digest())
        self.assertEqual(chunks[1], sha256('a' * 1024 * 1024).digest())
        self.assertEqual(chunks[2], sha256('a' * 20).digest())

    def test_less_than_one_chunk(self):
        chunks = chunk_hashes('aaaa')
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], sha256('aaaa').digest())
