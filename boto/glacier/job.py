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
import json

from .utils import chunk_hashes, tree_hash, bytes_to_hex
 
from .exceptions import HashesDoNotMatchError, UnexpectedHTTPResponseError

class Job(object):

    ResponseDataElements = (('Action', 'action', None),
                            ('ArchiveId', 'archive_id', None),
                            ('ArchiveSizeInBytes', 'archive_size', 0),
                            ('Completed', 'completed', False),
                            ('CompletionDate', 'completion_date', None),
                            ('CreationDate', 'creation_date', None),
                            ('InventorySizeInBytes', 'inventory_size', 0),
                            ('JobDescription', 'description', None),
                            ('JobId', 'id', None),
                            ('SHA256TreeHash', 'sha256_treehash', None),
                            ('SNSTopic', 'sns_topic', None),
                            ('StatusCode', 'status_code', None),
                            ('StatusMessage', 'status_message', None),
                            ('VaultARN', 'arn', None))

    def __init__(self, vault, response_data=None):
        self.vault = vault
        if response_data:
            for response_name, attr_name, default in self.ResponseDataElements:
                setattr(self, attr_name, response_data[response_name])
        else:
            for response_name, attr_name, default in self.ResponseDataElements:
                setattr(self, attr_name, default)

    def __repr__(self):
        return 'Job(%s)' % self.arn

    def get_output_chunk(self, chunk_number, chunk_size=1024*1024*4):
        """
        This operation downloads the output of the job in chunks. You
        should download the chunks starting from 0 and continue until
        the you get a an empty retun.

        Each chunk is downloaded in full and the hash checked before
        it is returned. Chunk size can be specified but must be a
        multiple of 1MB.

        :type chunk_number: int
        :param chunk_number: The number of the chunk to download,
            starting with 0.
            
        :type chunk_size: int
        :param chunk_size: Size of the chunk to download, must be a
           multiple of 1MB.
        """
        try:
            response = self.get_output((chunk_number*chunk_size, (chunk_number*(chunk_number+1))-1))
        except UnexpectedHTTPResponseError, e:
            if e.status == 400 and e.code == "InvalidParameterValueException":
                # This just means that we specified a range beyond the
                # end of the output. Return an empty string to
                # indicate end of file.
                return ""
            else:
                raise
        data = response.read()
        if response["TreeHash"] != bytes_to_hex(tree_hash(chunk_hashes(data))):
            raise HashesDoNotMatchError("Hashes do not match in downloaded chunk")
        return data

    def get_output(self, byte_range=None):
        """
        This operation downloads the output of the job. Depending on
        the job type you specified when you initiated the job, the
        output will be either the content of an archive or a vault
        inventory.

        You can download all the job output or download a portion of
        the output by specifying a byte range. In the case of an
        archive retrieval job, depending on the byte range you
        specify, Amazon Glacier returns the checksum for the portion
        of the data. You can compute the checksum on the client and
        verify that the values match to ensure the portion you
        downloaded is the correct data.

        :type byte_range: tuple
        :param range: A tuple of integer specifying the slice (in
            bytes, as an inclusive range) of the archive you want to
            receive.
        """
        return self.vault.layer1.get_job_output(self.vault.name,
                                                self.id,
                                                byte_range)
