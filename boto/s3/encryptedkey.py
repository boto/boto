
import boto.s3.key
from Crypto.Cipher import AES
from Crypto import Random
import base64
import hashlib
import os


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
        initialOffset = fp.tell()
        plaincontent = fp.read()
        ciphercontent = self.encrypt(plaincontent)
        fp.truncate(initialOffset)
        fp.write(ciphercontent)
        fp.seek(initialOffset)
        return fp

    def decryptFP(self,fp):
        initialOffset = fp.tell()
        ciphercontent = fp.read()
        print "ciphercontent:",ciphercontent
        plaincontent = self.decrypt(ciphercontent)
        print "plain:",plaincontent
        fp.truncate(initialOffset)
        fp.write(plaincontent)
        fp.seek(initialOffset)
        return fp

class EncryptedKey(boto.s3.key.Key):
    """
    Extends the Key class to perform local AES Encryption on files and strings

    Design goal to not break any functionality of the boto.s3.key.Key class.
    Acts as an encryption and decryption wrapper class around the core S3 functionality

    By overriding set_contents_from_file and get_contents_from_file,
    we can protect many differenent parts of the api, including
    getter and setter functions for strings, filenames, and filepointers.

    raw calling of 'key.send_file' and 'key.get_file' will not be protected however.

    """
    def __init__(self, bucket=None, name=None,encryptionKey=None):
        self.encryptionKey = encryptionKey
        if (encryptionKey != None):
            self.aes = AESCipher(hashlib.sha256(encryptionKey).digest())
        super(EncryptedKey,self).__init__(bucket,name)

    def set_encryption_key(self,encryptionKey):
        self.encryptionKey = encryptionKey
        self.aes = AESCipher(hashlib.sha256(encryptionKey).digest())

    def check_null_encryption_key(self):
        if (type(self.encryptionKey) != 'str' and len(self.encryptionKey) < 1):
            #raise an exception
            raise ValueError('encryptionKey string not set in EncryptedKey object')

    def set_contents_from_file(self,fp, headers=None, replace=True, 
        cb=None, num_cb=10, policy=None, md5=None, reduced_redundancy=False, 
        query_args=None, encrypt_key=False, size=None, rewind=False):

        #ensure we have a key to use
        self.check_null_encryption_key()

        #check if the contents is at EOF , if so, skip the encryption step.
        #print '#######################################'
        #spos = fp.tell()
        #print spos
        #fp.seek(0,os.SEEK_END)
        #endpos = fp.tell()
        #print endpos
        #fp.seek(spos)
        #if endpos != spos: 
        #    fp = self.aes.encryptFP(fp)

        initial = fp.tell()
        contents = fp.read()
        print 'contents:',contents
        fp.seek(initial)

        
        #if size is set, only encrypt up to that point
        fp = self.aes.encryptFP(fp)
        r = super(EncryptedKey,self).set_contents_from_file(fp,headers,replace,
            cb,num_cb,policy,md5,reduced_redundancy,query_args,encrypt_key,size,rewind)
        return r


    def get_contents_to_file(self,fp, headers=None, cb=None, 
        num_cb=10, torrent=False, version_id=None, 
        res_download_handler=None, response_headers=None):

        #ensure we have a key to use
        self.check_null_encryption_key()

        initialOffset = fp.tell()

        super(EncryptedKey,self).get_contents_to_file(fp,headers,cb,num_cb,
            torrent,version_id,res_download_handler,response_headers)

        #rewind to where we got the file pointer
        fp.seek(initialOffset)
        fp = self.aes.decryptFP(fp)

