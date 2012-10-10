# -*- coding: utf-8 -*-
# Copyright (c) 2012 Thomas Parslow http://almostobsolete.net/
# Copyright (c) 2012 Robie Basak <robie@justgohome.co.uk>
# Tree hash implementation from Aaron Brady bradya@gmail.com
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

import hashlib
import math


_ONE_MEGABYTE = 1024 * 1024


def chunk_hashes(bytestring, chunk_size=_ONE_MEGABYTE):
    chunk_count = int(math.ceil(len(bytestring) / float(chunk_size)))
    hashes = []
    for i in xrange(chunk_count):
        start = i * chunk_size
        end = (i + 1) * chunk_size
        hashes.append(hashlib.sha256(bytestring[start:end]).digest())
    return hashes


def tree_hash(fo):
    """
    Given a hash of each 1MB chunk (from chunk_hashes) this will hash
    together adjacent hashes until it ends up with one big one. So a
    tree of hashes.
    """
    hashes = []
    hashes.extend(fo)
    while len(hashes) > 1:
        new_hashes = []
        while True:
            if len(hashes) > 1:
                first = hashes.pop(0)
                second = hashes.pop(0)
                new_hashes.append(hashlib.sha256(first + second).digest())
            elif len(hashes) == 1:
                only = hashes.pop(0)
                new_hashes.append(only)
            else:
                break
        hashes.extend(new_hashes)
    return hashes[0]


def compute_hashes_from_fileobj(fileobj, chunk_size=1024 * 1024):
    """Compute the linear and tree hash from a fileobj.

    This function will compute the linear/tree hash of a fileobj
    in a single pass through the fileobj.

    :param fileobj: A file like object.

    :param chunk_size: The size of the chunks to use for the tree
        hash.  This is also the buffer size used to read from
        `fileobj`.

    :rtype: tuple
    :return: A tuple of (linear_hash, tree_hash).  Both hashes
        are returned in hex.

    """
    linear_hash = hashlib.sha256()
    chunks = []
    chunk = fileobj.read(chunk_size)
    while chunk:
        linear_hash.update(chunk)
        chunks.append(hashlib.sha256(chunk).digest())
        chunk = fileobj.read(chunk_size)
    return linear_hash.hexdigest(), bytes_to_hex(tree_hash(chunks))


def bytes_to_hex(str):
    return ''.join(["%02x" % ord(x) for x in str]).strip()


class _Partitioner(object):
    """Convert variable-size writes into part-sized writes

    Call write(data) with variable sized data as needed to write all data. Call
    flush() after all data is written.

    This instance will call send_fn(part_data) as needed in part_size pieces,
    except for the final part which may be shorter than part_size. Make sure to
    call flush() to ensure that a short final part results in a final send_fn
    call.

    """
    def __init__(self, part_size, send_fn):
        self.part_size = part_size
        self.send_fn = send_fn
        self._buffer = []
        self._buffer_size = 0

    def write(self, data):
        if data == '':
            return
        self._buffer.append(data)
        self._buffer_size += len(data)
        while self._buffer_size > self.part_size:
            self._send_part()

    def _send_part(self):
        data = ''.join(self._buffer)
        # Put back any data remaining over the part size into the
        # buffer
        if len(data) > self.part_size:
            self._buffer = [data[self.part_size:]]
            self._buffer_size = len(self._buffer[0])
        else:
            self._buffer = []
            self._buffer_size = 0
        # The part we will send
        part = data[:self.part_size]
        self.send_fn(part)

    def flush(self):
        if self._buffer_size > 0:
            self._send_part()


class _Uploader(object):
    """Upload to a Glacier upload_id.

    Call upload_part for each part (in any order) and then close to complete
    the upload.

    """
    def __init__(self, vault, upload_id, part_size, chunk_size=_ONE_MEGABYTE):
        self.vault = vault
        self.upload_id = upload_id
        self.part_size = part_size
        self.chunk_size = chunk_size

        self._uploaded_size = 0
        self._tree_hashes = []

        self.closed = False

    def _insert_tree_hash(self, index, tree_hash):
        list_length = len(self._tree_hashes)
        if index >= list_length:
            self._tree_hashes.extend([None] * (list_length - index + 1))
        self._tree_hashes[index] = tree_hash

    def upload_part(self, part_index, part_data):
        """Upload a part to Glacier.

        :param part_index: part number where 0 is the first part
        :param part_data: data to upload corresponding to this part

        """
        if self.closed:
            raise ValueError("I/O operation on closed file")
        # Create a request and sign it
        part_tree_hash = tree_hash(chunk_hashes(part_data, self.chunk_size))
        self._insert_tree_hash(part_index, part_tree_hash)

        hex_tree_hash = bytes_to_hex(part_tree_hash)
        linear_hash = hashlib.sha256(part_data).hexdigest()
        start = self.part_size * part_index
        content_range = (start,
                         (start + len(part_data)) - 1)
        response = self.vault.layer1.upload_part(self.vault.name,
                                                 self.upload_id,
                                                 linear_hash,
                                                 hex_tree_hash,
                                                 content_range, part_data)
        response.read()
        self._uploaded_size += len(part_data)

    def close(self):
        if self.closed:
            return
        if None in self._tree_hashes:
            raise RuntimeError("Some parts were not uploaded.")
        # Complete the multiplart glacier upload
        hex_tree_hash = bytes_to_hex(tree_hash(self._tree_hashes))
        response = self.vault.layer1.complete_multipart_upload(self.vault.name,
                                                               self.upload_id,
                                                               hex_tree_hash,
                                                               self._uploaded_size)
        self.archive_id = response['ArchiveId']
        self.closed = True


class Writer(object):
    """
    Presents a file-like object for writing to a Amazon Glacier
    Archive. The data is written using the multi-part upload API.
    """
    def __init__(self, vault, upload_id, part_size, chunk_size=_ONE_MEGABYTE):
        self.uploader = _Uploader(vault, upload_id, part_size, chunk_size)
        self.partitioner = _Partitioner(part_size, self._upload_part)
        self.closed = False
        self.next_part_index = 0

    def write(self, data):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        self.partitioner.write(data)

    def _upload_part(self, part_data):
        self.uploader.upload_part(self.next_part_index, part_data)
        self.next_part_index += 1

    def close(self):
        if self.closed:
            return
        self.partitioner.flush()
        self.uploader.close()
        self.closed = True

    def get_archive_id(self):
        self.close()
        return self.uploader.archive_id

    @property
    def upload_id(self):
        return self.uploader.upload_id

    @property
    def vault(self):
        return self.uploader.vault
