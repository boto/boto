
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


#class StreamCipher:

class EncryptedKey(boto.s3.key.Key):
    """
    Extends the Key class to perform local AES Encryption on files and strings

    Design goal to not break any functionality of the boto.s3.key.Key class.
    Acts as an encryption and decryption wrapper class around the core S3 functionality

    """
    def __init__(self, encryptionKey, bucket=None, name=None):
        self.encryptionKey = encryptionKey
        self.aes = AESCipher(hashlib.sha256(encryptionKey).digest())
        super(EncryptedKey,self).__init__(bucket,name)


    #data retrieval functions

    def set_contents_from_file(self,fp, headers=None, replace=True, 
        cb=None, num_cb=10, policy=None, md5=None, reduced_redundancy=False, 
        query_args=None, encrypt_key=False, size=None, rewind=False):
        fp = self.aes.encryptFP(fp)
        r = super(EncryptedKey,self).set_contents_from_file(fp,headers,replace,cb,num_cb,policy,md5,reduced_redundancy,query_args,encrypt_key,size,rewind)
        print r

    def set_contents_from_filename(self, filename, headers=None, 
        replace=True, cb=None, num_cb=10, policy=None, md5=None, 
        reduced_redundancy=False, encrypt_key=False):
        fp = open(filename)
        fp = self.aes.encryptFP(fp)
        self.set_contents_from_file(fp,headers,replace,cb,num_cb,policy,md5,reduced_redundancy,encrypt_key)



    def set_contents_from_string(self,s, headers=None, replace=True, 
        cb=None, num_cb=10, policy=None, md5=None, reduced_redundancy=False, 
        encrypt_key=False):
        ciphertext = self.aes.encrypt(s)
        print ciphertext
        super(EncryptedKey,self).set_contents_from_string(ciphertext,headers,replace,cb,num_cb,policy,md5,reduced_redundancy,encrypt_key)


    # Implement?
    # throw exception?
    def send_file(self,fp, headers=None, cb=None, num_cb=10, 
        query_args=None, chunked_transfer=False, size=None):
        pass


    def set_contents_from_stream(self, fp, headers=None, replace=True, 
        cb=None, num_cb=10, policy=None, reduced_redundancy=False, 
        query_args=None, size=None):
        pass



    #data upload functions


    def get_contents_to_file(self,fp, headers=None, cb=None, 
        num_cb=10, torrent=False, version_id=None, 
        res_download_handler=None, response_headers=None):
        super(EncryptedKey,self).get_contents_to_file(fp,headers,cb,num_cb,torrent,version_id,res_download_handler,response_headers)
        #make sure we are at the beginning of the file
        #or is the offset important?
        fp.seek(0)
        fp = decryptFP(fp)

    def get_contents_to_filename(self,filename, headers=None, cb=None, 
        num_cb=10, torrent=False, version_id=None, res_download_handler=None,
        response_headers=None):
        fp = open(filename)
        self.get_contents_to_file(fp,headers,cb,num_cb,torrent,version_id,res_download_handler,response_headers)


    #implement this one?
    # throw exception?
    def get_file(self,filename, headers=None, replace=True,
        cb=None, num_cb=10, policy=None, md5=None,
        reduced_redundancy=False, encrypt_key=False):
        pass

    def get_contents_as_string(self,headers=None, cb=None, num_cb=10, 
        torrent=False, version_id=None, response_headers=None):
        ciphercontent = super(EncryptedKey,self).get_contents_as_string(headers,cb,num_cb,torrent,version_id,response_headers)
        plaincontent = self.aes.decrypt(ciphercontent)
        return plaincontent
