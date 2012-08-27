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

class Job(object):
    def __init__(self, vault, job_id):
        self.vault = vault
        self.job_id = job_id

    def make_request(self, verb, resource, headers=None,
                   data='', ok_responses=(200,)):
        resource = "jobs/%s/%s" % (urllib.quote(self.job_id), resource)
        return self.vault.make_request(verb,resource, headers, data,ok_responses)

    def get_output(self, range_from=None, range_to=None):
        """
        Get the output of a job. In the case of an archive retrieval
        job this will be the data of the archive itself.

        Optionally, a range can be specified to only get a part of the data.

        
        :type range_from: int
        :param range_from: The first byte to get

        :type range_to: int
        :param range_to: The last byte to get

        :rtype: :class:`boto.connection.HttpResponse
        :return: A response object from which the output can be read.
        """
        headers = {}
        if range_from is not None or range_to is not None:
            assert range_from is not None and range_to is not None, "If you specify one of range_from or range_to you must specify the other"
            headers["Range"] = "bytes %d-%d" % (range_from, range_to)
        response = self.make_request("GET", "output", headers=headers)
        return response
