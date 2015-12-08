# Copyright (c) 2012 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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

class CRRRule(object):
    """
    A CRR(Cross Region Replication) rule for an S3 bucket.

    :ivar id: Unique identifier for the rule. The value cannot be longer
        than 255 characters. This value is optional. The server will
        generate a unique value for the rule if no value is provided.

    :ivar prefix: Prefix identifying one or more objects to which the
        rule applies. If prefix is not provided, Boto generates a default
        prefix which will match all objects.

    :ivar status: If 'Enabled', the rule is currently being applied.
        If 'Disabled', the rule is not currently being applied.

    :ivar destination: An instance of `Destination`.

    """
    def __init__(self, id=None, prefix=None, status=None, destination=None):
        self.id = id
        self.prefix = '' if prefix is None else prefix
        self.status = status
        self.destination = destination

    def __repr__(self):
        return '<Rule: %s>' % self.id

    def startElement(self, name, attrs, connection):
        if name == 'Destination':
            self.destination = Destination()
            return self.destination
        return None

    def endElement(self, name, value, connection):
        if name == 'ID':
            self.id = value
        elif name == 'Prefix':
            self.prefix = value
        elif name == 'Status':
            self.status = value
        else:
            setattr(self, name, value)

    def to_xml(self):
        s = '<Rule>'
        if self.id is not None:
            s += '<ID>%s</ID>' % self.id
        s += '<Prefix>%s</Prefix>' % self.prefix
        s += '<Status>%s</Status>' % self.status
        s += self.destination.to_xml()
        s += '</Rule>'
        return s

class Destination(object):
    """
    A destination class.

    :ivar bucket: The bucket name where you want Amazon S3 to
        store replicas of the object identified by the rule.

    :ivar storage_class: The storage class to replicate to.
        Valid values are STANDARD | STANDARD_IA | REDUCED_REDUNDANCY.

    :ivar arn: The prefix of Amazon Resource Name (ARN) of the bucket.

    """
    def __init__(self, bucket=None, storage_class=None, arn='arn:aws:s3:::'):
        if bucket is not None:
            self.bucket = arn + bucket
        else:
            self.bucket = bucket
        self.storage_class = storage_class

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'Bucket':
            self.bucket = value
        elif name == 'StorageClass':
            self.storage_class = value

    def __repr__(self):
        return '<Destination: %s, %s>' % (self.bucket, self.storage_class)

    def to_xml(self):
        s = '<Destination>'
        s += '<Bucket>%s</Bucket>' % self.bucket
        if self.storage_class is not None:
            s += '<StorageClass>%s</StorageClass>' % self.storage_class
        s += '</Destination>'
        return s

class CRR(list):
    """
    A container for the rules associated with a Cross Region Replication.
    """

    def __init__(self, role=None, endpoint=None, credentials=None):
        self.role = role
        self.crr_endpoint = endpoint
        self.crr_credentials = credentials

    def startElement(self, name, attrs, connection):
        if name == 'Rule':
            crrrule = CRRRule()
            self.append(crrrule)
            return crrrule
        return None

    def endElement(self, name, value, connection):
        if name == 'Role':
            self.role = value
        setattr(self, name, value)

    def to_xml(self):
        s = '<?xml version="1.0" encoding="UTF-8"?>'
        s += '<ReplicationConfiguration>'
        s += '<Role>%s</Role>' % self.role
        for crrrule in self:
            s += crrrule.to_xml()
        s += '</ReplicationConfiguration>'
        return s

    def add_crrrule(self, id=None, prefix='', status='Enabled', destination=None):
        """
        Add a rule to this CRR configuration.  This only adds
        the rule to the local copy.  To install the new rule(s) on
        the bucket, you need to pass this CRR config object
        to the configure_crr method of the Bucket object.

        :type id: str
        :param id: Unique identifier for the rule. The value cannot be longer
            than 255 characters. This value is optional. The server will
            generate a unique value for the rule if no value is provided.

        :type prefix: str
        :iparam prefix: Prefix identifying one or more objects to which the
            rule applies.

        :type status: str
        :param status: If 'Enabled', the rule is currently being applied.
            If 'Disabled', the rule is not currently being applied.

        :type destination: Destination
        :param destination: Indicates a destination bucket and storage_class.
        """
        crrrule = CRRRule(id, prefix, status, destination)
        self.append(crrrule)
