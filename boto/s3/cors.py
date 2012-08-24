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
#

class CORSRule(object):
    """
    CORS rule for a bucket.

    :ivar allowed_method: The HTTP method.

    :ivar allowed_origin: A single wildcarded domain name or a list
        of non-wildcarded domain names.

    :ivar id: Optional unique identifier for the rule. The value
        cannot be longer than 255 characters.

    :ivar max_age_seconds: An integer which alters the caching
        behavior for the pre-flight request.

    :ivar expose_header: Enables teh browser to read this header.

    :ivar allowed_header: Unsed in response to a preflight request
        to indicate which HTTP headers can be used when making the
        actual request.
    """

    ValidMethods = ('GET', 'PUT', 'HEAD', 'POST', 'DELETE')

    def __init__(self, allowed_method, allowed_origin,
                 id=None, max_age_seconds=None, expose_header=None,
                 allowed_header=None):
        if allowed_method not in self.ValidMethods:
            msg = 'allowed_method must be one of: %s' % self.ValidMethods
            raise ValueError(msg)
        if not isinstance(allowed_origin, (list, tuple)):
            if allowed_origin is None:
                allowed_origin = []
            else:
                allowed_origin = [allowed_origin]
        self.allowed_origin = allowed_origin
        self.id = id
        self.max_age_seconds = max_age_seconds
        self.expose_header = expose_header
        self.allowed_header = allowed_header

    def __repr__(self):
        return '<Rule: %s>' % self.id

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'ID':
            self.id = value
        elif name == 'AllowedMethod':
            self.allowed_method = value
        elif name == 'AllowedOrigin':
            self.allowed_origin.append(value)
        elif name == 'AllowedHeader':
            self.allowed_header = value
        elif name == 'MaxAgeSeconds':
            self.max_age_seconds = int(value)
        elif name == 'ExposeHeader':
            self.expose_header = value
        else:
            setattr(self, name, value)

    def to_xml(self):
        s = '<CORSRule>'
        for allowed_origin in self.allowed_origin:
            s += '<AllowedOrigin>%s</AllowedOrigin>' % allowed_origin
        s += '<AllowedMethod>%s</AllowedMethod>' % self.allowed_method
        if self.max_age_seconds:
            s += '<MaxAgeSeconds>%d</MaxAgeSeconds>' % self.max_age_seconds
        if self.expose_header:
            s += '<ExposeHeader>%s</ExposeHeader>' % self.expose_header
        if self.allow_header:
            s += '<AllowHeader>%s</AllowHeader>' % self.allow_header
        return s


class CORSConfiguration(list):
    """
    A container for the rules associated with a CORS configuration.
    """

    def startElement(self, name, attrs, connection):
        if name == 'CORSRule':
            rule = CORSRule()
            self.append(rule)
            return rule
        return None

    def endElement(self, name, value, connection):
        setattr(self, name, value)

    def to_xml(self):
        """
        Returns a string containing the XML version of the Lifecycle
        configuration as defined by S3.
        """
        s = '<CORSConfiguration>'
        for rule in self:
            s += rule.to_xml()
        s += '</CORSConfiguration>'
        return s

    def add_rule(self, id, prefix, status, expiration):
        """
        Add a rule to this CORS configuration.  This only adds
        the rule to the local copy.  To install the new rule(s) on
        the bucket, you need to pass this CORS config object
        to the configure_cors method of the Bucket object.

        :type allowed_method: str
        :param allowed_method: The HTTP method.

        :type allowed_origin: str or list of str
        :param allowed_origin: A single wildcarded domain name or a list
            of non-wildcarded domain names.

        :type id: str
        :iparam id: Optional unique identifier for the rule. The value
            cannot be longer than 255 characters.

        :type max_age_seconds: int
        :param max_age_seconds: An integer which alters the caching
            behavior for the pre-flight request.

        :type expose_header: str
        :param expose_header: Enables the browser to read this header.

        :type allowed_header: str
        :param allowed_header: Unsed in response to a preflight request
            to indicate which HTTP headers can be used when making the
            actual request.
        """
        rule = CORSRule(id, prefix, status, expiration)
        self.append(rule)
