# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.
# All Rights Reserved
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
try:
    import simplejson as json
except ImportError:
    import json

import boto.exception
import requests
import boto

class SearchServiceException(Exception):
    pass


class CommitMismatchError(Exception):
    pass


class DocumentServiceConnection(object):

    def __init__(self, domain=None, endpoint=None):
        self.domain = domain
        self.endpoint = endpoint
        if not self.endpoint:
            self.endpoint = domain.doc_service_endpoint
        self.documents_batch = []
        self._sdf = None

    def add(self, _id, version, fields, lang='en'):
        d = {'type': 'add', 'id': _id, 'version': version, 'lang': lang,
            'fields': fields}
        self.documents_batch.append(d)

    def delete(self, _id, version):
        d = {'type': 'delete', 'id': _id, 'version': version}
        self.documents_batch.append(d)

    def get_sdf(self):
        return self._sdf if self._sdf else json.dumps(self.documents_batch)

    def clear_sdf(self):
        self._sdf = None
        self.documents_batch = []

    def add_sdf_from_s3(self, key_obj):
        """@todo (lucas) would be nice if this could just take an s3://uri..."""
        self._sdf = key_obj.get_contents_as_string()

    def commit(self):
        sdf = self.get_sdf()

        if ': null' in sdf:
            boto.log.error('null value in sdf detected.  This will probably raise '
                '500 error.')
            index = sdf.index(': null')
            boto.log.error(sdf[index - 100:index + 100])

        url = "http://%s/2011-02-01/documents/batch" % (self.endpoint)

        request_config = {
            'pool_connections': 20,
            'keep_alive': True,
            'max_retries': 5,
            'pool_maxsize': 50
        }

        r = requests.post(url, data=sdf, config=request_config,
            headers={'Content-Type': 'application/json'})

        return CommitResponse(r, self, sdf)


class CommitResponse(object):
    """Wrapper for response to Cloudsearch document batch commit.

    :type response: :class:`requests.models.Response`
    :param response: Response from Cloudsearch /documents/batch API

    :type doc_service: :class:`exfm.cloudsearch.DocumentServiceConnection`
    :param doc_service: Object containing the documents posted and methods to
        retry

    :raises: :class:`boto.exception.BotoServerError`
    :raises: :class:`exfm.cloudsearch.SearchServiceException`
    """
    def __init__(self, response, doc_service, sdf):
        self.response = response
        self.doc_service = doc_service
        self.sdf = sdf

        try:
            self.content = json.loads(response.content)
        except:
            boto.log.error('Error indexing documents.\nResponse Content:\n{}\n\n'
                'SDF:\n{}'.format(response.content, self.sdf))
            raise boto.exception.BotoServerError(self.response.status_code, '',
                body=response.content)

        self.status = self.content['status']
        if self.status == 'error':
            self.errors = [e.get('message') for e in self.content.get('errors',
                [])]
        else:
            self.errors = []

        self.adds = self.content['adds']
        self.deletes = self.content['deletes']
        self._check_num_ops('add', self.adds)
        self._check_num_ops('delete', self.deletes)

    def _check_num_ops(self, type_, response_num):
        """Raise exception if number of ops in response doesn't match commit

        :type type_: str
        :param type_: Type of commit operation: 'add' or 'delete'

        :type response_num: int
        :param response_num: Number of adds or deletes in the response.

        :raises: :class:`exfm.cloudsearch.SearchServiceException`
        """
        commit_num = len([d for d in self.doc_service.documents_batch
            if d['type'] == type_])

        if response_num != commit_num:
            raise CommitMismatchError(
                'Incorrect number of {}s returned. Commit: {} Respose: {}'\
                .format(type_, commit_num, response_num))
