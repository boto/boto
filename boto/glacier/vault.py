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

from .job import Job
from .writer import Writer, bytes_to_hex, chunk_hashes, tree_hash
from .exceptions import ZeroLengthFileError
import hashlib
import os.path


class Vault(object):

    DefaultPartSize = 4 * 1024 * 1024  # 128MB

    ResponseDataElements = (('VaultName', 'name', None),
                            ('VaultARN', 'arn', None),
                            ('CreationDate', 'creation_date', None),
                            ('LastInventoryDate', 'last_inventory_date', None),
                            ('SizeInBytes', 'size', 0),
                            ('NumberOfArchives', 'number_of_archives', 0))

    def __init__(self, layer1, response_data=None):
        self.layer1 = layer1
        if response_data:
            for response_name, attr_name, default in self.ResponseDataElements:
                value = response_data[response_name]
                if isinstance(value, unicode):
                    value = value.encode('utf8')
                setattr(self, attr_name, value)
        else:
            for response_name, attr_name, default in self.ResponseDataElements:
                setattr(self, attr_name, default)

    def __repr__(self):
        return 'Vault("%s")' % self.arn

    def upload_archive(self, filename):
        """
        Adds an archive to a vault. For archives greater than 100MB the
        multipart upload will be used.

        :type file: str
        :param file: A filename to upload

        :rtype: str
        :return: The archive id of the newly created archive
        """
        megabyte = 1024 * 1024
        filesize = os.path.getsize(filename)
        if filesize == 0:
            raise ZeroLengthFileError(filename)
        if filesize > 100 * megabyte:
            return self.create_archive_from_file(filename)
        return self.upload_archive_single_operation(filename)

    def upload_archive_single_operation(self, filename):
        """
        Adds an archive to a vault in a single operation. It's recommended for
        archives less than 100MB
        :type file: str
        :param file: A filename to upload

        :rtype: str
        :return: The archive id of the newly created archive
        """
        archive = ''
        with open(filename, 'rb') as fd:
            archive = fd.read()
        if archive == '':
            raise ZeroLengthFileError(filename)
        linear_hash = hashlib.sha256(archive).hexdigest()
        hex_tree_hash  = bytes_to_hex(tree_hash(chunk_hashes(archive)))
        response = self.layer1.upload_archive(self.name, archive, linear_hash,
                                              hex_tree_hash)
        return response['ArchiveId']

    def create_archive_writer(self, part_size=DefaultPartSize,
                              description=None):
        """
        Create a new archive and begin a multi-part upload to it.
        Returns a file-like object to which the data for the archive
        can be written. Once all the data is written the file-like
        object should be closed, you can then call the get_archive_id
        method on it to get the ID of the created archive.

        :type part_size: int
        :param part_size: The part size for the multipart upload.

        :rtype: :class:`boto.glaicer.writer.Writer`
        :return: A Writer object that to which the archive data
            should be written.
        """
        response = self.layer1.initiate_multipart_upload(self.name,
                                                         part_size,
                                                         description)
        return Writer(self, response['UploadId'], part_size=part_size)

    def create_archive_from_file(self, file=None, file_obj=None):
        """
        Create a new archive and upload the data from the given file
        or file-like object.

        :type file: str
        :param file: A filename to upload

        :type file_obj: file
        :param file_obj: A file-like object to upload

        :rtype: str
        :return: The archive id of the newly created archive
        """
        if not file_obj:
            file_obj = open(file, "rb")

        writer = self.create_archive_writer()
        got_data = False
        while True:
            data = file_obj.read(1024 * 1024 * 4)
            if not data:
                break
            got_data = True
            writer.write(data)
        if got_data == False and file is None:
            raise ZeroLengthFileError()
        elif got_data == False and file is not None:
            raise ZeroLengthFileError(file)
        writer.close()
        return writer.get_archive_id()

    def retrieve_archive(self, archive_name, sns_topic=None,
                         description=None):
        """
        Initiate a archive retrieval job to download the data from an
        archive. You will need to wait for the notification from
        Amazon (via SNS) before you can actually download the data,
        this takes around 4 hours.

        :type archive_name: str
        :param archive_name: The name of the archive

        :type description: str
        :param description: An optional description for the job.

        :type sns_topic: str
        :param sns_topic: The Amazon SNS topic ARN where Amazon Glacier
            sends notification when the job is completed and the output
            is ready for you to download.

        :rtype: :class:`boto.glacier.job.Job`
        :return: A Job object representing the retrieval job.
        """
        job_data = {'Type': 'archive-retrieval',
                    'ArchiveId': archive_name}
        if sns_topic is not None:
            job_data['SNSTopic'] = sns_topic
        if description is not None:
            job_data['Description'] = description

        response = self.layer1.initiate_job(self.name, job_data)
        return response['JobId']

    def delete_archive(self, archive_id):
        """
        This operation deletes an archive from the vault.

        :type archive_id: str
        :param archive_id: The ID for the archive to be deleted.
        """
        return self.layer1.delete_archive(self.name, archive_id)

    def get_job(self, job_id):
        """
        Get an object representing a job in progress.

        :type job_id: str
        :param job_id: The ID of the job

        :rtype: :class:`boto.glaicer.job.Job`
        :return: A Job object representing the job.
        """
        response_data = self.layer1.describe_job(self.name, job_id)
        return Job(self, response_data)

    def list_jobs(self, completed=None, status_code=None):
        """
        Return a list of Job objects related to this vault.

        :type completed: boolean
        :param completed: Specifies the state of the jobs to return.
            If a value of True is passed, only completed jobs will
            be returned.  If a value of False is passed, only
            uncompleted jobs will be returned.  If no value is
            passed, all jobs will be returned.

        :type status_code: string
        :param status_code: Specifies the type of job status to return.
            Valid values are: InProgress|Succeeded|Failed.  If not
            specified, jobs with all status codes are returned.

        :rtype: list of :class:`boto.glaicer.job.Job`
        :return: A list of Job objects related to this vault.
        """
        response_data = self.layer1.list_jobs(self.name, completed,
                                              status_code)
        return [Job(self, jd) for jd in response_data['JobList']]
