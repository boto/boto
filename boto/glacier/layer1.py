# -*- coding: utf-8 -*-
# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
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

import json
import boto
from boto.connection import AWSAuthConnection

boto.set_stream_logger('glacier')


class Layer1(AWSAuthConnection):

    DefaultRegionName = 'us-east-1'
    """The default region to connect to."""

    Version = '2012-06-01'
    """Glacier API version."""

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 account_id='-', is_secure=True, port=None,
                 proxy=None, proxy_port=None,
                 debug=2, security_token=None, region=None):
        if not region:
            region_name = boto.config.get('DynamoDB', 'region',
                                          self.DefaultRegionName)
            for reg in boto.glacier.regions():
                if reg.name == region_name:
                    region = reg
                    break

        self.region = region
        self.account_id = account_id
        AWSAuthConnection.__init__(self, region.endpoint,
                                   aws_access_key_id, aws_secret_access_key,
                                   True, port, proxy, proxy_port, debug=debug,
                                   security_token=security_token)

    def _required_auth_capability(self):
        return ['hmac-v4']

    def make_request(self, verb, resource, headers=None,
                     data='', ok_responses=(200,)):
        if headers is None:
            headers = {}
        headers = {'x-amz-glacier-version': self.Version}
        uri = '/%s/%s' % (self.account_id, resource)
        response = AWSAuthConnection.make_request(self, verb, uri,
                                                  headers=headers,
                                                  data=data)
        body = response.read()
        if response.status in ok_responses:
            if body:
                boto.log.debug(body)
                body = json.loads(body)
            return body
        else:
            msg = 'Expected %s, got (%d, %s)' % (ok_responses,
                                                 response.status,
                                                 body)
            # create glacier-specific exceptions
            raise BaseException(msg)

    # Vaults

    def list_vaults(self, limit=None, marker=None):
        """
        This operation lists all vaults owned by the calling user’s
        account. The list returned in the response is ASCII-sorted by
        vault name.

        By default, this operation returns up to 1,000 items. If there
        are more vaults to list, the marker field in the response body
        contains the vault Amazon Resource Name (ARN) at which to
        continue the list with a new List Vaults request; otherwise,
        the marker field is null. In your next List Vaults request you
        set the marker parameter to the value Amazon Glacier returned
        in the responses to your previous List Vaults request. You can
        also limit the number of vaults returned in the response by
        specifying the limit parameter in the request.

        :type limit: int
        :param limit: The maximum number of items returned in the
            response. If you don't specify a value, the List Vaults
            operation returns up to 1,000 items.

        :type marker: str
        :param marker: A string used for pagination. marker specifies
            the vault ARN after which the listing of vaults should
            begin. (The vault specified by marker is not included in
            the returned list.) Get the marker value from a previous
            List Vaults response. You need to include the marker only
            if you are continuing the pagination of results started in
            a previous List Vaults request. Specifying an empty value
            ("") for the marker returns a list of vaults starting
            from the first vault.
        """
        return self.make_request('GET', 'vaults')

    def describe_vault(self, vault_name):
        """
        This operation returns information about a vault, including
        the vault Amazon Resource Name (ARN), the date the vault was
        created, the number of archives contained within the vault,
        and the total size of all the archives in the vault. The
        number of archives and their total size are as of the last
        vault inventory Amazon Glacier generated.  Amazon Glacier
        generates vault inventories approximately daily. This means
        that if you add or remove an archive from a vault, and then
        immediately send a Describe Vault request, the response might
        not reflect the changes.

        :type vault_name: str
        :param vault_name: The name of the new vault
        """
        uri = 'vaults/%s' % vault_name
        return self.make_request('GET', uri)

    def create_vault(self, vault_name):
        """
        This operation creates a new vault with the specified name.
        The name of the vault must be unique within a region for an
        AWS account. You can create up to 1,000 vaults per
        account. For information on creating more vaults, go to the
        Amazon Glacier product detail page.

        You must use the following guidelines when naming a vault.

        Names can be between 1 and 255 characters long.

        Allowed characters are a–z, A–Z, 0–9, '_' (underscore),
        '-' (hyphen), and '.' (period).

        This operation is idempotent, you can send the same request
        multiple times and it has no further effect after the first
        time Amazon Glacier creates the specified vault.

        :type vault_name: str
        :param vault_name: The name of the new vault
        """
        uri = 'vaults/%s' % vault_name
        return self.make_request('PUT', uri, ok_responses=(201,))

    def delete_vault(self, vault_name):
        """
        This operation deletes a vault. Amazon Glacier will delete a
        vault only if there are no archives in the vault as per the
        last inventory and there have been no writes to the vault
        since the last inventory. If either of these conditions is not
        satisfied, the vault deletion fails (that is, the vault is not
        removed) and Amazon Glacier returns an error.

        This operation is idempotent, you can send the same request
        multiple times and it has no further effect after the first
        time Amazon Glacier delete the specified vault.

        :type vault_name: str
        :param vault_name: The name of the new vault
        """
        uri = 'vaults/%s' % vault_name
        return self.make_request('DELETE', uri, ok_responses=(204,))

    def get_vault_notifications(self, vault_name):
        """
        This operation retrieves the notification-configuration
        subresource set on the vault.

        :type vault_name: str
        :param vault_name: The name of the new vault
        """
        uri = 'vaults/%s/notification-configuration' % vault_name
        return self.make_request('GET', uri)

    def set_vault_notifications(self, vault_name, notification_config):
        """
        This operation retrieves the notification-configuration
        subresource set on the vault.

        :type vault_name: str
        :param vault_name: The name of the new vault

        :type notification_config: dict
        :param notification_config: A Python dictionary containing
            an SNS Topic and events for which you want Amazon Glacier
            to send notifications to the topic.  Possible events are:

            * ArchiveRetrievalCompleted - occurs when a job that was
              initiated for an archive retrieval is completed.
            * InventoryRetrievalCompleted - occurs when a job that was
              initiated for an inventory retrieval is completed.

            The format of the dictionary is:

                {'SNSTopic': 'mytopic',
                 'Events': [event1,...]}
        """
        uri = 'vaults/%s/notification-configuration' % vault_name
        json_config = json.dumps(notification_config)
        return self.make_request('PUT', uri, data=json_config,
                                 ok_responses=(204,))

    def delete_vault_notifications(self, vault_name):
        """
        This operation deletes the notification-configuration
        subresource set on the vault.

        :type vault_name: str
        :param vault_name: The name of the new vault
        """
        uri = 'vaults/%s/notification-configuration' % vault_name
        return self.make_request('DELETE', uri, ok_responses=(204,))

    # Jobs

    def list_jobs(self, vault_name, completed=None, limit=None,
                  marker=None, status_code=None):
        """
        This operation lists jobs for a vault including jobs that are
        in-progress and jobs that have recently finished.

        :type vault_name: str
        :param vault_name: The name of the vault.

        :type completed: boolean
        :param completed: Specifies the state of the jobs to return.
            If a value of True is passed, only completed jobs will
            be returned.  If a value of False is passed, only
            uncompleted jobs will be returned.  If no value is
            passed, all jobs will be returned.

        :type limit: int
        :param limit: The maximum number of items returned in the
            response. If you don't specify a value, the List Jobs
            operation returns up to 1,000 items.

        :type marker: str
        :param marker: An opaque string used for pagination. marker
            specifies the job at which the listing of jobs should
            begin. Get the marker value from a previous List Jobs
            response. You need only include the marker if you are
            continuing the pagination of results started in a previous
            List Jobs request.

        :type status_code: string
        :param status_code: Specifies the type of job status to return.
            Valid values are: InProgress|Succeeded|Failed.  If not
            specified, jobs with all status codes are returned.
        """
        uri = 'vaults/%s/jobs' % vault_name
        return self.make_request('GET', uri)

    def describe_job(self, vault_name, job_id):
        """
        This operation returns information about a job you previously
        initiated, including the job initiation date, the user who
        initiated the job, the job status code/message and the Amazon
        Simple Notification Service (Amazon SNS) topic to notify after
        Amazon Glacier completes the job.

        :type vault_name: str
        :param vault_name: The name of the new vault

        :type job_id: str
        :param job_id: The ID of the job.
        """
        uri = 'vaults/%s/jobs/%s' % (vault_name, job_id)
        return self.make_request('GET', uri, ok_responses=(201,))

    def initiate_job(self, vault_name, job_data):
        """
        This operation initiates a job of the specified
        type. Retrieving an archive or a vault inventory are
        asynchronous operations that require you to initiate a job. It
        is a two-step process:

        * Initiate a retrieval job.
        * After the job completes, download the bytes.

        The retrieval is executed asynchronously.  When you initiate
        a retrieval job, Amazon Glacier creates a job and returns a
        job ID in the response.

        :type vault_name: str
        :param vault_name: The name of the new vault

        :type job_data: dict
        :param job_data: A Python dictionary containing the
            information about the requested job.  The dictionary
            can contain the following attributes:

            * ArchiveId - The ID of the archive you want to retrieve.
              This field is required only if the Type is set to
              archive-retrieval.
            * Description - The optional description for the job.
            * Format - When initiating a job to retrieve a vault
              inventory, you can optionally add this parameter to
              specify the output format.  Valid values are: CSV|JSON.
            * SNSTopic - The Amazon SNS topic ARN where Amazon Glacier
              sends a notification when the job is completed and the
              output is ready for you to download.
            * Type - The job type.  Valid values are:
              archive-retrieval|inventory-retrieval
        """
        uri = 'vaults/%s/jobs' % vault_name
        json_job_data = json.dumps(job_data)
        return self.make_request('POST', uri, data=json_job_data,
                                 ok_responses=(202,))

    def get_job_output(self, vault_name, job_id):
        """
        This operation downloads the output of the job you initiated
        using Initiate a Job. Depending on the job type
        you specified when you initiated the job, the output will be
        either the content of an archive or a vault inventory.

        You can download all the job output or download a portion of
        the output by specifying a byte range. In the case of an
        archive retrieval job, depending on the byte range you
        specify, Amazon Glacier returns the checksum for the portion
        of the data. You can compute the checksum on the client and
        verify that the values match to ensure the portion you
        downloaded is the correct data.

        :type vault_name: str :param
        :param vault_name: The name of the new vault

        :type job_id: str
        :param job_id: The ID of the job.
        """
        uri = 'vaults/%s/jobs/%s/output' % (vault_name, job_id)
        return self.make_request('GET', uri)

    # Archives

    def upload_archive(self, vault_name, archive,
                       linear_hash, tree_hash, description=None):
        """
        This operation adds an archive to a vault. For a successful
        upload, your data is durably persisted. In response, Amazon
        Glacier returns the archive ID in the x-amz-archive-id header
        of the response. You should save the archive ID returned so
        that you can access the archive later.

        :type vault_name: str :param
        :param vault_name: The name of the vault

        :type archive: bytes
        :param archive: The data to upload.

        :type linear_hash: str
        :param linear_hash: The SHA256 checksum (a linear hash) of the
            payload.

        :type tree_hash: str
        :param tree_hash: The user-computed SHA256 tree hash of the
            payload.  For more information on computing the
            tree hash, see http://goo.gl/u7chF.

        :type description: str
        :param description: An optional description of the archive.
        """
        uri = 'vaults/%s/archives' % vault_name
        headers = {'x-amz-content-sha256': linear_hash,
                   'x-amz-sha256-tree-hash': tree_hash,
                   'x-amz-content-length': len(archive)}
        if description:
            headers['x-amz-archive-description'] = description
        return self.make_request('GET', uri, headers=headers,
                                 data=archive, ok_responses=(201,))

    def delete_archive(self, vault_name, archive_id):
        """
        This operation deletes an archive from a vault.

        :type vault_name: str
        :param vault_name: The name of the new vault

        :type archive_id: str
        :param archive_id: The ID for the archive to be deleted.
        """
        uri = 'vaults/%s/archives/%s' % (vault_name, archive_id)
        return self.make_request('DELETE', uri, ok_responses=(204,))
