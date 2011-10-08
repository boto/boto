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

import StringIO
from boto.s3.key import Key as S3Key

class Key(S3Key):

    def add_email_grant(self, permission, email_address):
        """
        Convenience method that provides a quick way to add an email grant to a
        key. This method retrieves the current ACL, creates a new grant based on
        the parameters passed in, adds that grant to the ACL and then PUT's the
        new ACL back to GS.

        :type permission: string
        :param permission: The permission being granted. Should be one of:
            READ|FULL_CONTROL
            See http://code.google.com/apis/storage/docs/developer-guide.html#authorization
            for more details on permissions.

        :type email_address: string
        :param email_address: The email address associated with the Google
                              account to which you are granting the permission.
        """
        acl = self.get_acl()
        acl.add_email_grant(permission, email_address)
        self.set_acl(acl)

    def add_user_grant(self, permission, user_id):
        """
        Convenience method that provides a quick way to add a canonical user
        grant to a key. This method retrieves the current ACL, creates a new
        grant based on the parameters passed in, adds that grant to the ACL and
        then PUT's the new ACL back to GS.

        :type permission: string
        :param permission: The permission being granted. Should be one of:
            READ|FULL_CONTROL
            See http://code.google.com/apis/storage/docs/developer-guide.html#authorization
            for more details on permissions.

        :type user_id: string
        :param user_id: The canonical user id associated with the GS account to
             which you are granting the permission.
        """
        acl = self.get_acl()
        acl.add_user_grant(permission, user_id)
        self.set_acl(acl)

    def add_group_email_grant(self, permission, email_address, headers=None):
        """
        Convenience method that provides a quick way to add an email group
        grant to a key. This method retrieves the current ACL, creates a new
        grant based on the parameters passed in, adds that grant to the ACL and
        then PUT's the new ACL back to GS.

        :type permission: string
        :param permission: The permission being granted. Should be one of:
            READ|FULL_CONTROL
            See http://code.google.com/apis/storage/docs/developer-guide.html#authorization
            for more details on permissions.

        :type email_address: string
        :param email_address: The email address associated with the Google
            Group to which you are granting the permission.
        """
        acl = self.get_acl(headers=headers)
        acl.add_group_email_grant(permission, email_address)
        self.set_acl(acl, headers=headers)

    def add_group_grant(self, permission, group_id):
        """
        Convenience method that provides a quick way to add a canonical group
        grant to a key. This method retrieves the current ACL, creates a new
        grant based on the parameters passed in, adds that grant to the ACL and
        then PUT's the new ACL back to GS.

        :type permission: string
        :param permission: The permission being granted. Should be one of:
            READ|FULL_CONTROL
            See http://code.google.com/apis/storage/docs/developer-guide.html#authorization
            for more details on permissions.

        :type group_id: string
        :param group_id: The canonical group id associated with the Google
            Groups account you are granting the permission to.
        """
        acl = self.get_acl()
        acl.add_group_grant(permission, group_id)
        self.set_acl(acl)

    def set_contents_from_file(self, fp, headers=None, replace=True,
                               cb=None, num_cb=10, policy=None, md5=None,
                               res_upload_handler=None):
        """
        Store an object in GS using the name of the Key object as the
        key in GS and the contents of the file pointed to by 'fp' as the
        contents.

        :type fp: file
        :param fp: the file whose contents are to be uploaded

        :type headers: dict
        :param headers: additional HTTP headers to be sent with the PUT request.

        :type replace: bool
        :param replace: If this parameter is False, the method will first check
            to see if an object exists in the bucket with the same key. If it
            does, it won't overwrite it. The default value is True which will
            overwrite the object.

        :type cb: function
        :param cb: a callback function that will be called to report
            progress on the upload. The callback should accept two integer
            parameters, the first representing the number of bytes that have
            been successfully transmitted to GS and the second representing the
            total number of bytes that need to be transmitted.

        :type num_cb: int
        :param num_cb: (optional) If a callback is specified with the cb
            parameter, this parameter determines the granularity of the callback
            by defining the maximum number of times the callback will be called
            during the file transfer.

        :type policy: :class:`boto.gs.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the new key
            in GS.

        :type md5: A tuple containing the hexdigest version of the MD5 checksum
            of the file as the first element and the Base64-encoded version of
            the plain checksum as the second element. This is the same format
            returned by the compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason prior to
            upload, it's silly to have to do it twice so this param, if present,
            will be used as the MD5 values of the file. Otherwise, the checksum
            will be computed.

        :type res_upload_handler: ResumableUploadHandler
        :param res_upload_handler: If provided, this handler will perform the
            upload.

        TODO: At some point we should refactor the Bucket and Key classes,
        to move functionality common to all providers into a parent class,
        and provider-specific functionality into subclasses (rather than
        just overriding/sharing code the way it currently works).
        """
        provider = self.bucket.connection.provider
        headers = headers or {}
        if policy:
            headers[provider.acl_header] = policy
        if hasattr(fp, 'name'):
            self.path = fp.name
        if self.bucket != None:
            if not md5:
                md5 = self.compute_md5(fp)
            else:
                # Even if md5 is provided, still need to set size of content.
                fp.seek(0, 2)
                self.size = fp.tell()
                fp.seek(0)
            self.md5 = md5[0]
            self.base64md5 = md5[1]
            if self.name == None:
                self.name = self.md5
            if not replace:
                k = self.bucket.lookup(self.name)
                if k:
                    return
            if res_upload_handler:
                res_upload_handler.send_file(self, fp, headers, cb, num_cb)
            else:
                # Not a resumable transfer so use basic send_file mechanism.
                self.send_file(fp, headers, cb, num_cb)

    def set_contents_from_filename(self, filename, headers=None, replace=True,
                                   cb=None, num_cb=10, policy=None, md5=None,
                                   reduced_redundancy=None,
                                   res_upload_handler=None):
        """
        Store an object in GS using the name of the Key object as the
        key in GS and the contents of the file named by 'filename'.
        See set_contents_from_file method for details about the
        parameters.

        :type filename: string
        :param filename: The name of the file that you want to put onto GS

        :type headers: dict
        :param headers: Additional headers to pass along with the request to GS.

        :type replace: bool
        :param replace: If True, replaces the contents of the file if it
            already exists.

        :type cb: function
        :param cb: (optional) a callback function that will be called to report
            progress on the download. The callback should accept two integer
            parameters, the first representing the number of bytes that have
            been successfully transmitted from GS and the second representing
            the total number of bytes that need to be transmitted.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with the cb
            parameter this parameter determines the granularity of the callback
            by defining the maximum number of times the callback will be called
            during the file transfer.

        :type policy: :class:`boto.gs.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the new key
            in GS.

        :type md5: A tuple containing the hexdigest version of the MD5 checksum
            of the file as the first element and the Base64-encoded version of
            the plain checksum as the second element. This is the same format
            returned by the compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason prior to
            upload, it's silly to have to do it twice so this param, if present,
            will be used as the MD5 values of the file. Otherwise, the checksum
            will be computed.

        :type res_upload_handler: ResumableUploadHandler
        :param res_upload_handler: If provided, this handler will perform the
            upload.
        """
        fp = open(filename, 'rb')
        self.set_contents_from_file(fp, headers, replace, cb, num_cb,
                                    policy, md5, res_upload_handler)
        fp.close()

    def set_contents_from_string(self, s, headers=None, replace=True,
                                 cb=None, num_cb=10, policy=None, md5=None):
        """
        Store an object in S3 using the name of the Key object as the
        key in S3 and the string 's' as the contents.
        See set_contents_from_file method for details about the
        parameters.

        :type headers: dict
        :param headers: Additional headers to pass along with the
                        request to AWS.

        :type replace: bool
        :param replace: If True, replaces the contents of the file if
                        it already exists.

        :type cb: function
        :param cb: a callback function that will be called to report
                   progress on the upload.  The callback should accept
                   two integer parameters, the first representing the
                   number of bytes that have been successfully
                   transmitted to S3 and the second representing the
                   size of the to be transmitted object.

        :type cb: int
        :param num_cb: (optional) If a callback is specified with
                       the cb parameter this parameter determines the
                       granularity of the callback by defining
                       the maximum number of times the callback will
                       be called during the file transfer.

        :type policy: :class:`boto.s3.acl.CannedACLStrings`
        :param policy: A canned ACL policy that will be applied to the
                       new key in S3.

        :type md5: A tuple containing the hexdigest version of the MD5
                   checksum of the file as the first element and the
                   Base64-encoded version of the plain checksum as the
                   second element.  This is the same format returned by
                   the compute_md5 method.
        :param md5: If you need to compute the MD5 for any reason prior
                    to upload, it's silly to have to do it twice so this
                    param, if present, will be used as the MD5 values
                    of the file.  Otherwise, the checksum will be computed.
        """
        if isinstance(s, unicode):
            s = s.encode("utf-8")
        fp = StringIO.StringIO(s)
        r = self.set_contents_from_file(fp, headers, replace, cb, num_cb,
                                        policy, md5)
        fp.close()
        return r
