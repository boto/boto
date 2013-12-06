# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
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

"""
Provides NotificationMessage and Event classes, with utility methods, for
implementations of the Mechanical Turk Notification API.
"""

import hmac
try:
    from hashlib import sha1 as sha
except ImportError:
    import sha
import base64
import re
import email
from datetime import datetime
from dateutil import tz

class NotificationMessage:

    NOTIFICATION_WSDL = "http://mechanicalturk.amazonaws.com/AWSMechanicalTurk/2006-05-05/AWSMechanicalTurkRequesterNotification.wsdl"
    NOTIFICATION_VERSION = '2006-05-05'

    SERVICE_NAME = "AWSMechanicalTurkRequesterNotification"
    OPERATION_NAME = "Notify"

    EVENT_PATTERN = r"Event\.(?P<n>\d+)\.(?P<param>\w+)"
    EVENT_RE = re.compile(EVENT_PATTERN)

    def __init__(self, d):
        """
        Constructor; expects parameter d to be a dict of string parameters from a REST transport notification message
        """
        self.signature = d['Signature'] # vH6ZbE0NhkF/hfNyxz2OgmzXYKs=
        self.timestamp = d['Timestamp'] # 2006-05-23T23:22:30Z
        self.version = d['Version'] # 2006-05-05
        assert d['method'] == NotificationMessage.OPERATION_NAME, "Method should be '%s'" % NotificationMessage.OPERATION_NAME

        # Build Events
        self.events = []
        events_dict = {}
        if 'Event' in d:
            # TurboGears surprised me by 'doing the right thing' and making { 'Event': { '1': { 'EventType': ... } } } etc.
            events_dict = d['Event']
        else:
            for k in d:
                v = d[k]
                if k.startswith('Event.'):
                    ed = NotificationMessage.EVENT_RE.search(k).groupdict()
                    n = int(ed['n'])
                    param = str(ed['param'])
                    if n not in events_dict:
                        events_dict[n] = {}
                    events_dict[n][param] = v
        for n in events_dict:
            self.events.append(Event(events_dict[n]))

    def verify(self, secret_key):
        """
        Verifies the authenticity of a notification message.

        *** As of September 2012, Amazon modified the 2012-03-25
            API such that it has now deprecated the REST and SOAP
            notification protocols; and to inform us of that fact
            they are no longer signing their REST and SOAP notification 
            messages. The signature keyword now instead returns:
                Signature: u'DEPRECATED'
            So we are now always returning True in this case so
            as not to break existing code. ***

        TODO: This is doing a form of authentication and
              this functionality should really be merged
              with the pluggable authentication mechanism
              at some point.
        """
        if self.signature == u'DEPRECATED':
            return True

        verification_input = NotificationMessage.SERVICE_NAME
        verification_input += NotificationMessage.OPERATION_NAME
        verification_input += self.timestamp
        h = hmac.new(key=secret_key, digestmod=sha)
        h.update(verification_input)
        signature_calc = base64.b64encode(h.digest())
        return self.signature == signature_calc

class NotificationEmail:

    EVENT_PATTERN = r"^\s*(?P<key>[a-zA-Z\s]+[a-zA-Z]+)\s*:\s*(?P<value>[a-zA-Z0-9\-:\s]+[a-zA-Z0-9]+)\s*$"
    EVENT_RE = re.compile(EVENT_PATTERN)
    BLANK_PATTERN = r"^\s*$"
    BLANK_RE = re.compile(BLANK_PATTERN)

    def __init__(self, fp):
        """
        Constructor; expects parameter d to be a file pointer to an email message, usually stdin.
        """

        msg = email.message_from_file(fp)
        for part in msg.walk():
            if part.get_content_type() != 'text/plain':
                continue

            # Build Events
            self.events = []
            events_dict = {}
            kvFound = False
            for line in part.get_payload(decode=True).split('\n'):
                # Search for MTurk key-value pairs
                kv = NotificationEmail.EVENT_RE.search(line)
                # Search for blank line
                bl = NotificationEmail.BLANK_RE.search(line)

                if kv:
                    kvFound = True
                    key = str(kv.group('key'))
                    value = str(kv.group('value'))
                    events_dict[key] = value
                elif kvFound and bl:
                    kvFound = False
                    self.events.append(Event(events_dict))

class Event:
    def __init__(self, d):
        # If REST notification
        if 'EventType' in d:
            self.event_type = d['EventType']
            self.event_time_str = d['EventTime']
            self.hit_type = d['HITTypeId']
            self.hit_id = d['HITId']
            if 'AssignmentId' in d:   # Not present in all event types
                self.assignment_id = d['AssignmentId']
        # Else, if email notification
        elif 'Event Type' in d:
            self.event_type = d['Event Type']
            self.event_time_str = d['Event Time']
            self.hit_type = d['HIT Type ID']
            self.hit_id = d['HIT ID']
            if 'Assignment ID' in d:   # Not present in all event types
                self.assignment_id = d['Assignment ID']

        # Build self.event_time local datetime from UTC string self.event_time_str
        dtmturk = datetime.strptime(self.event_time_str, '%Y-%m-%dT%H:%M:%SZ')
        self.event_time = dtmturk.replace(tzinfo=tz.tzutc()).astimezone(tz.tzlocal())

    def __repr__(self):
        return "<boto.mturk.notification.Event: %s for HIT # %s>" % (self.event_type, self.hit_id)
