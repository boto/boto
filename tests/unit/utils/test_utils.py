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

from boto.utils import Password
from boto.utils import pythonize_name


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
        self.assertEquals(hashlib.sha224('foo').hexdigest(), str(password))

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


if __name__ == '__main__':
    unittest.main()
