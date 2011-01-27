# Copyright (c) 2011 Daniel Rhodes <rhodes.daniel@gmail.com>
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

import unittest
import time
from boto.ses.connection import SESConnection
from boto.ses.exception import SESResponseError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class SESConnectionTest (unittest.TestCase):
    
    def get_suite_description(self):
        return 'SES connection test suite'

    def setUp(self):
        self.conn = SESConnection()
        self.test_email = 'test@testemail.com'
    
    def test_1_connection(self):
        """ Tests insantiating basic connection """
        
        c = SESConnection()
        assert c
    
    def test_2_get_send_statistics(self):
        """ Tests retrieving send statistics """
        
        assert self.conn.get_send_statistics()
        
    def test_3_get_send_quota(self):
        """ Tests retrieving send quota """
        
        assert self.conn.get_send_quota()
        
    def test_4_get_verified_emails(self):
        """ Tests retrieving list of verified emails """
        
        assert self.conn.get_verified_emails()
        
    def test_5_verify_email_address(self):
        """ Tests verifying email address """
        
        assert self.conn.verify_email_address(email=self.test_email)
    
    def test_6_send_email(self):
        """ Tests sending an email """
        
        assert self.conn.send_email(source=self.test_email,
                     subject='Test',
                     message='Test Message',
                     to='self.test_email')
        
        # Email with cc and bcc
        assert self.conn.send_email(source=self.test_email, 
                         subject='Test', 
                         message='Test Message', 
                         to=[self.test_email], 
                         cc=[self.test_email],
                         bcc=[self.test_email])
                        
    def test_7_send_raw_email(self):
        """ Tests sending a raw email """
        
        assert self.conn.send_raw_email(source=self.test_email,
                         message=self._create_raw_email_message())
    def test_8_delete_verified_email(self):
        """ Tests deleting verified email """
        
        assert self.conn.delete_verified_email(email=self.test_email)
        
    def _create_raw_email_message(self):
        """ Creates a test mime-type email using native Email class """
        
        me = self.test_email
        you = self.test_email

        # Create message container - the correct MIME type is multipart/alternative.
        msg = MIMEMultipart('alternative')
        msg['From'] = me
        msg['To'] = you
        msg['Subject'] = "Link"

        # Create the body of the message (a plain-text and an HTML version).
        text = "Hi!\nHow are you?\nHere is the link you wanted:\nhttp://www.python.org"
        html = """\
        <html>
          <head></head>
          <body>
            <p>Hi!<br>
               How are you?<br>
               Here is the <a href="http://www.python.org">link</a> you wanted.
            </p>
          </body>
        </html>
        """

        # Record the MIME types of both parts - text/plain and text/html.
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(part1)
        msg.attach(part2)
    
        return msg