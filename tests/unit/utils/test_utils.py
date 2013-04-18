# Copyright (c) 2010 Robert Mela
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
import unittest
import hashlib
import hmac

try:
    from unittest import mock
except ImportError:
    import mock

from boto.utils import Password
from boto.utils import pythonize_name
from boto.utils import _build_instance_metadata_url
from boto.utils import retry_url


class TestPassword(unittest.TestCase):
    """Test basic password functionality"""

    def clstest(self, cls):
        """Insure that password.__eq__ hashes test value before compare."""
        password = cls('foo')
        self.assertNotEquals(password, 'foo')

        password.set('foo')
        hashed = str(password)
        self.assertEquals(password, 'foo')
        self.assertEquals(password.str, hashed)

        password = cls(hashed)
        self.assertNotEquals(password.str, 'foo')
        self.assertEquals(password, 'foo')
        self.assertEquals(password.str, hashed)

    def test_aaa_version_1_9_default_behavior(self):
        self.clstest(Password)

    def test_custom_hashclass(self):
        class SHA224Password(Password):
            hashfunc = hashlib.sha224

        password = SHA224Password()
        password.set('foo')
        self.assertEquals(hashlib.sha224(b'foo').hexdigest(), str(password))

    def test_hmac(self):
        def hmac_hashfunc(cls, msg):
            return hmac.new('mysecretkey', msg)

        class HMACPassword(Password):
            hashfunc = hmac_hashfunc

        self.clstest(HMACPassword)
        password = HMACPassword()
        password.set('foo')

        self.assertEquals(str(password),
                          hmac.new('mysecretkey', 'foo').hexdigest())

    def test_constructor(self):
        hmac_hashfunc = lambda msg: hmac.new('mysecretkey', msg)

        password = Password(hashfunc=hmac_hashfunc)
        password.set('foo')
        self.assertEquals(password.str,
                          hmac.new('mysecretkey', 'foo').hexdigest())


class TestPythonizeName(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(pythonize_name(''), '')

    def test_all_lower_case(self):
        self.assertEqual(pythonize_name('lowercase'), 'lowercase')

    def test_all_upper_case(self):
        self.assertEqual(pythonize_name('UPPERCASE'), 'uppercase')

    def test_camel_case(self):
        self.assertEqual(pythonize_name('OriginallyCamelCased'),
                         'originally_camel_cased')

    def test_already_pythonized(self):
        self.assertEqual(pythonize_name('already_pythonized'),
                         'already_pythonized')

    def test_multiple_upper_cased_letters(self):
        self.assertEqual(pythonize_name('HTTPRequest'), 'http_request')
        self.assertEqual(pythonize_name('RequestForHTTP'), 'request_for_http')

    def test_string_with_numbers(self):
        self.assertEqual(pythonize_name('HTTPStatus200Ok'), 'http_status_200_ok')


class TestBuildInstanceMetadataURL(unittest.TestCase):
    def test_normal(self):
        # This is the all-defaults case.
        self.assertEqual(_build_instance_metadata_url(
                'http://169.254.169.254',
                'latest',
                'meta-data'
            ),
            'http://169.254.169.254/latest/meta-data/'
        )

    def test_custom_path(self):
        self.assertEqual(_build_instance_metadata_url(
                'http://169.254.169.254',
                'latest',
                'dynamic'
            ),
            'http://169.254.169.254/latest/dynamic/'
        )

    def test_custom_version(self):
        self.assertEqual(_build_instance_metadata_url(
                'http://169.254.169.254',
                '1.0',
                'meta-data'
            ),
            'http://169.254.169.254/1.0/meta-data/'
        )

    def test_custom_url(self):
        self.assertEqual(_build_instance_metadata_url(
                'http://10.0.1.5',
                'latest',
                'meta-data'
            ),
            'http://10.0.1.5/latest/meta-data/'
        )

    def test_all_custom(self):
        self.assertEqual(_build_instance_metadata_url(
                'http://10.0.1.5',
                '2013-03-22',
                'user-data'
            ),
            'http://10.0.1.5/2013-03-22/user-data/'
        )


class TestRetryURL(unittest.TestCase):
    def setUp(self):
        try:
            self.urlopen_patch = mock.patch('urllib2.urlopen')
            self.opener_patch = mock.patch('urllib2.build_opener')
            self.urlopen = self.urlopen_patch.start()
            self.opener = self.opener_patch.start()
        except ImportError:
            self.urlopen_patch = mock.patch('urllib.request.urlopen')
            self.opener_patch = mock.patch('urllib.request.build_opener')
            self.urlopen = self.urlopen_patch.start()
            self.opener = self.opener_patch.start()

    def tearDown(self):
        self.urlopen_patch.stop()
        self.opener_patch.stop()

    def set_normal_response(self, response):
        fake_response = mock.Mock()
        fake_response.read.return_value = response
        self.urlopen.return_value = fake_response

    def set_no_proxy_allowed_response(self, response):
        fake_response = mock.Mock()
        fake_response.read.return_value = response
        self.opener.return_value.open.return_value = fake_response

    def test_retry_url_uses_proxy(self):
        self.set_normal_response('normal response')
        self.set_no_proxy_allowed_response('no proxy response')

        response = retry_url('http://10.10.10.10/foo', num_retries=1)
        self.assertEqual(response, 'no proxy response')


if __name__ == '__main__':
    unittest.main()
