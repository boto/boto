
########################################################################
# This module implements an encryption / decryption algorithm,
# that can be uses and integrated in different applications.
# It uses the simetric cipher AES, with 128 bits encryption, in CTR mode.
# The encryption key is 128 bits, and is generated using the PBKDF2 algorithm.
# Security is assured by:
#   - implementing AES 128 CTR mode for the encryption
#   - implementing HMAC SHA256 for integrity check
# The Initail Value (IV) is 128 bits.
# The generation of the encryption key is from:
#   - provided token
#   - random salt of 128 bits
# The main functions are:
# - encrypt_data(plaint_text, auth_token)
# - decrypt_data(cipher_text, auth_token)
# - generate_keys(seed_text, salt)
########################################################################

import time
import zlib

from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import HMAC
from Crypto.Hash import SHA256


class IntegrityViolation(Exception):
    pass

def generate_keys(seed_text, salt):
    '''# Use the PBKDF2 algorithm to generate 32 bytes = 512 bits key.
    # This key will be split into half to form the encrypt_key and hmac_key.
    # full_key = encrypt_key || hmac_key
    # The encrypt_key will be 16 bytes = 128 bits
    # The hmac_key will be 16 bytes = 128 bits'''

    full_key = PBKDF2(seed_text, salt, dkLen=32, count=1345)
    encrypt_key = full_key[:len(full_key) / 2]
    hmac_key = full_key[len(full_key) / 2:]

    return encrypt_key, hmac_key

def encrypt_data(plaint_text, auth_token):
    '''# Encryption function.
    # plain_text : string, auth_token: string, cipher_text: string
    # This function encrypts and signs the plain_text,
    # using AES 128 CTR mode encryption and HMAC SHA256 for authentication
    # Return value form:
    # mac = HMAC(rand_salt || ctr_iv || E(plaint_text))
    # cipher_text = rand_salt || ctr_iv || E(plaint_text) || mac'''

    # Compress the plain_text. This provides faster speeds for files > 10 MB
    # plaint_text = zlib.compress(plaint_text, 5)

    # Generate the encryption key from the auth_token with rand_salt.
    rand_salt = Random.new().read(16)
    encrypt_key, hmac_key = generate_keys(auth_token, rand_salt)
    cipher_text = rand_salt

    # Configure the counter for AES CTR-mode cipher, to use 16 bytes = 128 bits
    ctr_iv = Random.new().read(16)
    ctr = Counter.new(128, initial_value=long(ctr_iv.encode('hex'), 16))
    cipher_text = cipher_text + ctr_iv

    # Create the AES cipher object and encrypt the cipher_text
    cipher = AES.new(encrypt_key, AES.MODE_CTR, counter=ctr)
    cipher_text = cipher_text + cipher.encrypt(plaint_text)

    # Create the HMAC object and sign the cipher_text using 32 bytes = 256 bits
    hmac_obj = HMAC.new(hmac_key, cipher_text, SHA256)
    mac = hmac_obj.digest()

    # cipher_text = rand_salt || ctr_iv || E(plaint_text) || mac
    cipher_text = cipher_text + mac
    return cipher_text


def decrypt_data(cipher_text, auth_token):
    '''# Decryption function.
    # cipher_text : string, auth_token: string, plain_text: string
    # AES is a symetric encryption, thus the encryption key = decryption key
    # This function checks for the integrity of the cipher_text
    # and if ok then decrypts and outputs the recovered_plain_text,
    # otherwise raises and error, using AES 128 CTR mode encryption
    # and HMAC SHA256 for authentication
    # Input value form:
    # mac = HMAC(rand_salt || ctr_iv || E(plaint_text))
    # cipher_text = rand_salt || ctr_iv || E(plaint_text) || mac'''

    # Generate the encryption key from the auth_token.
    rand_salt = cipher_text[:16]
    encrypt_key, hmac_key = generate_keys(auth_token, rand_salt)

    # Get the sent mac and create the HMAC object, to sign the cipher_text
    mac = cipher_text[-32:]
    cipher_text = cipher_text[:-32]
    hmac_obj = HMAC.new(hmac_key, cipher_text, SHA256)
    computed_mac = hmac_obj.digest()

    # Check the MAC, to ensure integrity
    if computed_mac != mac:
        # Integrity failed, raise and exception
        raise IntegrityViolation()

    # Create and initialise the counter, of 16 bytes = 128 bits
    cipher_text = cipher_text[16:]
    ctr_iv = cipher_text[:16]
    cipher_text = cipher_text[16:]
    ctr = Counter.new(128, initial_value=long(ctr_iv.encode('hex'), 16))

    # Create the AES cipher object and decrypt the ciphertext
    cipher = AES.new(encrypt_key, AES.MODE_CTR, counter=ctr)

    # Decrypt the data
    plain_text = cipher.decrypt(cipher_text)

    # Decompress the plain_text, if it was compressed in the encryption.
    # plain_text = zlib.decompress(plain_text)
    return plain_text

# Encryption/Decryption testing.
if __name__ == "__main__":
    # Test the encryption / decryption
    filename = 'packages/test1.dat'
    enc_filename = 'packages/enc_test1.dat'
    dec_filename = 'packages/dec_test1.dat'
    token = '77efde43-360a-48cc-b41e-96d090c15beb'

    # Read the file to be encrypted from disk
    with open(filename, 'rb') as f:
        plain_text = f.read()

    # Encrypt
    try:
        start_time = time.time()
        cipher_text = encrypt_data(plain_text, token)
        elapsed_time = time.time() - start_time
        print "Encrypted data successfully in %.8f" % elapsed_time

        with open(enc_filename, 'wb') as enc_file:
            enc_file.write(cipher_text)
    except EnvironmentError:
        # Includes IOError, OSError and WindowsError (if applicable)
        print "Error writing file to disk"
        raise SystemExit(5)
    except ValueError:
        print "ValueError exception raised"
        raise SystemExit(2)

    # Decrypt
    # Read the file to be decrypted from disk
    with open(enc_filename, 'rb') as f:
        cipher_text = f.read()
    try:
        start_time = time.time()
        recovered_plain_text = decrypt_data(cipher_text, token)
        elapsed_time = time.time() - start_time
        print "Decrypted data successfully in %.8f" % elapsed_time

        # Write the encrypted data to disk.
        with open(dec_filename, 'wb') as dec_file:
            dec_file.write(plain_text)
    except EnvironmentError:
        # Includes IOError, OSError and WindowsError (if applicable)
        print "Error reading file from disk"
        raise SystemExit(5)

    # Check that the original plain text is the same as the recovered plain text.
    try:
        assert (plain_text == recovered_plain_text)
    except AssertionError:
        print "Original plain text is different from decrypted text."
        raise SystemExit(10)
    else:
        print "Encryption/decryption cycle test completed successfully!"
