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
from .writer import Writer
import urllib
import json


class Vault(object):

    DefaultPartSize = 4 * 1024 * 1024  #128MB

    def __init__(self, layer1, name):
        self.layer1 = layer1
        self.name = name

    def make_request(self, verb, resource, headers=None,
                   data='', ok_responses=(200,)):
        resource = "vaults/%s/%s" % (urllib.quote(self.name), resource)
        return self.layer1.make_request(verb,resource, headers,
                                        data,ok_responses)

    def create_archive_writer(self, part_size=DefaultPartSize):
        """
        Create a new archive and begin a multi-part upload to it.
        Returns a file-like object to which the data for the archive
        can be written. Once all the data is written the file-like
        object should be closed, you can then call the get_archive_id
        method on it to get the ID of the created archive.

        :type archive_name: str
        :param archive_name: The name of the archive

        :type part_size: int
        :param part_size: The part size for the multipart upload.

        :rtype: :class:`boto.glaicer.writer.Writer`
        :return: A Writer object that to which the archive data
            should be written.
        """

        headers = {
                    "x-amz-part-size": str(part_size)
                  }
        response = self.make_request("POST", "multipart-uploads",
                                     headers=headers, ok_responses=(201,))
        upload_id = response.getheader("x-amz-multipart-upload-id")
        return Writer(self, upload_id, part_size=part_size)

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
        writer = self.create_archive_writer(archive_name)
        while True:
            data = file_obj.read(1024 * 1024 * 4)
            if not data:
                break
            writer.write(data)
        writer.close()
        return writer.get_archive_id()

    def retrieve_archive(self, archive_name, sns_topic=None, description=None):
        """
        Initiate a archive retrieval job to download the data from an
        archive. You will need to wait for the notification from
        Amazon (via SNS) before you can actually download the data,
        this takes around 4 hours.

        :type archive_name: str
        :param archive_name: The name of the archive

        :rtype: :class:`boto.glaicer.job.Job`
        :return: A Job object representing the retrieval job.
        """
        params = {"Type": "archive-retrieval", "ArchiveId": archive_name}
        if sns_topic is not None:
            params["SNSTopic"] = sns_topic
        if description is not None:
            params["Description"] = description

        response = self.make_request("POST", "jobs", None,
                                     json.dumps(params),
                                     ok_responses=(202,))
        job_id = response.getheader("x-amz-job-id")
        job = Job(self, job_id)
        return job

    def get_job(self, job_id):
        """
        Get an object representing a job in progress.

        :type job_id: str
        :param job_id: The ID of the job

        :rtype: :class:`boto.glaicer.job.Job`
        :return: A Job object representing the job.
        """
        return Job(self, job_id)
