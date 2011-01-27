# Copyright (c) 2011 Daniel Rhodes
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

import boto
import boto.jsonresponse
from boto.connection import AWSAuthConnection
import exception
import uuid
import urllib
import base64

try:
	import json
except ImportError:
	import simplejson as json

class SESConnection(AWSAuthConnection):
	
	DefaultHost = 'email.us-east-1.amazonaws.com'
	Version = '2010-12-01'
	XMLNameSpace = 'https://ses.amazonaws.com/doc/2010-03-31/'
	
	def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
				 port=None, proxy=None, proxy_port=None,
				 host=DefaultHost, debug=0):
		AWSAuthConnection.__init__(self, host,
				aws_access_key_id, aws_secret_access_key,
				True, port, proxy, proxy_port, debug=debug)
	
	def _required_auth_capability(self):
		return ['hmac-v3']
	
	def _process_response(self, response):
		"""
		Process response from API
		:type response: HTTPLib response
		:param response: Response from request
		
		:type return: dict
		:param return: parsed response from API
		"""
		body = response.read()
		if response.status > 200:
			boto.log.error('%s %s' % (response.status, response.reason))
			boto.log.error('%s' % body)
			raise exception.SESResponseError(response.status,
										   response.reason,
										   body)
		list_markers = ('VerifiedEmailAddresses', 'SendDataPoints')
		e = boto.jsonresponse.Element(list_marker=list_markers)
		h = boto.jsonresponse.XmlHandler(e, None)
		h.parse(body)
		return e
	
	def _format_destinations(self, destination, prefix=None):
		"""
		Format destinations according to Destination.<prefix>.member.<n>
		
		:type destination: string or list
		:param destination: destination emails
		
		:type prefix: string or NoneType
		:param prefix: Name of the destination (e.g. ToAddresses, CcAddresses, BccAddresses)
		
		:type return: Dict
		:param return: formatted dictionary with destination addresses
		"""
		destinations = {}
		if prefix is not None:
			template = 'Destination.%s.member.%%s' % str(prefix)
		else:
			template = 'Destinations.member.%s'
		if type(destination) == str:
			destinations[template % 1] = destination
		else:
			for i, email_addr in enumerate(destination):
				destinations[template % i] = email_addr
			else:
				raise ValueError, 'No destinations.'
		return destinations
		
	def _make_request(self, action, params=None):
		"""
		Custom request method. SES uses a faux REST/RPC like interface. 
		
		:type action: string
		:param action: API action
		
		:type params: Dict
		:param params: Additional params that are added to the API request.
		
		:type return: type returned from _process_response
		:param return: Formatted response
		"""
		params = params or {}
		params['Action'] = action
		headers = {'Content-Type': 'application/x-www-form-urlencoded'}
		path = '/%s' % self.Version
		pairs = []
		for key, val in params.iteritems():
			if val is None: continue
			pairs.append(key + '=' + urllib.quote(str(val)))
		data = '&' . join(pairs)
		response = AWSAuthConnection.make_request(self, 'POST', path, headers, data)
		return self._process_response(response)
		
	def get_send_statistics(self):
		"""
		Return account statistics
		
		:type return: type returned from _process_response
		:param return: Formatted response
		"""
		return self._make_request(action='GetSendStatistics')
		
	def get_send_quota(self):
		"""
		Return account quota
		
		:type return: type returned from _process_response
		:param return: Formatted response
		"""
		return self._make_request(action='GetSendQuota')
		
	def get_verified_emails(self):
		""" 
		Return the emails verified for use by this account
		
		:type return: type returned from _process_response
		:param return: Formatted response
		"""
		return self._make_request(action='ListVerifiedEmailAddresses')
		
	def verify_email_address(self, email):
		""" 
		Verify an email address for use by this account
		
		:type email: string
		:param email: Email address to be verified
		
		:type return: type returned from _process_response
		:param return: Formatted response
		"""
		return self._make_request(action='VerifyEmailAddress', params={
			'EmailAddress': email
		})
		
	def delete_verified_email(self, email):
		""" 
		Remove a verified email address used by this account 
		
		:type email: string
		:param string: Email address to be removed

		:type return: type returned from _process_response
		:param return: Formatted response
		"""
		return self._make_request(action='DeleteVerifiedEmailAddress', params={
			'EmailAddress': email
		})
		
	def send_email(self, source, subject, message, to, cc=None, bcc=None):
		"""
		Send an unformatted plain-text email
		
		:type source: string
		:param source: The verified email
		
		:type subject: string
		:param subject The subject of the message
		
		:type to:  string or list
		:param to: The destinations of the message
		
		:type cc: string or list
		:param cc: The carbon copy recipients
		
		:type bcc: string or list
		:param bcc: The blind carbon copy recipients
		
		:type return: type returned from _process_response
		:param return: Formatted response
		"""
		params = {'Source': source,
				  'Message.Body.Text.Data': message,
				  'Message.Subject.Data': subject
		}
		params.update(self._format_destinations(destination=to, prefix='ToAddresses'))
		if cc is not None:
			params.update(self._format_destinations(destination=cc, prefix='CcAddresses'))
		if bcc is not None:
			params.update(self._format_destinations(destination=bcc, prefix='BccAddresses'))
		return self._make_request(action='SendEmail', params=params)
		
	def send_raw_email(self, source, message):
		"""
		Send a preformatted message
		
		:type source: string
		:param source: A verified email from this account
		
		:type message: Email
		:param message: A message in Python's native email type
		
		:type return: type returned from _process_response
		:param return: Formatted response
		"""
		params = {
				  'Source': source, 
				  'RawMessage.Data': base64.b64encode(message.as_string())
		}
		return self._make_request(action='SendRawEmail', params=params)