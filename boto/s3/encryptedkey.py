
import boto.s3.key
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


class EncryptedKey(boto.s3.key.Key):
    """
    Extends the Key class to perform local AES Encryption on files and strings

    Also can perform a stream cipher on stream based data.(maybe?)

    Design goal to not break any functionality of the boto.s3.key.Key class.
    Acts as an encryption and decryption wrapper class around the core S3 functionality

    """
    def __init__(self, encryptionKey, bucket=None, name=None):
        self.encryptionKey = encryptionKey
        self.aes = AESCipher(hashlib.sha256(encryptionKey).digest())
        super(EncryptedKey,self).__init__(bucket,name)
        super(EncryptedKey,self).send_file() = self.send_file


    def send_file(self,fp, headers=None, cb=None, num_cb=10, 
        query_args=None, chunked_transfer=False, size=None):
        super(EncryptedKey,self).send_file(fp,headers,cb,num_cb,query_args,chunked_transfer,size)
        return self.aes.encryptFP(fp)

    def get_file(self,fp, headers=None, cb=None, num_cb=10, torrent=None,version_id=None,override_num_retries=None,response_headers=None ):
        super(EncryptedKey,self).get_file(fp,headers,cb,num_cb, torrent, version_id, override_num_retries, response_headers)
        return self.aes.decryptFP(fp)
