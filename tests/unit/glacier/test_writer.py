from hashlib import sha256
import itertools

from tests.unit import unittest
from mock import (
    call,
    Mock,
    patch,
    sentinel,
)

from boto.glacier.layer1 import Layer1
from boto.glacier.vault import Vault
from boto.glacier.writer import (
    bytes_to_hex,
    chunk_hashes,
    tree_hash,
    Writer,
)


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

class TestWriter(unittest.TestCase):
    def setUp(self):
        super(TestWriter, self).setUp()
        self.vault = Mock(spec=Vault)
        self.vault.layer1 = Mock(spec=Layer1)
        self.vault.layer1.complete_multipart_upload.return_value = dict(
            ArchiveId=sentinel.archive_id)
        self.vault.name = sentinel.vault_name
        upload_id = sentinel.upload_id
        self.chunk_size = 2 # power of 2
        self.part_size = 4 # power of 2
        self.writer = Writer(
            self.vault, upload_id, self.part_size, self.chunk_size)

    @staticmethod
    def partify(data, part_size):
        for start in itertools.count(0, part_size):
            part = data[start:start+part_size]
            if part:
                yield part
            else:
                return

    def check_write(self, write_list):
        for write_data in write_list:
            self.writer.write(write_data)
        self.writer.close()

        data = ''.join(write_list)

        upload_part_calls = []
        data_tree_hashes = []
        for i, data_part in enumerate(self.partify(data, self.part_size)):
            start = i * self.part_size
            end = start + len(data_part)
            data_part_tree_hash_blob = tree_hash(
                chunk_hashes(data_part, self.chunk_size))
            data_part_tree_hash = bytes_to_hex(data_part_tree_hash_blob)
            data_part_linear_hash = sha256(data_part).hexdigest()
            upload_part_calls.append(
                call.layer1.upload_part(
                    sentinel.vault_name, sentinel.upload_id,
                    data_part_linear_hash, data_part_tree_hash,
                    (start, end - 1), data_part))
            data_tree_hashes.append(data_part_tree_hash_blob)

        self.vault.layer1.upload_part.assert_has_calls(
            upload_part_calls, any_order=True)
        self.assertEquals(
            len(upload_part_calls), self.vault.layer1.upload_part.call_count)

        data_tree_hash = bytes_to_hex(tree_hash(data_tree_hashes))
        self.vault.layer1.complete_multipart_upload.assert_called_once_with(
            sentinel.vault_name, sentinel.upload_id, data_tree_hash, len(data))

    def test_single_byte_write(self):
        self.check_write(['1'])

    def test_one_part_write(self):
        self.check_write(['1234'])

    def test_split_write_1(self):
        self.check_write(['1', '234'])

    def test_split_write_2(self):
        self.check_write(['12', '34'])

    def test_split_write_3(self):
        self.check_write(['123', '4'])

    def test_one_part_plus_one_write(self):
        self.check_write(['12345'])

    def test_returns_archive_id(self):
        self.writer.write('1')
        self.writer.close()
        self.assertEquals(sentinel.archive_id, self.writer.get_archive_id())

    def test_upload_id(self):
        self.assertEquals(sentinel.upload_id, self.writer.upload_id)
