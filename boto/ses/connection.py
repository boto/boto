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
import base64


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

    def _build_list_params(self, params, items, label):
        """Add an AWS API-compatible parameter list to a dictionary.

        :type params: dict
        :param params: The parameter dictionary

        :type items: list
        :param items: Items to be included in the list

        :type label: string
        :param label: The parameter list's name
        """
        if isinstance(items, str):
            items = [items]
        for i in range(1, len(items) + 1):
            params['%s.%d' % (label, i)] = items[i - 1]


    def _make_request(self, action, params=None):
        """Make a call to the SES API.

        :type action: string
        :param action: The API method to use (e.g. SendRawEmail)

        :type params: dict
        :param params: Parameters that will be sent as POST data with the API
                       call.
        """
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        params = params or {}
        params['Action'] = action
        response = super(SESConnection, self).make_request(
            'POST',
            '/',
            headers=headers,
            data=urllib.urlencode(params)
        )
        body = response.read()
        if response.status == 200:
            list_markers = ('VerifiedEmailAddresses', 'SendDataPoints')
            e = boto.jsonresponse.Element(list_marker=list_markers)
            h = boto.jsonresponse.XmlHandler(e, None)
            h.parse(body)
            return e
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)


    def send_email(self, source, subject, body, to_addresses, cc_addresses=None,
                   bcc_addresses=None, format='text'):
        """Composes an email message based on input data, and then immediately
        queues the message for sending.

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

        :type format: string
        :param format: The format of the message's body, must be either "text"
                       or "html".

        """
        params = {
            'Source': source,
            'Message.Subject.Data': subject,
        }

        format = format.lower().strip()
        if format == 'html':
            params['Message.Body.Html.Data'] = body
        elif format == 'text':
            params['Message.Body.Text.Data'] = body
        else:
            raise ValueError("'format' argument must be 'text' or 'html'")

        self._build_list_params(params, to_addresses,
                               'Destination.ToAddresses.member')
        if cc_addresses:
            self._build_list_params(params, cc_addresses,
                                   'Destination.CcAddresses.member')

        if bcc_addresses:
            self._build_list_params(params, bcc_addresses,
                                   'Destination.BccAddresses.member')

        return self._make_request('SendEmail', params)

    def send_raw_email(self, source, raw_message, destinations=None):
        """Sends an email message, with header and content specified by the
        client. The SendRawEmail action is useful for sending multipart MIME
        emails, with attachments or inline content. The raw text of the message
        must comply with Internet email standards; otherwise, the message
        cannot be sent.

        :type source: string
        :param source: The sender's email address.

        :type raw_message: string
        :param raw_message: The raw text of the message. The client is
          responsible for ensuring the following:

          - Message must contain a header and a body, separated by a blank line.
          - All required header fields must be present.
          - Each part of a multipart MIME message must be formatted properly.
          - MIME content types must be among those supported by Amazon SES.
            Refer to the Amazon SES Developer Guide for more details.
          - Content must be base64-encoded, if MIME requires it.

        :type destinations: list of strings or string
        :param destinations: A list of destinations for the message.

        """
        params = {
            'Source': source,
            'RawMessage.Data': base64.b64encode(raw_message),
        }

        self._build_list_params(params, destinations,
                               'Destinations.member')

        return self._make_request('SendRawEmail', params)

    def list_verified_email_addresses(self):
        """Fetch a list of the email addresses that have been verified.

        :rtype: dict
        :returns: A ListVerifiedEmailAddressesResponse structure. Note that
                  keys must be unicode strings.
        """
        return self._make_request('ListVerifiedEmailAddresses')

    def get_send_quota(self):
        """Fetches the user's current activity limits.

        :rtype: dict
        :returns: A GetSendQuotaResponse structure. Note that keys must be
                  unicode strings.
        """
        return self._make_request('GetSendQuota')

    def get_send_statistics(self):
        """Fetches the user's sending statistics. The result is a list of data
        points, representing the last two weeks of sending activity.

        Each data point in the list contains statistics for a 15-minute
        interval.

        :rtype: dict
        :returns: A GetSendStatisticsResponse structure. Note that keys must be
                  unicode strings.
        """
        return self._make_request('GetSendStatistics')

    def delete_verified_email_address(self, email_address):
        """Deletes the specified email address from the list of verified
        addresses.

        :type email_adddress: string
        :param email_address: The email address to be removed from the list of
                              verified addreses.

        :rtype: dict
        :returns: A DeleteVerifiedEmailAddressResponse structure. Note that
                  keys must be unicode strings.
        """
        return self._make_request('DeleteVerifiedEmailAddress', {
            'EmailAddress': email_address,
        })

    def verify_email_address(self, email_address):
        """Verifies an email address. This action causes a confirmation email
        message to be sent to the specified address.

        :type email_adddress: string
        :param email_address: The email address to be verified.

        :rtype: dict
        :returns: A VerifyEmailAddressResponse structure. Note that keys must
                  be unicode strings.
        """
        return self._make_request('VerifyEmailAddress', {
            'EmailAddress': email_address,
        })

