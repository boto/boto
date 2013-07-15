
import boto.s3.key
from Crypto.Cipher import AES
from Crypto import Random
from boto.utils import compute_md5
import base64
import hashlib
import os
import StringIO
import math


class AESCipher:
    """
    Support class which provides cryptographic functions on behalf
    of an EncryptedKey instance. Each encryption uses the same encryption key,
    but a new Random Initialization Vector. Encryption key is a passphrase that has been
    hashed by SHA256 before becoming the key used in AES 256 CBC mode.

    :ivar key: 256 bit hashed version of the user supplied passphrase. 
    :ivar BS: block size in number of bytes.
    :ivar pad: function to ensure data is divisible by the blocksize.
    :ivar unpad: strips extra padding for decryption.
    :ivar efp: encrypted filepointer stored from a compute_encrypted_md5 function call.
    """
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
        """
        Reads content from the filepointer, performs encryption,
        writes encrypted content back into the filepointer starting at the offset
        as it was first passed in.

        if fp is None, then reuse an existing encrypted file pointer,
        which would have been set by a compute_encrypted_md5 call.
        Doing this ensures that the MD5's will match, (since the IV is random each time).

        """
        if (fp is None):
            #we had a precomputed encrypted fp
            #from an MD5 computation,
            #and the user wants to use it
            return self.efp
        else:
            #computing a new encrypted fp.
            #save the initial offset, to return later.
            initialOffset = fp.tell()
            fp.seek(0)
            #open a new StringIO to act as fp, incase the one passed in wasn't open for writing.
            #Re-read the entire file from fp, even if there was an offset.
            fp_new = StringIO.StringIO()
            fp_new.write(fp.read(initialOffset))
            #then read past the offset, and use that as plaintext
            plaincontent = fp.read()
            ciphercontent = self.encrypt(plaincontent)
            fp_new.write(ciphercontent)
            fp_new.seek(initialOffset)
            return fp_new

    def decryptFP(self,fp):
        """
        Reads content from the filepointer, performs decryption,
        writes decrypted content back into the filepointer starting at the offset
        as it was first passed in.
        """
        initialOffset = fp.tell()
        ciphercontent = fp.read()
        plaincontent = self.decrypt(ciphercontent)
        fp.truncate(initialOffset)
        fp.write(plaincontent)
        fp.seek(initialOffset)
        return fp

    def compute_encrypted_size(self,content):
        """
        For a given plaintext and blocksize,
        computes how large in bytes the resultant ciphertext will be
        """
        blocksize = self.BS
        contentlen = len(content)
        contentlen = float(contentlen)
        paddedcontentlen = blocksize * (int(math.ceil(contentlen/blocksize)))
        paddedcontentlen = paddedcontentlen + blocksize #add the IV
        base64len = 4 * int(math.ceil( paddedcontentlen / 3.0))
        return base64len



class EncryptedKey(boto.s3.key.Key):
    """
    Extends the Key class to perform local AES Encryption (256 bit, Cipher Block Chaining)
    on files and strings

    Design goal was to not break any functionality of the boto.s3.key.Key class.
    Acts as an encryption and decryption wrapper class around the core S3 functionality

    By overriding set_contents_from_file and get_contents_from_file,
    we can protect many differenent parts of the api, including
    getter and setter functions for strings, filenames, and filepointers.

    the calling of 'key.send_file' and 'key.get_file' will not be protected however, since this
    shim lies one level above those functions, in set/get_contents_from_file overrides.

    New ivars
    :ivar encryptionKey: encryption key string (arbitrary length) to use for encryption and decryption
    :ivar aes: AESCipher helper class to perform crypto functions.

    """
    def __init__(self, bucket=None, name=None,encryptionKey=None):
        self.encryptionKey = encryptionKey
        if (encryptionKey is not None):
            self.aes = AESCipher(hashlib.sha256(encryptionKey).digest())
        super(EncryptedKey,self).__init__(bucket,name)

    def set_encryption_key(self,encryptionKey):
        """
        In case the EncryptedKey was constructed without an encryption key,
        allow it to be set, and instantiate the aes helper class.
        """
        self.encryptionKey = encryptionKey
        self.aes = AESCipher(hashlib.sha256(encryptionKey).digest())

    
    def check_null_encryption_key(self):
        """
        Function to ensure that an encryption key was set before any
        file operations are began
        """
        if (type(self.encryptionKey) != 'str' and len(self.encryptionKey) < 1):
            #raise an exception
            raise ValueError('encryptionKey string not set in EncryptedKey object')

    def compute_encrypted_md5(self, fp, size=None):
        """
        This function saves away the encrypted content, so that it matches 
        later, and another random IV isn't regenerated.
        To use this saved encrypted file pointer (efp), call set_contents_from_file
        with fp == None

        :type fp: file
        :param fp: File pointer to the file to MD5 hash.  The file
            pointer will encrpyted and then hashed.
            the fp will be reset to the same position before the
            method returns.

        :type size: int
        :param size: (optional) The Maximum number of bytes to read
            from the file pointer (fp). This is useful when uploading
            a file in multiple parts where the file is being split
            in place into different parts. Less bytes may be available.
        """
        #avoid modifying the original fp
        spos = fp.tell()
        #only read the size specified, if specified
        if (size is not None):
            content = fp.read(size)
            #also adjust the size variable, since we are encrypting
            size = self.aes.compute_encrypted_size(content)
        else:
            content = fp.read()
        fp.seek(spos)

        #encrypt the content, so we can hash it
        efp = StringIO.StringIO(content)
        efp = self.aes.encryptFP(efp)

        self.aes.efp = efp # save for later in case they do a real encryption
        #this ensures that a new random IV isn't used so that the md5 matches,
        #when encryption is actually performed.

        hex_digest, b64_digest, data_size = compute_md5(efp, size=size)
        # Returned values are MD5 hash, base64 encoded MD5 hash, and data size.
        # The internal implementation of compute_md5() needs to return the
        # data size but we don't want to return that value to the external
        # caller because it changes the class interface (i.e. it might
        # break some code) so we consume the third tuple value here and
        # return the remainder of the tuple to the caller, thereby preserving
        # the existing interface.
        self.size = data_size
        return (hex_digest, b64_digest)


    def set_contents_from_file(self,fp, headers=None, replace=True, 
        cb=None, num_cb=10, policy=None, md5=None, reduced_redundancy=False, 
        query_args=None, encrypt_key=False, size=None, rewind=False):
        """
        Subclass Override of Key.set_contents_from_file
        Calling other 'set' functions inherited from Key will eventually
        funnel to this function, which performs AES encryption on the data
        before passing into the Key.send_file function. This function will also
        recompute the size parameter (since encrpyted size is always larger than plaintext)
        and it will also handle computed MD5's.

        Before this function is called, the user should have set an encryption key
        on the EncryptedKey object either by using the constructor argument, or calling the
        set_encryption_key function.


        """
        #ensure we have a key to use
        self.check_null_encryption_key()

        if (fp is None):
            #calling to try to reuse the fp saved away by compute_encrypted_md5
            fp = self.aes.encryptFP(None)
            size = None #set size in case somebody set it in the call.
        #elif( fp != None and md5 != None):
            #need to clarify how to handle this,
            #they computed an MD5, but it will eventually change.
            #should we raise an exception telling the user?
        else:
            #proceed as normal

            #rewind requested, go to start of file
            if rewind is True:
                fp.seek(0)

            #if size is set, only encrypt up to that point
            if size is not None:
                contents = fp.read(size)
                fp = StringIO.StringIO(contents)
                #now reset the size to reflect the encrypted size
                size = self.aes.compute_encrypted_size(contents)

            initial = fp.tell()
            contents = fp.read()
            fp.seek(initial)

            #check if the contents is at EOF , if so, skip the encryption step.
            spos = fp.tell()
            fp.seek(0,os.SEEK_END)
            endpos = fp.tell()
            fp.seek(spos)
            if endpos != spos: 
                fp = self.aes.encryptFP(fp)
            #else it means we are at the EOF so no need to encrypt

        #end if(fp==None)

        r = super(EncryptedKey,self).set_contents_from_file(fp,headers,replace,
            cb,num_cb,policy,md5,reduced_redundancy,query_args,encrypt_key,size,rewind)
        return r


    def get_contents_to_file(self,fp, headers=None, cb=None, 
        num_cb=10, torrent=False, version_id=None, 
        res_download_handler=None, response_headers=None):
        """
        Subclass Override of Key.get_contents_to_file
        Calling other 'get' functions inherited from Key will eventually
        funnel to this function, which performs AES decryption on the data
        before passing into the other wrapper functions such as get_contentes_as_string,
        or get_contents_to_filename. 
       
        Before this function is called, the user should have set an encryption key
        on the EncryptedKey object either by using the constructor argument, or calling the
        set_encryption_key function.

        """

        #ensure we have a key to use
        self.check_null_encryption_key()
        initialOffset = fp.tell()
        super(EncryptedKey,self).get_contents_to_file(fp,headers,cb,num_cb,
            torrent,version_id,res_download_handler,response_headers)

        #We need to close the filepointer, re open it, and read in the content
        #since sometimes the fp isn't in read+write mode.
        name = fp.name
        fp.close()
        fp = open(name,'r') 
        fp.seek(initialOffset)
        encryptedcontent = fp.read()
        fp.close()
        
        plaincontent = self.aes.decrypt(encryptedcontent)
       
        #open fp for writing with the same name, get rid of encrypted content, and write the plaintext
        fp = open(name,'w') 
        fp.truncate(initialOffset)
        fp.write(plaincontent)
       
