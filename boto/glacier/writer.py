# -*- coding: utf-8 -*-
# Copyright (c) 2012 Thomas Parslow http://almostobsolete.net/
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

import urllib
import hashlib
import math
import json


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


class Writer(object):
    """
    Presents a file-like object for writing to a Amazon Glacier
    Archive. The data is written using the multi-part upload API.
    """
    def __init__(self, vault, upload_id, part_size):
        self.vault = vault
        self.upload_id = upload_id
        self.part_size = part_size

        self._buffer_size = 0
        self._uploaded_size = 0
        self._buffer = []
        self._tree_hashes = []

        self.archive_location = None
        self.closed = False

    def send_part(self):
        buf = "".join(self._buffer)
        # Put back any data remaining over the part size into the
        # buffer
        if len(buf) > self.part_size:
            self._buffer = [buf[self.part_size:]]
            self._buffer_size = len(self._buffer[0])
        else:
            self._buffer = []
            self._buffer_size = 0
        # The part we will send
        part = buf[:self.part_size]
        # Create a request and sign it
        part_tree_hash = tree_hash(chunk_hashes(part))
        self._tree_hashes.append(part_tree_hash)

        hex_tree_hash = bytes_to_hex(part_tree_hash)
        linear_hash = hashlib.sha256(part).hexdigest()
        content_range = (self._uploaded_size,
                         (self._uploaded_size + len(part)) - 1)
        response = self.vault.layer1.upload_part(self.vault.name,
                                                 self.upload_id,
                                                 linear_hash,
                                                 hex_tree_hash,
                                                 content_range, part)
        self._uploaded_size += len(part)

    def write(self, str):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        if str == "":
            return
        self._buffer.append(str)
        self._buffer_size += len(str)
        while self._buffer_size > self.part_size:
            self.send_part()

    def close(self):
        if self.closed:
            return
        if self._buffer_size > 0:
            self.send_part()
        # Complete the multiplart glacier upload
        hex_tree_hash = bytes_to_hex(tree_hash(self._tree_hashes))
        response = self.vault.layer1.complete_multipart_upload(self.vault.name,
                                                               self.upload_id,
                                                               hex_tree_hash,
                                                               self._uploaded_size)
        self.archive_id = response['ArchiveId']
        self.closed = True

    def get_archive_id(self):
        self.close()
        return self.archive_id
