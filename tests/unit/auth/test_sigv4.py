# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
import copy
import pickle
import os
from tests.compat import unittest, mock
from tests.unit import MockServiceWithConfigTestCase

from boto.auth import HmacAuthV4Handler
from boto.auth import S3HmacAuthV4Handler
from boto.auth import detect_potential_s3sigv4
from boto.auth import detect_potential_sigv4
from boto.connection import HTTPRequest
from boto.provider import Provider
from boto.regioninfo import RegionInfo


class TestSigV4Handler(unittest.TestCase):
    def setUp(self):
        self.provider = mock.Mock()
        self.provider.access_key = 'access_key'
        self.provider.secret_key = 'secret_key'
        self.request = HTTPRequest(
            'POST', 'https', 'glacier.us-east-1.amazonaws.com', 443,
            '/-/vaults/foo/archives', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')

    def test_not_adding_empty_qs(self):
        self.provider.security_token = None
        auth = HmacAuthV4Handler('glacier.us-east-1.amazonaws.com', mock.Mock(), self.provider)
        req = copy.copy(self.request)
        auth.add_auth(req)
        self.assertEqual(req.path, '/-/vaults/foo/archives')

    def test_inner_whitespace_is_collapsed(self):
        auth = HmacAuthV4Handler('glacier.us-east-1.amazonaws.com',
                                 mock.Mock(), self.provider)
        self.request.headers['x-amz-archive-description'] = 'two  spaces'
        self.request.headers['x-amz-quoted-string'] = '  "a   b   c" '
        headers = auth.headers_to_sign(self.request)
        self.assertEqual(headers, {'Host': 'glacier.us-east-1.amazonaws.com',
                                   'x-amz-archive-description': 'two  spaces',
                                   'x-amz-glacier-version': '2012-06-01',
                                   'x-amz-quoted-string': '  "a   b   c" '})
        # Note the single space between the "two spaces".
        self.assertEqual(auth.canonical_headers(headers),
                         'host:glacier.us-east-1.amazonaws.com\n'
                         'x-amz-archive-description:two spaces\n'
                         'x-amz-glacier-version:2012-06-01\n'
                         'x-amz-quoted-string:"a   b   c"')

    def test_canonical_query_string(self):
        auth = HmacAuthV4Handler('glacier.us-east-1.amazonaws.com',
                                 mock.Mock(), self.provider)
        request = HTTPRequest(
            'GET', 'https', 'glacier.us-east-1.amazonaws.com', 443,
            '/-/vaults/foo/archives', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')
        request.params['Foo.1'] = 'aaa'
        request.params['Foo.10'] = 'zzz'
        query_string = auth.canonical_query_string(request)
        self.assertEqual(query_string, 'Foo.1=aaa&Foo.10=zzz')

    def test_query_string(self):
        auth = HmacAuthV4Handler('sns.us-east-1.amazonaws.com',
                                 mock.Mock(), self.provider)
        params = {
            'Message': u'We \u2665 utf-8'.encode('utf-8'),
        }
        request = HTTPRequest(
            'POST', 'https', 'sns.us-east-1.amazonaws.com', 443,
            '/', None, params, {}, '')
        query_string = auth.query_string(request)
        self.assertEqual(query_string, 'Message=We%20%E2%99%A5%20utf-8')

    def test_canonical_uri(self):
        auth = HmacAuthV4Handler('glacier.us-east-1.amazonaws.com',
                                 mock.Mock(), self.provider)
        request = HTTPRequest(
            'GET', 'https', 'glacier.us-east-1.amazonaws.com', 443,
            'x/./././x .html', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')
        canonical_uri = auth.canonical_uri(request)
        # This should be both normalized & urlencoded.
        self.assertEqual(canonical_uri, 'x/x%20.html')

        auth = HmacAuthV4Handler('glacier.us-east-1.amazonaws.com',
                                 mock.Mock(), self.provider)
        request = HTTPRequest(
            'GET', 'https', 'glacier.us-east-1.amazonaws.com', 443,
            'x/./././x/html/', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')
        canonical_uri = auth.canonical_uri(request)
        # Trailing slashes should be preserved.
        self.assertEqual(canonical_uri, 'x/x/html/')

        request = HTTPRequest(
            'GET', 'https', 'glacier.us-east-1.amazonaws.com', 443,
            '/', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')
        canonical_uri = auth.canonical_uri(request)
        # There should not be two-slashes.
        self.assertEqual(canonical_uri, '/')

        # Make sure Windows-style slashes are converted properly
        request = HTTPRequest(
            'GET', 'https', 'glacier.us-east-1.amazonaws.com', 443,
            '\\x\\x.html', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')
        canonical_uri = auth.canonical_uri(request)
        self.assertEqual(canonical_uri, '/x/x.html')

    def test_credential_scope(self):
        # test the AWS standard regions IAM endpoint
        auth = HmacAuthV4Handler('iam.amazonaws.com',
                                 mock.Mock(), self.provider)
        request = HTTPRequest(
            'POST', 'https', 'iam.amazonaws.com', 443,
            '/', '/',
            {'Action': 'ListAccountAliases', 'Version': '2010-05-08'},
            {
                'Content-Length': '44',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Amz-Date': '20130808T013210Z'
            },
            'Action=ListAccountAliases&Version=2010-05-08')
        credential_scope = auth.credential_scope(request)
        region_name = credential_scope.split('/')[1]
        self.assertEqual(region_name, 'us-east-1')

        # test the AWS GovCloud region IAM endpoint
        auth = HmacAuthV4Handler('iam.us-gov.amazonaws.com',
                                 mock.Mock(), self.provider)
        request = HTTPRequest(
            'POST', 'https', 'iam.us-gov.amazonaws.com', 443,
            '/', '/',
            {'Action': 'ListAccountAliases', 'Version': '2010-05-08'},
            {
                'Content-Length': '44',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Amz-Date': '20130808T013210Z'
            },
            'Action=ListAccountAliases&Version=2010-05-08')
        credential_scope = auth.credential_scope(request)
        region_name = credential_scope.split('/')[1]
        self.assertEqual(region_name, 'us-gov-west-1')

        # iam.us-west-1.amazonaws.com does not exist however this
        # covers the remaining region_name control structure for a
        # different region name
        auth = HmacAuthV4Handler('iam.us-west-1.amazonaws.com',
                                 mock.Mock(), self.provider)
        request = HTTPRequest(
            'POST', 'https', 'iam.us-west-1.amazonaws.com', 443,
            '/', '/',
            {'Action': 'ListAccountAliases', 'Version': '2010-05-08'},
            {
                'Content-Length': '44',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Amz-Date': '20130808T013210Z'
            },
            'Action=ListAccountAliases&Version=2010-05-08')
        credential_scope = auth.credential_scope(request)
        region_name = credential_scope.split('/')[1]
        self.assertEqual(region_name, 'us-west-1')

        # Test connections to custom locations, e.g. localhost:8080
        auth = HmacAuthV4Handler('localhost', mock.Mock(), self.provider,
                                 service_name='iam')

        request = HTTPRequest(
            'POST', 'http', 'localhost', 8080,
            '/', '/',
            {'Action': 'ListAccountAliases', 'Version': '2010-05-08'},
            {
                'Content-Length': '44',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Amz-Date': '20130808T013210Z'
            },
            'Action=ListAccountAliases&Version=2010-05-08')
        credential_scope = auth.credential_scope(request)
        timestamp, region, service, v = credential_scope.split('/')
        self.assertEqual(region, 'localhost')
        self.assertEqual(service, 'iam')

    def test_headers_to_sign(self):
        auth = HmacAuthV4Handler('glacier.us-east-1.amazonaws.com',
                                 mock.Mock(), self.provider)
        request = HTTPRequest(
            'GET', 'http', 'glacier.us-east-1.amazonaws.com', 80,
            'x/./././x .html', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')
        headers = auth.headers_to_sign(request)
        # Port 80 & not secure excludes the port.
        self.assertEqual(headers['Host'], 'glacier.us-east-1.amazonaws.com')

        request = HTTPRequest(
            'GET', 'https', 'glacier.us-east-1.amazonaws.com', 443,
            'x/./././x .html', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')
        headers = auth.headers_to_sign(request)
        # SSL port excludes the port.
        self.assertEqual(headers['Host'], 'glacier.us-east-1.amazonaws.com')

        request = HTTPRequest(
            'GET', 'https', 'glacier.us-east-1.amazonaws.com', 8080,
            'x/./././x .html', None, {},
            {'x-amz-glacier-version': '2012-06-01'}, '')
        headers = auth.headers_to_sign(request)
        # URL should include port.
        self.assertEqual(headers['Host'], 'glacier.us-east-1.amazonaws.com:8080')

    def test_region_and_service_can_be_overriden(self):
        auth = HmacAuthV4Handler('queue.amazonaws.com',
                                 mock.Mock(), self.provider)
        self.request.headers['X-Amz-Date'] = '20121121000000'

        auth.region_name = 'us-west-2'
        auth.service_name = 'sqs'
        scope = auth.credential_scope(self.request)
        self.assertEqual(scope, '20121121/us-west-2/sqs/aws4_request')

    def test_pickle_works(self):
        provider = Provider('aws', access_key='access_key',
                            secret_key='secret_key')
        auth = HmacAuthV4Handler('queue.amazonaws.com', None, provider)

        # Pickle it!
        pickled = pickle.dumps(auth)

        # Now restore it
        auth2 = pickle.loads(pickled)
        self.assertEqual(auth.host, auth2.host)

    def test_bytes_header(self):
        auth = HmacAuthV4Handler('glacier.us-east-1.amazonaws.com',
                                 mock.Mock(), self.provider)
        request = HTTPRequest(
            'GET', 'http', 'glacier.us-east-1.amazonaws.com', 80,
            'x/./././x .html', None, {},
            {'x-amz-glacier-version': '2012-06-01', 'x-amz-hash': b'f00'}, '')
        canonical = auth.canonical_request(request)

        self.assertIn('f00', canonical)


class TestS3HmacAuthV4Handler(unittest.TestCase):
    def setUp(self):
        self.provider = mock.Mock()
        self.provider.access_key = 'access_key'
        self.provider.secret_key = 'secret_key'
        self.provider.security_token = 'sekret_tokens'
        self.request = HTTPRequest(
            'GET', 'https', 's3-us-west-2.amazonaws.com', 443,
            '/awesome-bucket/?max-keys=0', None, {},
            {}, ''
        )
        self.awesome_bucket_request = HTTPRequest(
            method='GET',
            protocol='https',
            host='awesome-bucket.s3-us-west-2.amazonaws.com',
            port=443,
            path='/',
            auth_path=None,
            params={
                'max-keys': 0,
            },
            headers={
                'User-Agent': 'Boto',
                'X-AMZ-Content-sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                'X-AMZ-Date': '20130605T193245Z',
            },
            body=''
        )
        self.auth = S3HmacAuthV4Handler(
            host='awesome-bucket.s3-us-west-2.amazonaws.com',
            config=mock.Mock(),
            provider=self.provider,
            region_name='s3-us-west-2'
        )

    def test_clean_region_name(self):
        # Untouched.
        cleaned = self.auth.clean_region_name('us-west-2')
        self.assertEqual(cleaned, 'us-west-2')

        # Stripped of the ``s3-`` prefix.
        cleaned = self.auth.clean_region_name('s3-us-west-2')
        self.assertEqual(cleaned, 'us-west-2')

        # Untouched (classic).
        cleaned = self.auth.clean_region_name('s3.amazonaws.com')
        self.assertEqual(cleaned, 's3.amazonaws.com')

        # Untouched.
        cleaned = self.auth.clean_region_name('something-s3-us-west-2')
        self.assertEqual(cleaned, 'something-s3-us-west-2')

    def test_region_stripping(self):
        auth = S3HmacAuthV4Handler(
            host='s3-us-west-2.amazonaws.com',
            config=mock.Mock(),
            provider=self.provider
        )
        self.assertEqual(auth.region_name, None)

        # What we wish we got.
        auth = S3HmacAuthV4Handler(
            host='s3-us-west-2.amazonaws.com',
            config=mock.Mock(),
            provider=self.provider,
            region_name='us-west-2'
        )
        self.assertEqual(auth.region_name, 'us-west-2')

        # What we actually get (i.e. ``s3-us-west-2``).
        self.assertEqual(self.auth.region_name, 'us-west-2')

    def test_determine_region_name(self):
        name = self.auth.determine_region_name('s3-us-west-2.amazonaws.com')
        self.assertEqual(name, 'us-west-2')

    def test_canonical_uri(self):
        request = HTTPRequest(
            'GET', 'https', 's3-us-west-2.amazonaws.com', 443,
            'x/./././x .html', None, {},
            {}, ''
        )
        canonical_uri = self.auth.canonical_uri(request)
        # S3 doesn't canonicalize the way other SigV4 services do.
        # This just urlencoded, no normalization of the path.
        self.assertEqual(canonical_uri, 'x/./././x%20.html')

    def test_determine_service_name(self):
        # What we wish we got.
        name = self.auth.determine_service_name(
            's3.us-west-2.amazonaws.com'
        )
        self.assertEqual(name, 's3')

        # What we actually get.
        name = self.auth.determine_service_name(
            's3-us-west-2.amazonaws.com'
        )
        self.assertEqual(name, 's3')

        # What we wish we got with virtual hosting.
        name = self.auth.determine_service_name(
            'bucket.s3.us-west-2.amazonaws.com'
        )
        self.assertEqual(name, 's3')

        # What we actually get with virtual hosting.
        name = self.auth.determine_service_name(
            'bucket.s3-us-west-2.amazonaws.com'
        )
        self.assertEqual(name, 's3')

    def test_add_auth(self):
        # The side-effects sideshow.
        self.assertFalse('x-amz-content-sha256' in self.request.headers)
        self.auth.add_auth(self.request)
        self.assertTrue('x-amz-content-sha256' in self.request.headers)
        the_sha = self.request.headers['x-amz-content-sha256']
        self.assertEqual(
            the_sha,
            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
        )

    def test_host_header(self):
        host = self.auth.host_header(
            self.awesome_bucket_request.host,
            self.awesome_bucket_request
        )
        self.assertEqual(host, 'awesome-bucket.s3-us-west-2.amazonaws.com')

    def test_canonical_query_string(self):
        qs = self.auth.canonical_query_string(self.awesome_bucket_request)
        self.assertEqual(qs, 'max-keys=0')

    def test_correct_handling_of_plus_sign(self):
        request = HTTPRequest(
            'GET', 'https', 's3-us-west-2.amazonaws.com', 443,
            'hello+world.txt', None, {},
            {}, ''
        )
        canonical_uri = self.auth.canonical_uri(request)
        # Ensure that things are properly quoted.
        self.assertEqual(canonical_uri, 'hello%2Bworld.txt')

        request = HTTPRequest(
            'GET', 'https', 's3-us-west-2.amazonaws.com', 443,
            'hello%2Bworld.txt', None, {},
            {}, ''
        )
        canonical_uri = self.auth.canonical_uri(request)
        # Verify double escaping hasn't occurred.
        self.assertEqual(canonical_uri, 'hello%2Bworld.txt')

    def test_mangle_path_and_params(self):
        request = HTTPRequest(
            method='GET',
            protocol='https',
            host='awesome-bucket.s3-us-west-2.amazonaws.com',
            port=443,
            # LOOK AT THIS PATH. JUST LOOK AT IT.
            path='/?delete&max-keys=0',
            auth_path=None,
            params={
                'key': 'why hello there',
                # This gets overwritten, to make sure back-compat is maintained.
                'max-keys': 1,
            },
            headers={
                'User-Agent': 'Boto',
                'X-AMZ-Content-sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                'X-AMZ-Date': '20130605T193245Z',
            },
            body=''
        )

        mod_req = self.auth.mangle_path_and_params(request)
        self.assertEqual(mod_req.path, '/?delete&max-keys=0')
        self.assertEqual(mod_req.auth_path, '/')
        self.assertEqual(mod_req.params, {
            'max-keys': '0',
            'key': 'why hello there',
            'delete': ''
        })

    def test_canonical_request(self):
        expected = """GET
/
max-keys=0
host:awesome-bucket.s3-us-west-2.amazonaws.com
user-agent:Boto
x-amz-content-sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
x-amz-date:20130605T193245Z

host;user-agent;x-amz-content-sha256;x-amz-date
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"""

        authed_req = self.auth.canonical_request(self.awesome_bucket_request)
        self.assertEqual(authed_req, expected)

        # Now the way ``boto.s3`` actually sends data.
        request = copy.copy(self.awesome_bucket_request)
        request.path = request.auth_path = '/?max-keys=0'
        request.params = {}
        expected = """GET
/
max-keys=0
host:awesome-bucket.s3-us-west-2.amazonaws.com
user-agent:Boto
x-amz-content-sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
x-amz-date:20130605T193245Z

host;user-agent;x-amz-content-sha256;x-amz-date
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"""

        # Pre-mangle it. In practice, this happens as part of ``add_auth``,
        # but that's a side-effect that's hard to test.
        request = self.auth.mangle_path_and_params(request)
        authed_req = self.auth.canonical_request(request)
        self.assertEqual(authed_req, expected)

    def test_non_string_headers(self):
        self.awesome_bucket_request.headers['Content-Length'] = 8
        canonical_headers = self.auth.canonical_headers(
            self.awesome_bucket_request.headers)
        self.assertEqual(
            canonical_headers,
            'content-length:8\n'
            'user-agent:Boto\n'
            'x-amz-content-sha256:e3b0c44298fc1c149afbf4c8996fb92427ae'
            '41e4649b934ca495991b7852b855\n'
            'x-amz-date:20130605T193245Z'
        )


class FakeS3Connection(object):
    def __init__(self, *args, **kwargs):
        self.host = kwargs.pop('host', None)

    @detect_potential_s3sigv4
    def _required_auth_capability(self):
        return ['nope']

    def _mexe(self, *args, **kwargs):
        pass


class FakeEC2Connection(object):
    def __init__(self, *args, **kwargs):
        self.region = kwargs.pop('region', None)

    @detect_potential_sigv4
    def _required_auth_capability(self):
        return ['nope']

    def _mexe(self, *args, **kwargs):
        pass


class TestS3SigV4OptIn(MockServiceWithConfigTestCase):
    connection_class = FakeS3Connection

    def test_sigv4_opt_out(self):
        # Default is opt-out.
        fake = FakeS3Connection(host='s3.amazonaws.com')
        self.assertEqual(fake._required_auth_capability(), ['nope'])

    def test_sigv4_non_optional(self):
        # Requires SigV4.
        for region in ['.cn-north', '.eu-central', '-eu-central']:
            fake = FakeS3Connection(host='s3' + region + '-1.amazonaws.com')
            self.assertEqual(
                fake._required_auth_capability(), ['hmac-v4-s3'])

    def test_sigv4_opt_in_config(self):
        # Opt-in via the config.
        self.config = {
            's3': {
                'use-sigv4': True,
            },
        }
        fake = FakeS3Connection()
        self.assertEqual(fake._required_auth_capability(), ['hmac-v4-s3'])

    def test_sigv4_opt_in_env(self):
        # Opt-in via the ENV.
        self.environ['S3_USE_SIGV4'] = True
        fake = FakeS3Connection(host='s3.amazonaws.com')
        self.assertEqual(fake._required_auth_capability(), ['hmac-v4-s3'])


class TestSigV4OptIn(MockServiceWithConfigTestCase):
    connection_class = FakeEC2Connection

    def setUp(self):
        super(TestSigV4OptIn, self).setUp()
        self.standard_region = RegionInfo(
            name='us-west-2',
            endpoint='ec2.us-west-2.amazonaws.com'
        )
        self.sigv4_region = RegionInfo(
            name='cn-north-1',
            endpoint='ec2.cn-north-1.amazonaws.com.cn'
        )

    def test_sigv4_opt_out(self):
        # Default is opt-out.
        fake = FakeEC2Connection(region=self.standard_region)
        self.assertEqual(fake._required_auth_capability(), ['nope'])

    def test_sigv4_non_optional(self):
        # Requires SigV4.
        fake = FakeEC2Connection(region=self.sigv4_region)
        self.assertEqual(fake._required_auth_capability(), ['hmac-v4'])

    def test_sigv4_opt_in_config(self):
        # Opt-in via the config.
        self.config = {
            'ec2': {
                'use-sigv4': True,
            },
        }
        fake = FakeEC2Connection(region=self.standard_region)
        self.assertEqual(fake._required_auth_capability(), ['hmac-v4'])

    def test_sigv4_opt_in_env(self):
        # Opt-in via the ENV.
        self.environ['EC2_USE_SIGV4'] = True
        fake = FakeEC2Connection(region=self.standard_region)
        self.assertEqual(fake._required_auth_capability(), ['hmac-v4'])
