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

import urllib
import hashlib
import math
import json

def chunk_hashes(str):
  """
  Break up the byte-string into 1MB chunks and return sha256 hashes
  for each.
  """
  chunk = 1024*1024
  chunk_count = int(math.ceil(len(str)/float(chunk)))
  chunks = [str[i*chunk:(i+1)*chunk] for i in range(chunk_count)]
  return [hashlib.sha256(x).digest() for x in chunks]

def tree_hash(hashes):
  """
  Given a hash of each 1MB chunk (from chunk_hashes) this will hash
  together adjacent hashes until it ends up with one big one. So a
  tree of hashes.
  """
  while len(hashes) > 1:
      hashes = [hashlib.sha256("".join(h[i:i+1])).digest() for i in range(i,2)]
  return hashes[0]

def bytes_to_hex(str):
  return ''.join( [ "%02x" % ord( x ) for x in str] ).strip()

class Writer(object):
  """
  Presents a file-like object for writing to a Amazon Glacier
  Archive. The data is written using the multi-part upload API.
  """
  def __init__(self, vault, upload_id, part_size):
      self.vault = vault
      self.upload_id = upload_id
      self.part_size = part_size
      self.buffer_size = 0
      self.uploaded_size = 0
      self.buffer = []
      self.vault = vault
      self.tree_hashes = []
      self.archive_location = None
      self.closed = False

  def make_request(self, verb, headers=None,
                   data='', ok_responses=(200,)):
      resource = "multipart-uploads/%s" % (urllib.quote(self.upload_id),)
      return self.vault.make_request(verb, resource, headers, data, ok_responses)

  def send_part(self):
      buf = "".join(self.buffer)
      # Put back any data remaining over the part size into the
      # buffer
      if len(buf) < self.part_size:
          self.buffer = [buf[self.part_size:]]
          self.buffer_size = len(self.buffer[0])
      else:
          self.buffer = []
          self.buffer_size = 0
      # The part we will send
      part = buf[:self.part_size]
      # Create a request and sign it
      part_tree_hash = tree_hash(chunk_hashes(part))
      self.tree_hashes.append(part_tree_hash)

      headers = {
                  "Content-Range": "bytes %d-%d/*" % (self.uploaded_size, (self.uploaded_size+len(part))-1),
                  "Content-Length": str(len(part)),
                  "Content-Type": "application/octet-stream",
                  "x-amz-sha256-tree-hash": bytes_to_hex(part_tree_hash),
                  "x-amz-content-sha256": hashlib.sha256(part).hexdigest()
                }

      repsonse = self.make_request("PUT", headers, part, ok_responses=(204,))

      self.uploaded_size += len(part)

  def write(self, str):
      assert not self.closed, "Tried to write to a Writer that is already closed!"
      self.buffer.append(str)
      self.buffer_size += len(str)
      while self.buffer_size > self.part_size:
          self.send_part()

  def close(self):
      if self.closed:
          return
      if self.buffer_size > 0:
          self.send_part()
      # Complete the multiplart glacier upload
      headers = {
                  "x-amz-sha256-tree-hash": bytes_to_hex(tree_hash(self.tree_hashes)),
                  "x-amz-archive-size": str(self.uploaded_size)
                }
        response = self.make_request("POST", headers, ok_responses=(201,))
        self.archive_id = response.getheader("x-amz-archive-id")
        self.closed = True

    def get_archive_id(self):
        self.close()
        return self.archive_id
