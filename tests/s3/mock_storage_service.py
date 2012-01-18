# Copyright 2010 Google Inc.
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

"""
Provides basic mocks of core storage service classes, for unit testing:
ACL, Key, Bucket, Connection, and StorageUri. We implement a subset of
the interfaces defined in the real boto classes, but don't handle most
of the optional params (which we indicate with the constant "NOT_IMPL").
"""

import copy
import boto
import base64
from boto.utils import compute_md5

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

NOT_IMPL = None


class MockAcl(object):

    def __init__(self, parent=NOT_IMPL):
        pass

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        pass

    def to_xml(self):
        return '<mock_ACL_XML/>'


class MockKey(object):

    def __init__(self, bucket=None, name=None):
        self.bucket = bucket
        self.name = name
        self.data = None
        self.etag = None
        self.size = None
        self.content_encoding = None
        self.content_type = None
        self.last_modified = 'Wed, 06 Oct 2010 05:11:54 GMT'
        self.BufferSize = 8192

    def get_contents_as_string(self, headers=NOT_IMPL,
                               cb=NOT_IMPL, num_cb=NOT_IMPL,
                               torrent=NOT_IMPL,
                               version_id=NOT_IMPL):
        return self.data

    def get_contents_to_file(self, fp, headers=NOT_IMPL,
                             cb=NOT_IMPL, num_cb=NOT_IMPL,
                             torrent=NOT_IMPL,
                             version_id=NOT_IMPL,
                             res_download_handler=NOT_IMPL):
        fp.write(self.data)

    def get_file(self, fp, headers=NOT_IMPL, cb=NOT_IMPL, num_cb=NOT_IMPL,
                 torrent=NOT_IMPL, version_id=NOT_IMPL,
                 override_num_retries=NOT_IMPL):
        fp.write(self.data)

    def _handle_headers(self, headers):
        if not headers:
            return
        if 'Content-Encoding' in headers:
            self.content_encoding = headers['Content-Encoding']
        if 'Content-Type' in headers:
            self.content_type = headers['Content-Type']

    def open_read(self, headers=NOT_IMPL, query_args=NOT_IMPL,
                  override_num_retries=NOT_IMPL):
        pass

    def set_contents_from_file(self, fp, headers=None, replace=NOT_IMPL,
                               cb=NOT_IMPL, num_cb=NOT_IMPL,
                               policy=NOT_IMPL, md5=NOT_IMPL,
                               res_upload_handler=NOT_IMPL):
        self.data = fp.read()
        self.set_etag()
        self.size = len(self.data)
        self._handle_headers(headers)

    def set_contents_from_string(self, s, headers=NOT_IMPL, replace=NOT_IMPL,
                                 cb=NOT_IMPL, num_cb=NOT_IMPL, policy=NOT_IMPL,
                                 md5=NOT_IMPL, reduced_redundancy=NOT_IMPL):
        self.data = copy.copy(s)
        self.set_etag()
        self.size = len(s)
        self._handle_headers(headers)

    def set_contents_from_filename(self, filename, headers=None, replace=NOT_IMPL,
                                   cb=NOT_IMPL, num_cb=NOT_IMPL,
                                   policy=NOT_IMPL, md5=NOT_IMPL,
                                   res_upload_handler=NOT_IMPL):
        fp = open(filename, 'rb')
        self.set_contents_from_file(fp, headers, replace, cb, num_cb,
                                    policy, md5, res_upload_handler)
        fp.close()
    
    def copy(self, dst_bucket_name, dst_key, metadata=NOT_IMPL,
             reduced_redundancy=NOT_IMPL, preserve_acl=NOT_IMPL):
        dst_bucket = self.bucket.connection.get_bucket(dst_bucket_name)
        return dst_bucket.copy_key(dst_key, self.bucket.name,
                                   self.name, metadata)

    def set_etag(self):
        """
        Set etag attribute by generating hex MD5 checksum on current 
        contents of mock key.
        """
        m = md5()
        m.update(self.data)
        hex_md5 = m.hexdigest()
        self.etag = hex_md5

    def compute_md5(self, fp):
        """
        :type fp: file
        :param fp: File pointer to the file to MD5 hash.  The file pointer
                   will be reset to the beginning of the file before the
                   method returns.

        :rtype: tuple
        :return: A tuple containing the hex digest version of the MD5 hash
                 as the first element and the base64 encoded version of the
                 plain digest as the second element.
        """
        tup = compute_md5(fp)
        # Returned values are MD5 hash, base64 encoded MD5 hash, and file size.
        # The internal implementation of compute_md5() needs to return the 
        # file size but we don't want to return that value to the external
        # caller because it changes the class interface (i.e. it might
        # break some code) so we consume the third tuple value here and 
        # return the remainder of the tuple to the caller, thereby preserving 
        # the existing interface.
        self.size = tup[2]
        return tup[0:2]

class MockBucket(object):

    def __init__(self, connection=None, name=None, key_class=NOT_IMPL):
        self.name = name
        self.keys = {}
        self.acls = {name: MockAcl()}
        # default object ACLs are one per bucket and not supported for keys
        self.def_acl = MockAcl()
        self.subresources = {}
        self.connection = connection
        self.logging = False

    def copy_key(self, new_key_name, src_bucket_name,
                 src_key_name, metadata=NOT_IMPL, src_version_id=NOT_IMPL,
                 storage_class=NOT_IMPL, preserve_acl=NOT_IMPL):
        new_key = self.new_key(key_name=new_key_name)
        src_key = mock_connection.get_bucket(
            src_bucket_name).get_key(src_key_name)
        new_key.data = copy.copy(src_key.data)
        new_key.size = len(new_key.data)
        return new_key

    def disable_logging(self):
        self.logging = False

    def enable_logging(self, target_bucket_prefix):
        self.logging = True

    def get_acl(self, key_name='', headers=NOT_IMPL, version_id=NOT_IMPL):
        if key_name:
            # Return ACL for the key.
            return self.acls[key_name]
        else:
            # Return ACL for the bucket.
            return self.acls[self.name]

    def get_def_acl(self, key_name=NOT_IMPL, headers=NOT_IMPL, 
                    version_id=NOT_IMPL):
        # Return default ACL for the bucket.
        return self.def_acl

    def get_subresource(self, subresource, key_name=NOT_IMPL, headers=NOT_IMPL,
                        version_id=NOT_IMPL):
        if subresource in self.subresources:
            return self.subresources[subresource]
        else:
            return '<Subresource/>'

    def new_key(self, key_name=None):
        mock_key = MockKey(self, key_name)
        self.keys[key_name] = mock_key
        self.acls[key_name] = MockAcl()
        return mock_key

    def delete_key(self, key_name, headers=NOT_IMPL,
                   version_id=NOT_IMPL, mfa_token=NOT_IMPL):
        if key_name not in self.keys:
            raise boto.exception.StorageResponseError(404, 'Not Found')
        del self.keys[key_name]

    def get_all_keys(self, headers=NOT_IMPL):
        return self.keys.itervalues()

    def get_key(self, key_name, headers=NOT_IMPL, version_id=NOT_IMPL):
        # Emulate behavior of boto when get_key called with non-existent key.
        if key_name not in self.keys:
            return None
        return self.keys[key_name]

    def list(self, prefix='', delimiter=NOT_IMPL, marker=NOT_IMPL,
             headers=NOT_IMPL):
        # Return list instead of using a generator so we don't get
        # 'dictionary changed size during iteration' error when performing
        # deletions while iterating (e.g., during test cleanup).
        result = []
        for k in self.keys.itervalues():
            if not prefix:
                result.append(k)
            elif k.name.startswith(prefix):
                result.append(k)
        return result

    def set_acl(self, acl_or_str, key_name='', headers=NOT_IMPL,
                version_id=NOT_IMPL):
        # We only handle setting ACL XML here; if you pass a canned ACL
        # the get_acl call will just return that string name.
        if key_name:
            # Set ACL for the key.
            self.acls[key_name] = acl_or_str
        else:
            # Set ACL for the bucket.
            self.acls[self.name] = acl_or_str

    def set_def_acl(self, acl_or_str, key_name=NOT_IMPL, headers=NOT_IMPL,
                    version_id=NOT_IMPL):
        # We only handle setting ACL XML here; if you pass a canned ACL
        # the get_acl call will just return that string name.
        # Set default ACL for the bucket.
        self.def_acl = acl_or_str

    def set_subresource(self, subresource, value, key_name=NOT_IMPL,
                        headers=NOT_IMPL, version_id=NOT_IMPL):
        self.subresources[subresource] = value


class MockConnection(object):

    def __init__(self, aws_access_key_id=NOT_IMPL,
                 aws_secret_access_key=NOT_IMPL, is_secure=NOT_IMPL,
                 port=NOT_IMPL, proxy=NOT_IMPL, proxy_port=NOT_IMPL,
                 proxy_user=NOT_IMPL, proxy_pass=NOT_IMPL,
                 host=NOT_IMPL, debug=NOT_IMPL,
                 https_connection_factory=NOT_IMPL,
                 calling_format=NOT_IMPL,
                 path=NOT_IMPL, provider=NOT_IMPL,
                 bucket_class=NOT_IMPL):
        self.buckets = {}

    def create_bucket(self, bucket_name, headers=NOT_IMPL, location=NOT_IMPL,
                      policy=NOT_IMPL):
        if bucket_name in self.buckets:
            raise boto.exception.StorageCreateError(
                409, 'BucketAlreadyOwnedByYou',
                "<Message>Your previous request to create the named bucket "
                "succeeded and you already own it.</Message>")
        mock_bucket = MockBucket(name=bucket_name, connection=self)
        self.buckets[bucket_name] = mock_bucket
        return mock_bucket

    def delete_bucket(self, bucket, headers=NOT_IMPL):
        if bucket not in self.buckets:
            raise boto.exception.StorageResponseError(
                404, 'NoSuchBucket', '<Message>no such bucket</Message>')
        del self.buckets[bucket]

    def get_bucket(self, bucket_name, validate=NOT_IMPL, headers=NOT_IMPL):
        if bucket_name not in self.buckets:
            raise boto.exception.StorageResponseError(404, 'NoSuchBucket',
                                                 'Not Found')
        return self.buckets[bucket_name]

    def get_all_buckets(self, headers=NOT_IMPL):
        return self.buckets.itervalues()


# We only mock a single provider/connection.
mock_connection = MockConnection()


class MockBucketStorageUri(object):

    def __init__(self, scheme, bucket_name=None, object_name=None,
                 debug=NOT_IMPL, suppress_consec_slashes=NOT_IMPL):
        self.scheme = scheme
        self.bucket_name = bucket_name
        self.object_name = object_name
        if self.bucket_name and self.object_name:
            self.uri = ('%s://%s/%s' % (self.scheme, self.bucket_name,
                                        self.object_name))
        elif self.bucket_name:
            self.uri = ('%s://%s/' % (self.scheme, self.bucket_name))
        else:
            self.uri = ('%s://' % self.scheme)

    def __repr__(self):
        """Returns string representation of URI."""
        return self.uri

    def acl_class(self):
        return MockAcl

    def canned_acls(self):
        return boto.provider.Provider('aws').canned_acls

    def clone_replace_name(self, new_name):
        return MockBucketStorageUri(self.scheme, self.bucket_name, new_name)

    def connect(self, access_key_id=NOT_IMPL, secret_access_key=NOT_IMPL):
        return mock_connection

    def create_bucket(self, headers=NOT_IMPL, location=NOT_IMPL,
                      policy=NOT_IMPL):
        return self.connect().create_bucket(self.bucket_name)

    def delete_bucket(self, headers=NOT_IMPL):
        return self.connect().delete_bucket(self.bucket_name)

    def delete_key(self, validate=NOT_IMPL, headers=NOT_IMPL,
                   version_id=NOT_IMPL, mfa_token=NOT_IMPL):
        self.get_bucket().delete_key(self.object_name)

    def disable_logging(self, validate=NOT_IMPL, headers=NOT_IMPL,
                        version_id=NOT_IMPL):
        self.get_bucket().disable_logging()

    def enable_logging(self, target_bucket, target_prefix, validate=NOT_IMPL,
                       headers=NOT_IMPL, version_id=NOT_IMPL):
        self.get_bucket().enable_logging(target_bucket)

    def equals(self, uri):
        return self.uri == uri.uri

    def get_acl(self, validate=NOT_IMPL, headers=NOT_IMPL, version_id=NOT_IMPL):
        return self.get_bucket().get_acl(self.object_name)

    def get_def_acl(self, validate=NOT_IMPL, headers=NOT_IMPL, 
                    version_id=NOT_IMPL):
        return self.get_bucket().get_def_acl(self.object_name)

    def get_subresource(self, subresource, validate=NOT_IMPL, headers=NOT_IMPL,
                        version_id=NOT_IMPL):
        return self.get_bucket().get_subresource(subresource, self.object_name)

    def get_all_buckets(self, headers=NOT_IMPL):
        return self.connect().get_all_buckets()

    def get_all_keys(self, validate=NOT_IMPL, headers=NOT_IMPL):
        return self.get_bucket().get_all_keys(self)

    def get_bucket(self, validate=NOT_IMPL, headers=NOT_IMPL):
        return self.connect().get_bucket(self.bucket_name)

    def get_key(self, validate=NOT_IMPL, headers=NOT_IMPL,
                version_id=NOT_IMPL):
        return self.get_bucket().get_key(self.object_name)

    def is_file_uri(self):
        return False

    def is_cloud_uri(self):
        return True

    def names_container(self):
        return not self.object_name

    def names_singleton(self):
        return self.object_name

    def new_key(self, validate=NOT_IMPL, headers=NOT_IMPL):
        bucket = self.get_bucket()
        return bucket.new_key(self.object_name)

    def set_acl(self, acl_or_str, key_name='', validate=NOT_IMPL,
                headers=NOT_IMPL, version_id=NOT_IMPL):
        self.get_bucket().set_acl(acl_or_str, key_name)

    def set_def_acl(self, acl_or_str, key_name=NOT_IMPL, validate=NOT_IMPL,
                    headers=NOT_IMPL, version_id=NOT_IMPL):
        self.get_bucket().set_def_acl(acl_or_str)

    def set_subresource(self, subresource, value, validate=NOT_IMPL,
                        headers=NOT_IMPL, version_id=NOT_IMPL):
        self.get_bucket().set_subresource(subresource, value, self.object_name)
