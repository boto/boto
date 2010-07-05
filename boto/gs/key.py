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

import boto
from boto.s3.key import Key as S3Key

class Key(S3Key):

    def add_email_grant(self, permission, email_address):
        """
        Convenience method that provides a quick way to add an email grant to a key.
        This method retrieves the current ACL, creates a new grant based on the parameters
        passed in, adds that grant to the ACL and then PUT's the new ACL back to GS.
        
        :type permission: string
        :param permission: The permission being granted.  Should be one of:
                           READ|FULL_CONTROL
                           See http://code.google.com/apis/storage/docs/developer-guide.html#authorization
                           for more details on permissions.
        
        :type email_address: string
        :param email_address: The email address associated with the AWS account you are granting
                              the permission to.
        """
        acl = self.get_acl()
        acl.add_email_grant(permission, email_address)
        self.set_acl(acl)

    def add_user_grant(self, permission, user_id):
        """
        Convenience method that provides a quick way to add a canonical user grant to a key.
        This method retrieves the current ACL, creates a new grant based on the parameters
        passed in, adds that grant to the ACL and then PUT's the new ACL back to GS.
        
        :type permission: string
        :param permission: The permission being granted.  Should be one of:
                            READ|FULL_CONTROL
                            See http://code.google.com/apis/storage/docs/developer-guide.html#authorization
                            for more details on permissions.
        
        :type user_id: string
        :param user_id: The canonical user id associated with the GS account you are granting
                        the permission to.
        """
        acl = self.get_acl()
        acl.add_user_grant(permission, user_id)
        self.set_acl(acl)
