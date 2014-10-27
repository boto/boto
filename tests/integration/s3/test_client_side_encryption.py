"""
Some unit tests for the S3 Client Side Encryption
"""
import os
import shutil
import subprocess
import unittest
import time
import urllib
import binascii
import urllib2
from pip.vendor.distlib.version import NormalizedVersion

from boto.s3.connection import S3Connection
from boto.s3.multipart import MultiPartUpload

try:
    import psutil
except ImportError:
    psutil = None

try:
    import py4j
except ImportError:
    py4j = None


class S3ClientSideEncryptionTest(unittest.TestCase):
    s3 = True

    def setUp(self):
        super(S3ClientSideEncryptionTest, self).setUp()
        self.conn = S3Connection()
        self.bucket_name = 'client-side-encryption-%d' % int(time.time())
        self.bucket = self.conn.create_bucket(self.bucket_name)

    def tearDown(self):
        for key in self.bucket:
            key.delete()
        self.bucket.delete()
        super(S3ClientSideEncryptionTest, self).tearDown()

    def test_client_side_encryption(self):
        print('--- running {} tests ---'.format(self.__class__.__name__))

        client_side_encryption_keys = [
            ''.join([chr(0)] * (128 / 8)),  # Zero-key, AES 128
            ''.join([chr(0)] * (192 / 8)),  # Zero-key, AES 192
            ''.join([chr(0)] * (256 / 8)),  # Zero-key, AES 256
            os.urandom(128 / 8),  # Random-key, AES 128
            os.urandom(192 / 8),  # Random-key, AES 192
            os.urandom(256 / 8),  # Random-key, AES 256
        ]
        for encryption_key_index, encryption_key in enumerate(client_side_encryption_keys):
            encryption_key_hex = binascii.b2a_hex(encryption_key)
            encryption_key_base64 = binascii.b2a_base64(encryption_key)
            print 'Key of size {}, hex={}, base64={}'.format(
                8 * len(encryption_key),
                encryption_key_hex,
                encryption_key_base64
            )

            encrypted_connection = S3Connection(client_side_encryption_key=encryption_key)
            encrypted_bucket = encrypted_connection.get_bucket(self.bucket_name)

            unencrypted_connection = S3Connection()
            unencrypted_bucket = unencrypted_connection.get_bucket(self.bucket_name)

            key_name_base = 'foo-{key_content_index}-encrypted-using-key-{encryption_key_index}-method-{method_index}'
            key_contents = [
                '',   # Empty content, edge case
                '0123456701234567',   # Small content, multiple of the block size (16)
                '0123456701234567' + '0',  # Small content, needs padding
                '0123456701234567' * 2**6,        # 1Kb content, multiple of the block size (16)
                '0123456801234567' * 2**6 + '0',  # 1Kb content, needs padding
            ]
            for key_content_index, key_content in enumerate(key_contents):
                print '\tTest using content {}'.format(key_content_index)

                methods = [
                    lambda key, content, filename, fp: key.set_contents_from_string(content),
                    lambda key, content, filename, fp: key.set_contents_from_filename(filename),
                    lambda key, content, filename, fp: key.set_contents_from_file(fp),
                    # BotoClientError: s3 does not support chunked transfer
                    # lambda key, content, filename, fp: key.set_contents_from_stream(fp),
                ]
                for method_index, method in enumerate(methods):
                    print '\t\tTest using method {}'.format(method_index)

                    key_size = len(key_content)
                    key_name = key_name_base.format(key_content_index=key_content_index,
                                                    encryption_key_index=encryption_key_index,
                                                    method_index=method_index)

                    key_content_filename = '/tmp/{}'.format(key_name)
                    with open(key_content_filename, 'w') as key_content_fp:
                        key_content_fp.write(key_content)

                    # Encrypted content shouldn't be readable
                    with open(key_content_filename, 'r') as key_content_fp:
                        encrypted_key = encrypted_bucket.new_key(key_name)
                        unencrypted_key = unencrypted_bucket.new_key(key_name)
                        method(encrypted_key, key_content, key_content_filename, key_content_fp)
                        raw_content = unencrypted_key.get_contents_as_string()
                        decrypted_content = encrypted_key.get_contents_as_string()
                        self.assertNotEqual(key_content, raw_content)
                        self.assertEqual(key_content, decrypted_content)

                    # Unencrypted content should still be readable
                    # (files stored in clear can still be read)
                    with open(key_content_filename, 'r') as key_content_fp:
                        encrypted_key = encrypted_bucket.new_key(key_name)
                        unencrypted_key = unencrypted_bucket.new_key(key_name)
                        method(unencrypted_key, key_content, key_content_filename, key_content_fp)
                        raw_content = unencrypted_key.get_contents_as_string()
                        decrypted_content = encrypted_key.get_contents_as_string()
                        self.assertEqual(key_content, raw_content)
                        self.assertEqual(key_content, decrypted_content)

                    # Successive GET should return the same value (checks internal state/caching)
                    with open(key_content_filename, 'r') as key_content_fp:
                        encrypted_key = encrypted_bucket.new_key(key_name)
                        method(encrypted_key, key_content, key_content_filename, key_content_fp)
                        decrypted_content1 = encrypted_key.get_contents_as_string()
                        decrypted_content2 = encrypted_key.get_contents_as_string()
                        self.assertEqual(key_content, decrypted_content1)
                        self.assertEqual(key_content, decrypted_content2)

                    # PUT/GET x2 using the same key object
                    # This checks if the iv and the key are updated properly
                    encrypted_key = encrypted_bucket.new_key(key_name)
                    with open(key_content_filename, 'r') as key_content_fp:
                        method(encrypted_key, key_content, key_content_filename, key_content_fp)
                        decrypted_content1 = encrypted_key.get_contents_as_string()
                    with open(key_content_filename, 'r') as key_content_fp:
                        method(encrypted_key, key_content, key_content_filename, key_content_fp)
                        decrypted_content2 = encrypted_key.get_contents_as_string()
                    self.assertEqual(key_content, decrypted_content1)
                    self.assertEqual(key_content, decrypted_content2)

                    # Check that the size is correct
                    with open(key_content_filename, 'r') as key_content_fp:
                        # The size should be set after an upload
                        encrypted_key1 = encrypted_bucket.new_key(key_name)
                        method(encrypted_key1, key_content, key_content_filename, key_content_fp)
                        self.assertEqual(encrypted_key1.size, key_size)
                        # The size should be set after a download
                        encrypted_key2 = encrypted_bucket.new_key(key_name)
                        decrypted_content2 = encrypted_key2.get_contents_as_string()
                        self.assertEqual(encrypted_key2.size, key_size)

        print('--- {} tests completed ---'.format(self.__class__.__name__))

    def test_client_side_encryption_multipart(self):
        print('--- running {} multipart tests ---'.format(self.__class__.__name__))

        connection = S3Connection(client_side_encryption_key=os.urandom(256 / 8))
        bucket = connection.get_bucket(self.bucket_name)

        multipart_upload = MultiPartUpload(bucket)  # does not create an upload, so there's nothing to clean
        self.assertRaises(ValueError, multipart_upload.upload_part_from_file, None, None)
        self.assertRaises(ValueError, multipart_upload.copy_part_from_key, None, None, None)

        print('--- tests {} multipart tests completed ---'.format(self.__class__.__name__))


class _TestWithJavaS3GatewayMixin(object):
    jars = None
    gateway = None

    @classmethod
    def _get_classpath(cls):

        if not cls.jars:
            aws_java_sdk_version = '1.8.11'

            manifest_url = 'https://raw.githubusercontent.com/aws/aws-sdk-java/{}/META-INF/MANIFEST.MF'.format(aws_java_sdk_version)
            manifest_lines = urllib2.urlopen(manifest_url).read().split('\n')
            bundle_lines = [line for line in manifest_lines if 'bundle-version' in line]
            bundles = [(line.split(';')[0].split(' ')[-1], line.split('"')[1]) for line in bundle_lines]

            jars = []
            for package, version in bundles:
                base_package = package.rsplit('.', 1)[0]
                if 'jackson' in package:
                    version = '2.0.2'
                if 'javax.mail' in package:
                    base_package = package
                base_url = "http://repository.springsource.com/ivy/bundles/external/{base_package}/com.springsource.{package}/{version}/com.springsource.{package}-{version}.jar"
                url = base_url.format(base_package=base_package, package=package, version=version)
                jar = '/tmp/{package}-{version}.jar'.format(package=package, version=version)
                if not os.path.isfile(jar):
                    print 'Downloading {}'.format(url)
                    urllib.URLopener().retrieve(url, jar)
                jars.append(jar)

            mvn_bundles = [
                ('net/sf/py4j', 'py4j', '0.8.2'),
                ('com/amazonaws', 'aws-java-sdk', aws_java_sdk_version),
                ('org/apache/commons', 'commons-io', '1.3.2'),
                ('joda-time', 'joda-time', '2.2'),
            ]
            if NormalizedVersion(aws_java_sdk_version) >= NormalizedVersion('1.8.10'):
                mvn_bundles.append(('com/amazonaws', 'aws-java-sdk-core', aws_java_sdk_version))
            for path, name, version in mvn_bundles:
                base_url = "http://central.maven.org/maven2/{path}/{name}/{version}/{name}-{version}.jar"
                url = base_url.format(path=path, name=name, version=version)
                jar = '/tmp/{name}-{version}.jar'.format(name=name, version=version)
                if not os.path.isfile(jar):
                    print 'Downloading {}'.format(url)
                    urllib.URLopener().retrieve(url, jar)
                jars.append(jar)

            cls.jars = jars

        return ':'.join(['.'] + cls.jars)

    @classmethod
    def _stop_gateway(cls):
        import psutil
        for process in psutil.process_iter():
            if 'BotoS3Gateway' in process.cmdline():
                print 'Stopping gateway...'
                process.kill()
                time.sleep(1)

    @classmethod
    def _build_gateway(cls):
        src_filename = __file__.replace('.pyc', '.java').replace('.py', '.java')
        dst_filename = '/tmp/BotoS3Gateway.java'
        if os.path.isfile(dst_filename):
            os.remove(dst_filename)
        shutil.copy(src_filename, dst_filename)
        subprocess.check_output(
            [
                'javac',
                '-cp',
                cls._get_classpath(),
                dst_filename
            ],
            cwd='/tmp',
        )

    @classmethod
    def _start_gateway(cls):
        subprocess.Popen(
            [
                'java',
                '-cp',
                cls._get_classpath(),
                'BotoS3Gateway',
            ],
            cwd='/tmp',
        )
        time.sleep(3)
        from py4j.java_gateway import JavaGateway
        cls.gateway = JavaGateway()

    def setUp(self):
        super(_TestWithJavaS3GatewayMixin, self).setUp()
        self._stop_gateway()
        self._build_gateway()
        self._start_gateway()

    def tearDown(self):
        self._stop_gateway()
        super(_TestWithJavaS3GatewayMixin, self).tearDown()


class S3ClientSideEncryptionTestJavaImplementationCompatibility(_TestWithJavaS3GatewayMixin, unittest.TestCase):
    s3 = True

    def setUp(self):
        super(S3ClientSideEncryptionTestJavaImplementationCompatibility, self).setUp()
        self.conn = S3Connection()
        self.bucket_name = 'client-side-encryption-%d' % int(time.time())
        self.bucket = self.conn.create_bucket(self.bucket_name)

    def tearDown(self):
        for key in self.bucket:
            key.delete()
        self.bucket.delete()
        super(S3ClientSideEncryptionTestJavaImplementationCompatibility, self).setUp()

    @unittest.skipIf(not psutil or not py4j, "Please install psutil and py4j to run this test")
    def test_client_side_encryption_java_compatibility(self):
        print('--- running {} tests ---'.format(self.__class__.__name__))

        client_side_encryption_keys = [
            ''.join([chr(0)] * (128 / 8)),  # Zero-key, AES 128
            ''.join([chr(0)] * (192 / 8)),  # Zero-key, AES 192
            ''.join([chr(0)] * (256 / 8)),  # Zero-key, AES 256
            os.urandom(128 / 8),  # Random-key, AES 128
            os.urandom(192 / 8),  # Random-key, AES 192
            os.urandom(256 / 8),  # Random-key, AES 256
        ]
        for encryption_key_index, encryption_key in enumerate(client_side_encryption_keys):
            encryption_key_hex = binascii.b2a_hex(encryption_key)
            encryption_key_base64 = binascii.b2a_base64(encryption_key)
            print 'Key of size {}, hex={}, base64={}'.format(
                8 * len(encryption_key),
                encryption_key_hex,
                encryption_key_base64
            ).replace('\n', '')

            encrypted_connection = S3Connection(client_side_encryption_key=encryption_key)
            encrypted_bucket = encrypted_connection.get_bucket(self.bucket_name)

            unencrypted_connection = S3Connection()
            unencrypted_bucket = unencrypted_connection.get_bucket(self.bucket_name)

            key_name_base = 'foo-{key_content_index}-encrypted-using-key-{encryption_key_index}'
            key_contents = [
                '',   # Empty content, edge case
                '0123456701234567',   # Small content, multiple of the block size (16)
                '0123456701234567' + '0',  # Small content, needs padding
                '0123456701234567' * 2**6,        # 1Kb content, multiple of the block size (16)
                '0123456701234567' * 2**6 + '0',  # 1Kb content, needs padding
            ]
            for key_content_index, key_content in enumerate(key_contents):
                print '\tTest using content {}'.format(key_content_index)

                methods = [
                    lambda a, b, c, d, e, content, filename: self.gateway.entry_point.putString(a, b, c, d,
                                                                                                e, content),
                    lambda a, b, c, d, e, content, filename: self.gateway.entry_point.putFile(a, b, c, d,
                                                                                              e, filename),
                ]
                for method_index, method in enumerate(methods):
                    print '\t\tTest using method {}'.format(method_index)

                    key_size = len(key_content)
                    key_name = key_name_base.format(key_content_index=key_content_index,
                                                    encryption_key_index=encryption_key_index)
                    encrypted_key = encrypted_bucket.new_key(key_name)
                    unencrypted_key = unencrypted_bucket.new_key(key_name)

                    key_content_filename = '/tmp/{}'.format(key_name)
                    with open(key_content_filename, 'w') as key_content_fp:
                        key_content_fp.write(key_content)

                    access_key = unencrypted_connection.provider.access_key
                    secret_key = unencrypted_connection.provider.secret_key

                    # To make debugging easier if something fails later, test the java encryption
                    method(access_key, secret_key, encryption_key_base64,
                           self.bucket_name, key_name,
                           key_content, key_content_filename)
                    raw_content = unencrypted_key.get_contents_as_string()
                    self.assertNotEqual(key_content, raw_content)
                    decrypted_content = self.gateway.entry_point.getString(access_key, secret_key,
                                                                           encryption_key_base64,
                                                                           self.bucket_name, key_name)
                    self.assertEqual(key_content, decrypted_content)

                    # Encrypt with python, decrypt with java
                    encrypted_key.set_contents_from_string(key_content)
                    decrypted_content = self.gateway.entry_point.getString(access_key, secret_key, encryption_key_base64,
                                                                           self.bucket_name, key_name)
                    self.assertEqual(key_content, decrypted_content)

                    # Encrypt with java, decrypt with python
                    method(access_key, secret_key, encryption_key_base64,
                           self.bucket_name, key_name,
                           key_content, key_content_filename)
                    decrypted_content = encrypted_key.get_contents_as_string()
                    self.assertEqual(key_content, decrypted_content)
                    # When sending the size in java like in these tests, the original size
                    # of the file won't be set. Test that it's handled properly
                    self.assertEqual(key_content, decrypted_content)
                    self.assertEqual(encrypted_key.size, key_size)

        print('--- {} tests completed ---'.format(self.__class__.__name__))
