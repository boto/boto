# Copyright (c) 2006-2009 Mitch Garnaat http://garnaat.org/
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

import uuid
from boto.cloudfront.identity import OriginAccessIdentity
from boto.cloudfront.object import Object, StreamingObject
from boto.cloudfront.signers import ActiveTrustedSigners, TrustedSigners
from boto.cloudfront.logging import LoggingInfo
from boto.cloudfront.origin import S3Origin, CustomOrigin
from boto.s3.acl import ACL

class DistributionConfig:

    def __init__(self, connection=None, origin=None, enabled=False,
                 caller_reference='', cnames=None, comment='',
                 trusted_signers=None, default_root_object=None,
                 logging=None):
        """
        :param origin: Origin information to associate with the
                       distribution.  If your distribution will use
                       an Amazon S3 origin, then this should be an
                       S3Origin object. If your distribution will use
                       a custom origin (non Amazon S3), then this
                       should be a CustomOrigin object.
        :type origin: :class:`boto.cloudfront.origin.S3Origin` or
                      :class:`boto.cloudfront.origin.CustomOrigin`

        :param enabled: Whether the distribution is enabled to accept
                        end user requests for content.
        :type enabled: bool
        
        :param caller_reference: A unique number that ensures the
                                 request can't be replayed.  If no
                                 caller_reference is provided, boto
                                 will generate a type 4 UUID for use
                                 as the caller reference.
        :type enabled: str
        
        :param cnames: A CNAME alias you want to associate with this
                       distribution. You can have up to 10 CNAME aliases
                       per distribution.
        :type enabled: array of str
        
        :param comment: Any comments you want to include about the
                        distribution.
        :type comment: str
        
        :param trusted_signers: Specifies any AWS accounts you want to
                                permit to create signed URLs for private
                                content. If you want the distribution to
                                use signed URLs, this should contain a
                                TrustedSigners object; if you want the
                                distribution to use basic URLs, leave
                                this None.
        :type trusted_signers: :class`boto.cloudfront.signers.TrustedSigners`
        
        :param default_root_object: Designates a default root object.
                                    Only include a DefaultRootObject value
                                    if you are going to assign a default
                                    root object for the distribution.
        :type comment: str

        :param logging: Controls whether access logs are written for the
                        distribution. If you want to turn on access logs,
                        this should contain a LoggingInfo object; otherwise
                        it should contain None.
        :type logging: :class`boto.cloudfront.logging.LoggingInfo`
        
        """
        self.connection = connection
        self.origin = origin
        self.enabled = enabled
        if caller_reference:
            self.caller_reference = caller_reference
        else:
            self.caller_reference = str(uuid.uuid4())
        self.cnames = []
        if cnames:
            self.cnames = cnames
        self.comment = comment
        self.trusted_signers = trusted_signers
        self.logging = None
        self.default_root_object = default_root_object

    def to_xml(self):
        s = '<?xml version="1.0" encoding="UTF-8"?>\n'
        s += '<DistributionConfig xmlns="http://cloudfront.amazonaws.com/doc/2010-07-15/">\n'
        if self.origin:
            s += self.origin.to_xml()
        s += '  <CallerReference>%s</CallerReference>\n' % self.caller_reference
        for cname in self.cnames:
            s += '  <CNAME>%s</CNAME>\n' % cname
        if self.comment:
            s += '  <Comment>%s</Comment>\n' % self.comment
        s += '  <Enabled>'
        if self.enabled:
            s += 'true'
        else:
            s += 'false'
        s += '</Enabled>\n'
        if self.trusted_signers:
            s += '<TrustedSigners>\n'
            for signer in self.trusted_signers:
                if signer == 'Self':
                    s += '  <Self></Self>\n'
                else:
                    s += '  <AwsAccountNumber>%s</AwsAccountNumber>\n' % signer
            s += '</TrustedSigners>\n'
        if self.logging:
            s += '<Logging>\n'
            s += '  <Bucket>%s</Bucket>\n' % self.logging.bucket
            s += '  <Prefix>%s</Prefix>\n' % self.logging.prefix
            s += '</Logging>\n'
        if self.default_root_object:
            dro = self.default_root_object
            s += '<DefaultRootObject>%s</DefaultRootObject>\n' % dro
        s += '</DistributionConfig>\n'
        return s

    def startElement(self, name, attrs, connection):
        if name == 'TrustedSigners':
            self.trusted_signers = TrustedSigners()
            return self.trusted_signers
        elif name == 'Logging':
            self.logging = LoggingInfo()
            return self.logging
        elif name == 'S3Origin':
            self.origin = S3Origin()
            return self.origin
        elif name == 'CustomOrigin':
            self.origin = CustomOrigin()
            return self.origin
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'CNAME':
            self.cnames.append(value)
        elif name == 'Comment':
            self.comment = value
        elif name == 'Enabled':
            if value.lower() == 'true':
                self.enabled = True
            else:
                self.enabled = False
        elif name == 'CallerReference':
            self.caller_reference = value
        elif name == 'DefaultRootObject':
            self.default_root_object = value
        else:
            setattr(self, name, value)

class StreamingDistributionConfig(DistributionConfig):

    def __init__(self, connection=None, origin='', enabled=False,
                 caller_reference='', cnames=None, comment='',
                 trusted_signers=None, logging=None):
        DistributionConfig.__init__(self, connection=connection,
                                    origin=origin, enabled=enabled,
                                    caller_reference=caller_reference,
                                    cnames=cnames, comment=comment,
                                    trusted_signers=trusted_signers,
                                    logging=logging)
    def to_xml(self):
        s = '<?xml version="1.0" encoding="UTF-8"?>\n'
        s += '<StreamingDistributionConfig xmlns="http://cloudfront.amazonaws.com/doc/2010-07-15/">\n'
        if self.origin:
            s += self.origin.to_xml()
        s += '  <CallerReference>%s</CallerReference>\n' % self.caller_reference
        for cname in self.cnames:
            s += '  <CNAME>%s</CNAME>\n' % cname
        if self.comment:
            s += '  <Comment>%s</Comment>\n' % self.comment
        s += '  <Enabled>'
        if self.enabled:
            s += 'true'
        else:
            s += 'false'
        s += '</Enabled>\n'
        if self.trusted_signers:
            s += '<TrustedSigners>\n'
            for signer in self.trusted_signers:
                if signer == 'Self':
                    s += '  <Self/>\n'
                else:
                    s += '  <AwsAccountNumber>%s</AwsAccountNumber>\n' % signer
            s += '</TrustedSigners>\n'
        if self.logging:
            s += '<Logging>\n'
            s += '  <Bucket>%s</Bucket>\n' % self.logging.bucket
            s += '  <Prefix>%s</Prefix>\n' % self.logging.prefix
            s += '</Logging>\n'
        s += '</StreamingDistributionConfig>\n'
        return s

class DistributionSummary:

    def __init__(self, connection=None, domain_name='', id='',
                 last_modified_time=None, status='', origin=None,
                 cname='', comment='', enabled=False):
        self.connection = connection
        self.domain_name = domain_name
        self.id = id
        self.last_modified_time = last_modified_time
        self.status = status
        self.origin = origin
        self.enabled = enabled
        self.cnames = []
        if cname:
            self.cnames.append(cname)
        self.comment = comment
        self.trusted_signers = None
        self.etag = None
        self.streaming = False

    def startElement(self, name, attrs, connection):
        if name == 'TrustedSigners':
            self.trusted_signers = TrustedSigners()
            return self.trusted_signers
        elif name == 'S3Origin':
            self.origin = S3Origin()
            return self.origin
        elif name == 'CustomOrigin':
            self.origin = CustomOrigin()
            return self.origin
        return None

    def endElement(self, name, value, connection):
        if name == 'Id':
            self.id = value
        elif name == 'Status':
            self.status = value
        elif name == 'LastModifiedTime':
            self.last_modified_time = value
        elif name == 'DomainName':
            self.domain_name = value
        elif name == 'Origin':
            self.origin = value
        elif name == 'CNAME':
            self.cnames.append(value)
        elif name == 'Comment':
            self.comment = value
        elif name == 'Enabled':
            if value.lower() == 'true':
                self.enabled = True
            else:
                self.enabled = False
        elif name == 'StreamingDistributionSummary':
            self.streaming = True
        else:
            setattr(self, name, value)

    def get_distribution(self):
        return self.connection.get_distribution_info(self.id)

class StreamingDistributionSummary(DistributionSummary):

    def get_distribution(self):
        return self.connection.get_streaming_distribution_info(self.id)
    
class Distribution:

    def __init__(self, connection=None, config=None, domain_name='',
                 id='', last_modified_time=None, status=''):
        self.connection = connection
        self.config = config
        self.domain_name = domain_name
        self.id = id
        self.last_modified_time = last_modified_time
        self.status = status
        self.active_signers = None
        self.etag = None
        self._bucket = None
        self._object_class = Object

    def startElement(self, name, attrs, connection):
        if name == 'DistributionConfig':
            self.config = DistributionConfig()
            return self.config
        elif name == 'ActiveTrustedSigners':
            self.active_signers = ActiveTrustedSigners()
            return self.active_signers
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'Id':
            self.id = value
        elif name == 'LastModifiedTime':
            self.last_modified_time = value
        elif name == 'Status':
            self.status = value
        elif name == 'DomainName':
            self.domain_name = value
        else:
            setattr(self, name, value)

    def update(self, enabled=None, cnames=None, comment=None):
        """
        Update the configuration of the Distribution.  The only values
        of the DistributionConfig that can be updated are:

         * CNAMES
         * Comment
         * Whether the Distribution is enabled or not

        :type enabled: bool
        :param enabled: Whether the Distribution is active or not.

        :type cnames: list of str
        :param cnames: The DNS CNAME's associated with this
                        Distribution.  Maximum of 10 values.

        :type comment: str or unicode
        :param comment: The comment associated with the Distribution.

        """
        new_config = DistributionConfig(self.connection, self.config.origin,
                                        self.config.enabled, self.config.caller_reference,
                                        self.config.cnames, self.config.comment,
                                        self.config.trusted_signers,
                                        self.config.default_root_object)
        if enabled != None:
            new_config.enabled = enabled
        if cnames != None:
            new_config.cnames = cnames
        if comment != None:
            new_config.comment = comment
        if origin != None:
            new_config.origin = get_oai_value(origin_access_identity)
        if trusted_signers:
            new_config.trusted_signers = trusted_signers
        if default_root_object:
            new_config.default_root_object = default_root_object
        self.etag = self.connection.set_distribution_config(self.id, self.etag, new_config)
        self.config = new_config
        self._object_class = Object

    def enable(self):
        """
        Deactivate the Distribution.  A convenience wrapper around
        the update method.
        """
        self.update(enabled=True)

    def disable(self):
        """
        Activate the Distribution.  A convenience wrapper around
        the update method.
        """
        self.update(enabled=False)

    def delete(self):
        """
        Delete this CloudFront Distribution.  The content
        associated with the Distribution is not deleted from
        the underlying Origin bucket in S3.
        """
        self.connection.delete_distribution(self.id, self.etag)

    def _get_bucket(self):
        if not self._bucket:
            bucket_name = self.config.origin.replace('.s3.amazonaws.com', '')
            from boto.s3.connection import S3Connection
            s3 = S3Connection(self.connection.aws_access_key_id,
                              self.connection.aws_secret_access_key,
                              proxy=self.connection.proxy,
                              proxy_port=self.connection.proxy_port,
                              proxy_user=self.connection.proxy_user,
                              proxy_pass=self.connection.proxy_pass)
            self._bucket = s3.get_bucket(bucket_name)
            self._bucket.distribution = self
            self._bucket.set_key_class(self._object_class)
        return self._bucket
    
    def get_objects(self):
        """
        Return a list of all content objects in this distribution.
        
        :rtype: list of :class:`boto.cloudfront.object.Object`
        :return: The content objects
        """
        bucket = self._get_bucket()
        objs = []
        for key in bucket:
            objs.append(key)
        return objs

    def set_permissions(self, object, replace=False):
        """
        Sets the S3 ACL grants for the given object to the appropriate
        value based on the type of Distribution.  If the Distribution
        is serving private content the ACL will be set to include the
        Origin Access Identity associated with the Distribution.  If
        the Distribution is serving public content the content will
        be set up with "public-read".

        :type object: :class:`boto.cloudfront.object.Object`
        :param enabled: The Object whose ACL is being set

        :type replace: bool
        :param replace: If False, the Origin Access Identity will be
                        appended to the existing ACL for the object.
                        If True, the ACL for the object will be
                        completely replaced with one that grants
                        READ permission to the Origin Access Identity.

        """
        if isinstance(self.config.origin, S3Origin):
            if self.config.origin.origin_access_identity:
                id = self.config.origin.origin_access_identity.split('/')[-1]
                oai = self.connection.get_origin_access_identity_info(id)
                policy = object.get_acl()
                if replace:
                    policy.acl = ACL()
                policy.acl.add_user_grant('READ', oai.s3_user_id)
                object.set_acl(policy)
            else:
                object.set_canned_acl('public-read')

    def set_permissions_all(self, replace=False):
        """
        Sets the S3 ACL grants for all objects in the Distribution
        to the appropriate value based on the type of Distribution.

        :type replace: bool
        :param replace: If False, the Origin Access Identity will be
                        appended to the existing ACL for the object.
                        If True, the ACL for the object will be
                        completely replaced with one that grants
                        READ permission to the Origin Access Identity.

        """
        bucket = self._get_bucket()
        for key in bucket:
            self.set_permissions(key, replace)

    def add_object(self, name, content, headers=None, replace=True):
        """
        Adds a new content object to the Distribution.  The content
        for the object will be copied to a new Key in the S3 Bucket
        and the permissions will be set appropriately for the type
        of Distribution.

        :type name: str or unicode
        :param name: The name or key of the new object.

        :type content: file-like object
        :param content: A file-like object that contains the content
                        for the new object.

        :type headers: dict
        :param headers: A dictionary containing additional headers
                        you would like associated with the new
                        object in S3.

        :rtype: :class:`boto.cloudfront.object.Object`
        :return: The newly created object.
        """
        if self.config.origin_access_identity:
            policy = 'private'
        else:
            policy = 'public-read'
        bucket = self._get_bucket()
        object = bucket.new_key(name)
        object.set_contents_from_file(content, headers=headers, policy=policy)
        if self.config.origin_access_identity:
            self.set_permissions(object, replace)
        return object
            
class StreamingDistribution(Distribution):

    def __init__(self, connection=None, config=None, domain_name='',
                 id='', last_modified_time=None, status=''):
        Distribution.__init__(self, connection, config, domain_name,
                              id, last_modified_time, status)
        self._object_class = StreamingObject

    def startElement(self, name, attrs, connection):
        if name == 'StreamingDistributionConfig':
            self.config = StreamingDistributionConfig()
            return self.config
        else:
            return Distribution.startElement(self, name, attrs, connection)

    def update(self, enabled=None, cnames=None, comment=None):
        """
        Update the configuration of the StreamingDistribution.  The only values
        of the StreamingDistributionConfig that can be updated are:

         * CNAMES
         * Comment
         * Whether the Distribution is enabled or not

        :type enabled: bool
        :param enabled: Whether the StreamingDistribution is active or not.

        :type cnames: list of str
        :param cnames: The DNS CNAME's associated with this
                        Distribution.  Maximum of 10 values.

        :type comment: str or unicode
        :param comment: The comment associated with the Distribution.

        """
        new_config = StreamingDistributionConfig(self.connection,
                                                 self.config.origin,
                                                 self.config.enabled,
                                                 self.config.caller_reference,
                                                 self.config.cnames,
                                                 self.config.comment,
                                                 self.config.trusted_signers)
        if enabled != None:
            new_config.enabled = enabled
        if cnames != None:
            new_config.cnames = cnames
        if comment != None:
            new_config.comment = comment
        self.etag = self.connection.set_streaming_distribution_config(self.id,
                                                                      self.etag,
                                                                      new_config)
        self.config = new_config
        self._object_class = StreamingObject

    def delete(self):
        self.connection.delete_streaming_distribution(self.id, self.etag)
            
        
