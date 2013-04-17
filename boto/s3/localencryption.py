from Crypto.Cipher import AES
from Crypto import Random
import base64
import hashlib


#blocksize and padding functions
class AESCipher:
    def __init__( self, key ):
        self.key = key 
        self.BS = AES.block_size 
        self.pad = lambda s: s + (self.BS - len(s) % self.BS) * chr(self.BS - len(s) % self.BS) 
        self.unpad = lambda s : s[0:-ord(s[-1])]

    def encrypt( self, raw ):
        raw = self.pad(raw)
        iv = Random.new().read( self.BS )
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
        return base64.b64encode( iv + cipher.encrypt( raw ) ) 

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        iv = enc[:self.BS]
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
        return self.unpad(cipher.decrypt( enc[self.BS:] ))

    def encryptFP(self,fp):
        plaincontent = fp.read()
        ciphercontent = self.encrypt(plaincontent)
        fp.truncate(0)
        fp.write(ciphercontent)
        fp.seek(0)
        return fp

    def decryptFP(self,fp):
        ciphercontent = fp.read()
        plaincontent = self.decrypt(ciphercontent)
        #reset the filepointer to the beginning
        # or original offset?
        fp.truncate(0)
        fp.write(plaincontent)
        fp.seek(0)
        return fp


