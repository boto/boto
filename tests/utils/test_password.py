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


import logging
log = logging.getLogger(__file__)

class TestPassword(unittest.TestCase):
    """Test basic password functionality"""
    
    def clstest(self,cls):

        """Insure that password.__eq__ hashes test value before compare"""

        password=cls('foo')
        log.debug( "Password %s" % password )
        self.assertNotEquals(password , 'foo')

        password.set('foo')
        hashed = str(password)
        self.assertEquals(password , 'foo')
        self.assertEquals(password.str, hashed)

        password = cls(hashed)
        self.assertNotEquals(password.str , 'foo')
        self.assertEquals(password , 'foo')
        self.assertEquals(password.str , hashed)

 
    def test_aaa_version_1_9_default_behavior(self):
        from boto.utils import Password
        self.clstest(Password)

    def test_custom_hashclass(self):

        from boto.utils import Password
        import hashlib

        class SHA224Password(Password):
            hashfunc=hashlib.sha224

        password=SHA224Password()
        password.set('foo')
        self.assertEquals( hashlib.sha224('foo').hexdigest(), str(password))
 
    def test_hmac(self):
        from boto.utils import Password
        import hmac

        def hmac_hashfunc(cls,msg):
            log.debug("\n%s %s" % (cls.__class__, cls) )
            return hmac.new('mysecretkey', msg)

        class HMACPassword(Password):
            hashfunc=hmac_hashfunc

        self.clstest(HMACPassword)
        password=HMACPassword()
        password.set('foo')
  
        self.assertEquals(str(password), hmac.new('mysecretkey','foo').hexdigest())

    def test_constructor(self):
        from boto.utils import Password
        import hmac

        hmac_hashfunc = lambda msg: hmac.new('mysecretkey', msg )

        password = Password(hashfunc=hmac_hashfunc)
        password.set('foo')
        self.assertEquals(password.str, hmac.new('mysecretkey','foo').hexdigest())

        
       
if __name__ == '__main__':
    import sys
    sys.path = [ '../../' ] + sys.path
    #logging.basicConfig()
    #log.setLevel(logging.DEBUG)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPassword)
    unittest.TextTestRunner(verbosity=2).run(suite)
