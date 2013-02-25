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
import os
from six.moves import configparser
from boto.compat import json
import requests


class Credentials(object):
    """
    Holds the credentials needed to authenticate requests.  In addition
    the Credential object knows how to search for credentials and how
    to choose the right credentials when multiple credentials are found.
    """

    def __init__(self, access_key=None, secret_key=None, token=None):
        self.access_key = access_key
        self.secret_key = secret_key
        self.token = token


def _search_md(url='http://169.254.169.254/latest/meta-data/iam/'):
    d = {}
    try:
        r = requests.get(url, timeout=.1)
        if r.content:
            fields = r.content.split('\n')
            for field in fields:
                if field.endswith('/'):
                    d[field[0:-1]] = get_iam_role(url + field)
                else:
                    val = requests.get(url + field).content
                    if val[0] == '{':
                        val = json.loads(val)
                    else:
                        p = val.find('\n')
                        if p > 0:
                            val = r.content.split('\n')
                    d[field] = val
    except (requests.Timeout, requests.ConnectionError):
        pass
    return d


def search_metadata(**kwargs):
    credentials = None
    metadata = _search_md()
    # Assuming there's only one role on the instance profile.
    if metadata:
        metadata = metadata['iam']['security-credentials'].values()[0]
        credentials = Credentials(metadata['AccessKeyId'],
                                  metadata['SecretAccessKey'],
                                  metadata['Token'])
    return credentials


def search_environment(**kwargs):
    """
    Search for credentials in explicit environment variables.
    """
    credentials = None
    access_key = os.environ.get(kwargs['access_key_name'].upper(), None)
    secret_key = os.environ.get(kwargs['secret_key_name'].upper(), None)
    if access_key and secret_key:
        credentials = Credentials(access_key, secret_key)
    return credentials


def search_file(**kwargs):
    """
    If the 'AWS_CREDENTIAL_FILE' environment variable exists, parse that
    file for credentials.
    """
    credentials = None
    if 'AWS_CREDENTIAL_FILE' in os.environ:
        persona = kwargs.get('persona', 'default')
        access_key_name = kwargs['access_key_name']
        secret_key_name = kwargs['secret_key_name']
        access_key = secret_key = None
        path = os.getenv('AWS_CREDENTIAL_FILE')
        path = os.path.expandvars(path)
        path = os.path.expanduser(path)
        cp = configparser.RawConfigParser()
        cp.read(path)
        if not cp.has_section(persona):
            raise ValueError('Persona: %s not found' % persona)
        if cp.has_option(persona, access_key_name):
            access_key = cp.get(persona, access_key_name)
        else:
            access_key = None
        if cp.has_option(persona, secret_key_name):
            secret_key = cp.get(persona, secret_key_name)
        else:
            secret_key = None
        if access_key and secret_key:
            credentials = Credentials(access_key, secret_key)
    return credentials


def search_boto_config(**kwargs):
    """
    Look for credentials in boto config file.
    """
    credentials = access_key = secret_key = None
    if 'BOTO_CONFIG' in os.environ:
        paths = [os.environ['BOTO_CONFIG']]
    else:
        paths = ['/etc/boto.cfg', '~/.boto']
    paths = [os.path.expandvars(p) for p in paths]
    paths = [os.path.expanduser(p) for p in paths]
    cp = configparser.RawConfigParser()
    cp.read(paths)
    if cp.has_section('Credentials'):
        access_key = cp.get('Credentials', 'aws_access_key_id')
        secret_key = cp.get('Credentials', 'aws_secret_access_key')
    if access_key and secret_key:
        credentials = Credentials(access_key, secret_key)
    return credentials

AllCredentialFunctions = [search_environment,
                          search_file,
                          search_boto_config,
                          search_metadata]


def get_credentials(persona='default'):
    for cred_fn in AllCredentialFunctions:
        credentials = cred_fn(persona=persona,
                              access_key_name='access_key',
                              secret_key_name='secret_key')
        if credentials:
            break
    return credentials
