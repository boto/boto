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
import hashlib

from .utils import chunk_hashes, tree_hash, bytes_to_hex

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
        assert not self.closed, "Tried to write to a Writer that is already closed!"
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
        response = self.vault.layer1.complete_multipart_upload(
            self.vault.name, self.upload_id, hex_tree_hash, self._uploaded_size)
        self.archive_id = response['ArchiveId']
        self.closed = True

    def get_archive_id(self):
        self.close()
        return self.archive_id
