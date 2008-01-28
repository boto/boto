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

#
# Parts of this code were copied or derived from sample code supplied by AWS.
# The following notice applies to that code.
#
#  This software code is made available "AS IS" without warranties of any
#  kind.  You may copy, display, modify and redistribute the software
#  code either by itself or as incorporated into your code; provided that
#  you do not remove any proprietary notices.  Your use of this software
#  code is at your own risk and you waive any claim against Amazon
#  Digital Services, Inc. or its affiliates with respect to your use of
#  this software code. (c) 2006 Amazon Digital Services, Inc. or its
#  affiliates.

"""
Some handy utility functions used by several classes.
"""

import base64
import hmac
import re
import sha
import urllib, urllib2
import imp
import popen2, os, StringIO

METADATA_PREFIX = 'x-amz-meta-'
AMAZON_HEADER_PREFIX = 'x-amz-'

# generates the aws canonical string for the given parameters
def canonical_string(method, path, headers, expires=None):
    interesting_headers = {}
    for key in headers:
        lk = key.lower()
        if lk in ['content-md5', 'content-type', 'date'] or lk.startswith(AMAZON_HEADER_PREFIX):
            interesting_headers[lk] = headers[key].strip()

    # these keys get empty strings if they don't exist
    if not interesting_headers.has_key('content-type'):
        interesting_headers['content-type'] = ''
    if not interesting_headers.has_key('content-md5'):
        interesting_headers['content-md5'] = ''

    # just in case someone used this.  it's not necessary in this lib.
    if interesting_headers.has_key('x-amz-date'):
        interesting_headers['date'] = ''

    # if you're using expires for query string auth, then it trumps date
    # (and x-amz-date)
    if expires:
        interesting_headers['date'] = str(expires)

    sorted_header_keys = interesting_headers.keys()
    sorted_header_keys.sort()

    buf = "%s\n" % method
    for key in sorted_header_keys:
        if key.startswith(AMAZON_HEADER_PREFIX):
            buf += "%s:%s\n" % (key, interesting_headers[key])
        else:
            buf += "%s\n" % interesting_headers[key]

    # don't include anything after the first ? in the resource...
    buf += "%s" % path.split('?')[0]

    # ...unless there is an acl or torrent parameter
    if re.search("[&?]acl($|=|&)", path):
        buf += "?acl"
    elif re.search("[&?]logging($|=|&)", path):
        buf += "?logging"
    elif re.search("[&?]torrent($|=|&)", path):
        buf += "?torrent"

    return buf

# computes the base64'ed hmac-sha hash of the canonical string and the secret
# access key, optionally urlencoding the result
def encode(aws_secret_access_key, str, urlencode=False):
    b64_hmac = base64.encodestring(hmac.new(aws_secret_access_key, str, sha).digest()).strip()
    if urlencode:
        return urllib.quote_plus(b64_hmac)
    else:
        return b64_hmac

def merge_meta(headers, metadata):
    final_headers = headers.copy()
    for k in metadata.keys():
        final_headers[METADATA_PREFIX + k] = metadata[k]

    return final_headers

def get_aws_metadata(headers):
    metadata = {}
    for hkey in headers.keys():
        if hkey.lower().startswith(METADATA_PREFIX):
            metadata[hkey[len(METADATA_PREFIX):]] = headers[hkey]
            del headers[hkey]
    return metadata

def get_instance_metadata(version='latest'):
    metadata = {}
    try:
        url = 'http://169.254.169.254/%s/meta-data/' % version
        s = urllib.urlopen(url)
        md_fields = s.read().split('\n')
        for md in md_fields:
            md_url = url + md
            s = urllib.urlopen(md_url)
            val = s.read()
            if val.find('\n') > 0:
                val = val.split('\n')
            metadata[md] = val
    except:
        print 'problem reading metadata'
    return metadata

def get_instance_userdata(version='latest', sep=None):
    user_data = None
    try:
        url = 'http://169.254.169.254/%s/user-data/' % version
        s = urllib.urlopen(url)
        user_data = s.read()
        if sep:
            l = user_data.split(sep)
            user_data = {}
            for nvpair in l:
                t = nvpair.split('=')
                user_data[t[0].strip()] = t[1].strip()
    except:
        print 'problem reading metadata'
    return user_data
    
def get_instance_userdata_raw(version='latest'):
    user_data = None
    try:
        url = 'http://169.254.169.254/%s/user-data/' % version
        s = urllib.urlopen(url)
        user_data = s.read()
    except:
        print 'problem reading metadata'
    return user_data
    
def find_class(module_name, class_name):
    modules = module_name.split('.')
    path = None
    for module_name in modules:
        fp, pathname, description = imp.find_module(module_name, path)
        module = imp.load_module(module_name, fp, pathname, description)
        if hasattr(module, '__path__'):
            path = module.__path__
    return getattr(module, class_name)
    
def update_dme(username, password, dme_id, ip_address):
    """
    Update your Dynamic DNS record with DNSMadeEasy.com
    """
    dme_url = 'https://www.dnsmadeeasy.com/servlet/updateip'
    dme_url += '?username=%s&password=%s&id=%s&ip=%s'
    s = urllib2.urlopen(dme_url % (username, password, dme_id, ip_address))
    return s.read()

class ShellCommand(object):

    def __init__(self, command, log_fp=None):
        self.exit_code = 0
        self.command = command
        if log_fp:
            self.log_fp = log_fp
        else:
            self.log_fp = StringIO.StringIO()
        self.run()

    def run(self):
        self.log_fp.write('running:\n%s\n' % self.command)
        p = popen2.Popen4(self.command)
        status = p.wait()
        self.log_fp.write(p.fromchild.read())
        self.log_fp.write('\n')
        self.exit_code = os.WEXITSTATUS(status)
        return self.exit_code

    def setReadOnly(self, value):
        raise AttributeError

    def getStatus(self):
        return self.exit_code

    status = property(getStatus, setReadOnly, None, 'The exit code for the command')

    def getOutput(self):
        return self.log_fp.getvalue()

    output = property(getOutput, setReadOnly, None, 'The STDIN and STDERR output of the command')
    
