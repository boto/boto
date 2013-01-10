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

import requests
from .auth import SigV2Auth
from .credentials import get_credentials
from .dictresponse import Element, XmlHandler


class Service(object):
    """
    This is a simple example service that connects to the EC2 endpoint
    and supports a single request (DescribeInstances) to show how to
    use the requests-based code rather than the standard boto code which
    is based on httplib.  At the moment, the only auth mechanism
    supported is SigV2.
    """

    def __init__(self, host='https://ec2.us-east-1.amazonaws.com',
                 path='/', api_version='2012-03-01', persona=None):
        self.credentials = get_credentials(persona)
        self.auth = SigV2Auth(self.credentials, api_version=api_version)
        self.host = host
        self.path = path

    def get_response(self, params, list_marker=None):
        r = requests.post(self.host, params=params,
                          hooks={'args': self.auth.add_auth})
        r.encoding = 'utf-8'
        body = r.text.encode('utf-8')
        e = Element(list_marker=list_marker, pythonize_name=True)
        h = XmlHandler(e, self)
        h.parse(body)
        return e

    def build_list_params(self, params, items, label):
        if isinstance(items, str):
            items = [items]
        for i in range(1, len(items) + 1):
            params['%s.%d' % (label, i)] = items[i - 1]

    def describe_instances(self, instance_ids=None):
        params = {}
        if instance_ids:
            self.build_list_params(params, instance_ids, 'InstanceId')
        return self.get_response(params)
