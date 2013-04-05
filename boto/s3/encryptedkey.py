
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


#class StreamCipher:

class EncryptedKey(boto.s3.key.Key):
    """
    Extends the Key class to perform local AES Encryption on files and strings

    Also can perform a stream cipher on stream based data.(maybe?)

    Design goal to not break any functionality of the boto.s3.key.Key class.
    Acts as an encryption and decryption wrapper class around the core S3 functionality

    """
    def __init__(self, bucket=None, name=None, encryptionKey):
        self.encryptionKey = encryptionKey
        self.aes = AESCipher(hashlib.sha256(encryptionKey).digest())


    #data retrieval functions

    def set_contents_from_filename(self, filename, headers=None, 
        replace=True, cb=None, num_cb=10, policy=None, md5=None, 
        reduced_redundancy=False, encrypt_key=False):




    def set_contents_from_file(self,fp, headers=None, replace=True, 
        cb=None, num_cb=10, policy=None, md5=None, reduced_redundancy=False, 
        query_args=None, encrypt_key=False, size=None, rewind=False:


    def set_contents_from_string(self,s, headers=None, replace=True, 
        cb=None, num_cb=10, policy=None, md5=None, reduced_redundancy=False, 
        encrypt_key=False):

    def send_file(self,fp, headers=None, cb=None, num_cb=10, 
        query_args=None, chunked_transfer=False, size=None):


    def set_contents_from_stream(self, fp, headers=None, replace=True, 
        cb=None, num_cb=10, policy=None, reduced_redundancy=False, 
        query_args=None, size=None):



    #data upload functions

    def get_contents_to_filename(self,filename, headers=None, cb=None, 
        num_cb=10, torrent=False, version_id=None, res_download_handler=None,
        response_headers=None):


    def get_contents_to_file(self,fp, headers=None, cb=None, 
        num_cb=10, torrent=False, version_id=None, 
        res_download_handler=None, response_headers=None):

        filename = fp.name
        super.get_contents_to_file(fp,headers,cb,num_cb,torrent,version_id,res_download_handler,response_headers)
        #now read the file back in, and decrypt, truncating the encrypted file
        #could be improved to decrypt on the fly, in the future
        #since this approach is kind of wasteful
        fp = open(filename)
        ciphercontent = fp.read()
        fp.close()
        plaincontent = self.aes.decrypt(ciphercontent)
        fp = open(filename,'w+')
        fp.write(plaincontent)
        fp.close()

    def get_file(self,filename, headers=None, replace=True,
        cb=None, num_cb=10, policy=None, md5=None,
        reduced_redundancy=False, encrypt_key=False):


    def get_contents_as_string(self,headers=None, cb=None, num_cb=10, 
        torrent=False, version_id=None, response_headers=None):

        ciphercontent = super.get_contents_as_string(headers,cb,num_cb,torrent,version_id,response_headers)
        plaincontent = self.aes.decrypt(ciphercontent)
        return plaincontent
