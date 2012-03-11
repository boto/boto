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
import sys
import os
import types

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

try:
    from urllib.parse import quote, quote_plus, unquote
except ImportError:
    from urllib import quote, quote_plus, unquote

try:
    from urllib.request import urlopen, Request, build_opener, install_opener
except ImportError:
    from urllib2 import urlopen, Request

try:
    from urllib.request import HTTPPasswordMgrWithDefaultRealm
except ImportError:
    from urllib2 import HTTPPasswordMgrWithDefaultRealm

try:
    from urllib.request import HTTPBasicAuthHandler, HTTPError
except ImportError:
    from urllib2 import HTTPBasicAuthHandler

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

try:
    import http.client as httplib
except ImportError:
    import httplib

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

if PY3:
    import io
    StringIO = io.StringIO
else:
    import StringIO
    StringIO = StringIO.StringIO

if PY3:
    raw_input = input
else:
    raw_input = raw_input
    
try:
    # Python 3.x
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email.mime.text import MIMEText
    from email.utils import formatdate
    import email.encoders as Encoders
    unicode = str
except ImportError:
    # Python 2.x
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEBase import MIMEBase
    from email.MIMEText import MIMEText
    from email.utils import formatdate
    from email import Encoders


def on_appengine():
    return all(key in os.environ for key in ('USER_IS_ADMIN',
                                             'CURRENT_VERSION_ID',
                                             'APPLICATION_ID'))


def httplib_ssl_hack(port):
    return ((on_appengine and sys.version[:3] == '2.5') or
            sys.version.startswith('3') or
            sys.version[:3] in ('2.6', '2.7')) and port == 443
