# Copyright (c) 2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2011 Harry Marr http://hmarr.com/
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

from boto.connection import AWSAuthConnection
from boto.exception import BotoServerError
import boto
import boto.jsonresponse
import urllib


class SESConnection(AWSAuthConnection):

    ResponseError = BotoServerError
    DefaultHost = 'email.us-east-1.amazonaws.com'
    APIVersion = '2010-12-01'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 port=None, proxy=None, proxy_port=None,
                 host=DefaultHost, debug=0):
        AWSAuthConnection.__init__(self, host, aws_access_key_id,
                                   aws_secret_access_key, True, port, proxy,
                                   proxy_port, debug=debug)

    def _required_auth_capability(self):
        return ['ses']

    def build_list_params(self, params, items, label):
        if isinstance(items, str):
            items = [items]
        for i in range(1, len(items) + 1):
            params['%s.%d' % (label, i)] = items[i - 1]

    def send_email(self, source, subject, body, to_addresses, cc_addresses=None,
                   bcc_addresses=None, format='text'):
        """
        :type source: string
        :param source: The sender's email address.

        :type subject: string
        :param subject: The subject of the message: A short summary of the
                        content, which will appear in the recipient's inbox.

        :type body: string
        :param body: The message body.

        :type to_addresses: list of strings or string
        :param to_addresses: The To: field(s) of the message.

        :type cc_addresses: list of strings or string
        :param cc_addresses: The CC: field(s) of the message.

        :type bcc_addresses: list of strings or string
        :param bcc_addresses: The BCC: field(s) of the message.

        """
        params = {
            'Action': 'SendEmail',
            'Source': source,
            'Message.Subject.Data': subject,
            'Message.Body.Text.Data': body,
        }
        self.build_list_params(params, to_addresses,
                               'Destination.ToAddresses.member')
        if cc_addresses:
            self.build_list_params(params, cc_addresses,
                                   'Destination.CcAddresses.member')

        if bcc_addresses:
            self.build_list_params(params, bcc_addresses,
                                   'Destination.BccAddresses.member')


        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = self.make_request('POST', '/', headers=headers,
                                     data=urllib.urlencode(params))
        body = response.read()
        if response.status == 200:
            e = boto.jsonresponse.Element()
            h = boto.jsonresponse.XmlHandler(e, None)
            h.parse(body)
            return e
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)

