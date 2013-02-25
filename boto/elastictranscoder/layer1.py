# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
from boto.compat import json
from boto.exception import JSONResponseError
from boto.connection import AWSAuthConnection
from boto.regioninfo import RegionInfo
from boto.elastictranscoder import exceptions


class ElasticTranscoderConnection(AWSAuthConnection):
    """
    AWS Elastic Transcoder Service
    The AWS Elastic Transcoder Service.
    """
    APIVersion = "2012-09-25"
    DefaultRegionName = "us-east-1"
    DefaultRegionEndpoint = "elastictranscoder.us-east-1.amazonaws.com"
    ResponseError = JSONResponseError

    _faults = {
        "LimitExceededException": exceptions.LimitExceededException,
        "ResourceInUseException": exceptions.ResourceInUseException,
        "AccessDeniedException": exceptions.AccessDeniedException,
        "ResourceNotFoundException": exceptions.ResourceNotFoundException,
        "InternalServiceException": exceptions.InternalServiceException,
        "ValidationException": exceptions.ValidationException,
    }


    def __init__(self, **kwargs):
        region = kwargs.get('region')
        if not region:
            region = RegionInfo(self, self.DefaultRegionName,
                                self.DefaultRegionEndpoint)
        else:
            del kwargs['region']
        kwargs['host'] = region.endpoint
        AWSAuthConnection.__init__(self, **kwargs)
        self.region = region

    def _required_auth_capability(self):
        return ['hmac-v4']

    def cancel_job(self, id):
        """
        To delete a job, send a DELETE request to the `//jobs/ [jobId]
        ` resource.
        You can only cancel a job that has a status of `Submitted`. To
        prevent a pipeline from starting to process a job while you're
        getting the job identifier, use UpdatePipelineStatus to
        temporarily pause the pipeline.

        :type id: string
        :param id: The identifier of the job that you want to delete.

        To get a list of the jobs (including their `jobId`) that have
            a status of `Submitted`, use the ListJobsByStatus API
            action.

        """
        uri = '/2012-09-25/jobs/{0}'.format(id)
        return self.make_request('DELETE', uri, expected_status=202)

    def create_job(self, pipeline_id, input_name, output):
        """
        To create a job, send a POST request to the `//jobs` resource.

        When you create a job, Elastic Transcoder returns JSON data
        that includes the values that you specified plus information
        about the job that is created.

        :type pipeline_id: string
        :param pipeline_id: The `Id` of the pipeline that you want Elastic
            Transcoder to use for transcoding. The pipeline
            determines several settings, including the
            Amazon S3 bucket from which Elastic Transcoder
            gets the files to transcode and the bucket into
            which Elastic Transcoder puts the transcoded
            files.

        :type input_name: dict
        :param input_name: A section of the request body that provides
            information about the file that is being
            transcoded.

        :type output: dict
        :param output: A section of the request body that provides information
            about the transcoded (target) file.

        """
        uri = '/2012-09-25/jobs'
        params = {
            'PipelineId': pipeline_id,
            'Input': input_name,
            'Output': output,
        }
        return self.make_request('POST', uri, expected_status=201,
                                 data=json.dumps(params))

    def create_pipeline(self, name, input_bucket, output_bucket, role,
                        notifications):
        """
        To create a pipeline, send a POST request to the `/pipelines`
        resource.

        :type name: string
        :param name: The name of the pipeline. We recommend that the name be
            unique within the AWS account, but uniqueness is not
            enforced.

        Constraints: Maximum 40 characters.

        :type input_bucket: string
        :param input_bucket: The bucket in which you saved the media files that
            you want to transcode.

        :type output_bucket: string
        :param output_bucket: The bucket in which you want to save the
            transcoded files.

        :type role: string
        :param role: The IAM Amazon Resource Name (ARN) for the role that you
            want to use to create the pipeline.

        :type notifications: dict
        :param notifications: The () topic that you want to notify to report job
            status.
        
        To receive notifications, you must also subscribe
            to the new topic in the console.

        + **Progressing**: The () topic that you want to
              notify when has started to process the job.
        + **Completed**: The topic that you want to notify
              when has finished processing the job.
        + **Warning**: The topic that you want to notify
              when encounters a warning condition.
        + **Error**: The topic that you want to notify
              when encounters an error condition.

        """
        uri = '/2012-09-25/pipelines'
        params = {
            'Name': name,
            'InputBucket': input_bucket,
            'OutputBucket': output_bucket,
            'Role': role,
            'Notifications': notifications,
        }
        return self.make_request('POST', uri, expected_status=201,
                                 data=json.dumps(params))

    def create_preset(self, name, container, video, audio, thumbnails,
                      description=None):
        """
        To create a preset, send a POST request to the `//presets`
        resource.
        checks the settings that you specify to ensure that they meet
        requirements and to determine whether they comply with H.264
        standards. If your settings are not valid for , returns an
        HTTP 400 response ( `ValidationException`) and does not create
        the preset. If the settings are valid for but aren't strictly
        compliant with the H.264 standard, creates the preset and
        returns a warning message in the response. This helps you
        determine whether your settings comply with the H.264 standard
        while giving you greater flexibility with respect to the video
        that produces.
        uses the H.264 video-compression format. For more information,
        see the International Telecommunication Union publication
        Recommendation ITU-T H.264: Advanced video coding for generic
        audiovisual services .

        :type name: string
        :param name: The name of the preset. We recommend that the name be
            unique within the AWS account, but uniqueness is not
            enforced.

        :type description: string
        :param description: A description of the preset.

        :type container: string
        :param container: The container type for the output file. This value
            must be `mp4`.

        :type video: dict
        :param video: A section of the request body that specifies the video
            parameters.

        :type audio: dict
        :param audio: A section of the request body that specifies the audio
            parameters

        :type thumbnails: dict
        :param thumbnails: A section of the request body that specifies the
            thumbnail parameters, if any.

        """
        uri = '/2012-09-25/presets'
        params = {
            'Name': name,
            'Container': container,
            'Video': video,
            'Audio': audio,
            'Thumbnails': thumbnails,
        }
        if description is not None:
            params['Description'] = description
        return self.make_request('POST', uri, expected_status=201,
                                 data=json.dumps(params))

    def delete_pipeline(self, id):
        """
        To delete a pipeline, send a DELETE request to the
        `//pipelines/ [pipelineId]` resource.

        You can only delete a pipeline that has never been used or
        that is not currently in use (doesn't contain any active
        jobs). If the pipeline is currently in use, `DeletePipeline`
        returns an error.

        :type id: string
        :param id: The identifier of the pipeline that you want to delete.

        """
        uri = '/2012-09-25/pipelines/{0}'.format(id)
        return self.make_request('DELETE', uri, expected_status=202)

    def delete_preset(self, id):
        """
        To delete a preset, send a DELETE request to the `//presets/
        [presetId]` resource.

        If the preset has been used, you cannot delete it.

        :type id: string
        :param id: The identifier of the preset for which you want to get
            detailed information.

        """
        uri = '/2012-09-25/presets/{0}'.format(id)
        return self.make_request('DELETE', uri, expected_status=202)

    def list_jobs_by_pipeline(self, pipeline_id, ascending=None,
                              page_token=None):
        """
        To get a list of the jobs currently in a pipeline, send a GET
        request to the `//jobsByPipeline/ [pipelineId]` resource.

        Elastic Transcoder returns all of the jobs currently in the
        specified pipeline. The response body contains one element for
        each job that satisfies the search criteria.

        :type pipeline_id: string
        :param pipeline_id: The ID of the pipeline for which you want to get job
            information.

        :type ascending: string
        :param ascending: To list jobs in chronological order by the date and
            time that they were submitted, enter `True`. To
            list jobs in reverse chronological order, enter
            `False`.

        :type page_token: string
        :param page_token: When returns more than one page of results, use
            `pageToken` in subsequent `GET` requests to get
            each successive page of results.

        """
        uri = '/2012-09-25/jobsByPipeline/{0}'.format(pipeline_id)
        params = {}
        if ascending is not None:
            params['Ascending'] = ascending
        if page_token is not None:
            params['PageToken'] = page_token
        return self.make_request('GET', uri, expected_status=200,
                                 params=params)

    def list_jobs_by_status(self, status, ascending=None, page_token=None):
        """
        To get a list of the jobs that have a specified status, send a
        GET request to the `//jobsByStatus/ [status]` resource.

        Elastic Transcoder returns all of the jobs that have the
        specified status. The response body contains one element for
        each job that satisfies the search criteria.

        :type status: string
        :param status: To get information about all of the jobs associated with
            the current AWS account that have a given status,
            specify the following status: `Submitted`,
            `Progressing`, `Completed`, `Canceled`, or `Error`.

        :type ascending: string
        :param ascending: To list jobs in chronological order by the date and
            time that they were submitted, enter `True`. To
            list jobs in reverse chronological order, enter
            `False`.

        :type page_token: string
        :param page_token: When returns more than one page of results, use
            `pageToken` in subsequent `GET` requests to get
            each successive page of results.

        """
        uri = '/2012-09-25/jobsByStatus/{0}'.format(status)
        params = {}
        if ascending is not None:
            params['Ascending'] = ascending
        if page_token is not None:
            params['PageToken'] = page_token
        return self.make_request('GET', uri, expected_status=200,
                                 params=params)

    def list_pipelines(self):
        """
        To get a list of the pipelines associated with the current AWS
        account, send a GET request to the `//pipelines` resource.


        """
        uri = '/2012-09-25/pipelines'
        return self.make_request('GET', uri, expected_status=200)

    def list_presets(self):
        """
        To get a list of all presets associated with the current AWS
        account, send a GET request to the `//presets` resource.


        """
        uri = '/2012-09-25/presets'
        return self.make_request('GET', uri, expected_status=200)

    def read_job(self, id):
        """
        To get detailed information about a job, send a GET request to
        the `//jobs/ [jobId]` resource.

        :type id: string
        :param id: The identifier of the job for which you want to get detailed
            information.

        """
        uri = '/2012-09-25/jobs/{0}'.format(id)
        return self.make_request('GET', uri, expected_status=200)

    def read_pipeline(self, id):
        """
        To get detailed information about a pipeline, send a GET
        request to the `//pipelines/ [pipelineId]` resource.

        :type id: string
        :param id: The identifier of the pipeline to read.

        """
        uri = '/2012-09-25/pipelines/{0}'.format(id)
        return self.make_request('GET', uri, expected_status=200)

    def read_preset(self, id):
        """
        To get detailed information about a preset, send a GET request
        to the `//presets/ [presetId]` resource.

        :type id: string
        :param id: The identifier of the preset for which you want to get
            detailed information.

        """
        uri = '/2012-09-25/presets/{0}'.format(id)
        return self.make_request('GET', uri, expected_status=200)

    def test_role(self, role, input_bucket, output_bucket, topics):
        """
        To test the IAM role that's used by Elastic Transcoder to
        create the pipeline, send a POST request to the `//roleTests`
        resource.

        The `TestRole` action lets you determine whether the IAM role
        you are using has sufficient permissions to let perform tasks
        associated with the transcoding process. The action attempts
        to assume the specified IAM role, checks read access to the
        input and output buckets, and tries to send a test
        notification to Amazon SNS topics that you specify.

        :type role: string
        :param role: The IAM Amazon Resource Name (ARN) for the role that you
            want Elastic Transcoder to test.

        :type input_bucket: string
        :param input_bucket: The bucket that contains media files to be
            transcoded. The action attempts to read from
            this bucket.

        :type output_bucket: string
        :param output_bucket: The bucket that will write transcoded media files
            to. The action attempts to read from this
            bucket.

        :type topics: list
        :param topics: The ARNs of one or more () topics that you want the
            action to send a test notification to.

        """
        uri = '/2012-09-25/roleTests'
        params = {
            'Role': role,
            'InputBucket': input_bucket,
            'OutputBucket': output_bucket,
            'Topics': topics,
        }
        return self.make_request('POST', uri, expected_status=200,
                                 data=json.dumps(params))

    def update_pipeline_notifications(self, id, notifications):
        """
        To update () notifications for a pipeline, send a POST request
        to the `//pipelines/ [pipelineId] /notifications` resource.

        When you update notifications for a pipeline, returns the
        values that you specified in the request.

        :type id: string
        :param id: The identifier of the pipeline for which you want to change
            notification settings.

        :type notifications: dict
        :param notifications: The () topic that you want to notify to report job
            status.
        To receive notifications, you must also subscribe
            to the new topic in the console.

        + **Progressing**: The () topic that you want to
              notify when has started to process the job.
        + **Completed**: The topic that you want to notify
              when has finished processing the job.
        + **Warning**: The topic that you want to notify
              when encounters a warning condition.
        + **Error**: The topic that you want to notify
              when encounters an error condition.

        """
        uri = '/2012-09-25/pipelines/{0}/notifications'.format(id)
        params = {'Notifications': notifications, }
        return self.make_request('POST', uri, expected_status=200,
                                 data=json.dumps(params))

    def update_pipeline_status(self, id, status):
        """
        To pause or reactivate a pipeline, so the pipeline stops or
        restarts processing jobs, update the status for the pipeline.
        Send a POST request to the `//pipelines/ [pipelineId] /status`
        resource.

        Changing the pipeline status is useful if you want to cancel
        one or more jobs. You can't cancel jobs after has started
        processing them; if you pause the pipeline to which you
        submitted the jobs, you have more time to get the job IDs for
        the jobs that you want to cancel, and to send a CancelJob
        request.

        :type id: string
        :param id: The identifier of the pipeline to update.

        :type status: string
        :param status: The new status of the pipeline:


        + `active`: Enable the pipeline, so it starts processing
              jobs.
        + `paused`: Disable the pipeline, so it stops processing
              jobs.

        """
        uri = '/2012-09-25/pipelines/{0}/status'.format(id)
        params = {'Status': status, }
        return self.make_request('POST', uri, expected_status=200,
                                 data=json.dumps(params))

    def make_request(self, verb, resource, headers=None, data='',
                     expected_status=None, params=None):
        if headers is None:
            headers = {}
        response = AWSAuthConnection.make_request(
            self, verb, resource, headers=headers, data=data)
        body = json.load(response)
        if response.status == expected_status:
            return body
        else:
            error_type = response.getheader('x-amzn-ErrorType').split(':')[0]
            error_class = self._faults.get(error_type, self.ResponseError)
            raise error_class(response.status, response.reason, body)
