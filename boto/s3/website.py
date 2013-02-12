# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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

def tag(key, value):
    start = '<%s>' % key
    end = '</%s>' % key
    return '%s%s%s' % (start, value, end)


class WebsiteConfiguration(object):
    """
    Website configuration for a bucket.

    :ivar suffix: Suffix that is appended to a request that is for a
        "directory" on the website endpoint (e.g. if the suffix is
        index.html and you make a request to samplebucket/images/
        the data that is returned will be for the object with the
        key name images/index.html).  The suffix must not be empty
        and must not include a slash character.

    :ivar error_key: The object key name to use when a 4xx class error
        occurs.  This key identifies the page that is returned when
        such an error occurs.

    :ivar redirect_all_requests_to: Describes the redirect behavior for every
        request to this bucket's website endpoint. If this value is non None,
        no other values are considered when configuring the website
        configuration for the bucket. This is an instance of
        ``RedirectLocation``.

    :ivar routing_rules: ``RoutingRules`` object which specifies conditions
        and redirects that apply when the conditions are met.

    """
    WEBSITE_SKELETON = """<?xml version="1.0" encoding="UTF-8"?>
      <WebsiteConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
      %(body)s
      </WebsiteConfiguration>"""


    def __init__(self, suffix=None, error_key=None,
                 redirect_all_requests_to=None, routing_rules=None):
        self.suffix = suffix
        self.error_key = error_key
        self.redirect_all_requests_to = redirect_all_requests_to
        self.routing_rules = routing_rules

    def to_xml(self):
        body_parts = []
        if self.suffix is not None:
            body_parts.append(tag('IndexDocument', tag('Suffix', self.suffix)))
        if self.error_key is not None:
            body_parts.append(tag('ErrorDocument', tag('Key', self.error_key)))
        if self.redirect_all_requests_to is not None:
            body_parts.append(self.redirect_all_requests_to.to_xml())
        if self.routing_rules is not None:
            body_parts.append(self.routing_rules.to_xml())
        body = '\n'.join(body_parts)
        return self.WEBSITE_SKELETON % {'body': body}


class RedirectLocation(object):
    """Specify redirect behavior for every request to a bucket's endpoint.

    :ivar hostname: Name of the host where requests will be redirected.

    :ivar protocol: Protocol to use (http, https) when redirecting requests.
        The default is the protocol that is used in the original request.

    """

    def __init__(self, hostname, protocol=None):
        self.hostname = hostname
        self.protocol = protocol

    def to_xml(self):
        inner_text = []
        if self.hostname is not None:
            inner_text.append(tag('HostName', self.hostname))
        if self.protocol is not None:
            inner_text.append(tag('Protocol', self.protocol))
        return tag('RedirectAllRequestsTo', '\n'.join(inner_text))


class RoutingRules(object):
    def __init__(self):
        self._rules = []

    def add_rule(self, rule):
        """

        :type rule: :class:`boto.s3.website.RoutingRule`
        :param rule: A routing rule.

        :return: This ``RoutingRules`` object is returned,
            so that it can chain subsequent calls.

        """
        self._rules.append(rule)
        return self

    def to_xml(self):
        inner_text = []
        for rule in self._rules:
            inner_text.append(rule.to_xml())
        return tag('RoutingRules', '\n'.join(inner_text))


class RoutingRule(object):
    """Represents a single routing rule.

    There are convenience methods to making creating rules
    more concise::

        rule = RoutingRule.when(key_prefix='foo/').then_redirect('example.com')

    :ivar condition: Describes condition that must be met for the
        specified redirect to apply.

    :ivar redirect: Specifies redirect behavior.  You can redirect requests to
        another host, to another page, or with another protocol. In the event
        of an error, you can can specify a different error code to return.

    """
    def __init__(self, condition, redirect):
        self.condition = condition
        self.redirect = redirect

    def to_xml(self):
        return tag('RoutingRule',
                   self.condition.to_xml() + self.redirect.to_xml())

    @classmethod
    def when(cls, key_prefix=None, http_error_code=None):
        return cls(Condition(key_prefix=key_prefix,
                             http_error_code=http_error_code), None)

    def then_redirect(self, hostname=None, protocol=None, replace_key=None,
                      replace_key_prefix=None, http_redirect_code=None):
        self.redirect = Redirect(
                hostname=hostname, protocol=protocol,
                replace_key=replace_key,
                replace_key_prefix=replace_key_prefix,
                http_redirect_code=http_redirect_code)
        return self


class Condition(object):
    """

    :ivar key_prefix: The object key name prefix when the redirect is applied.
        For example, to redirect requests for ExamplePage.html, the key prefix
        will be ExamplePage.html. To redirect request for all pages with the
        prefix docs/, the key prefix will be /docs, which identifies all
        objects in the docs/ folder.

    :ivar http_error_code: The HTTP error code when the redirect is applied. In
        the event of an error, if the error code equals this value, then the
        specified redirect is applied.

    """
    def __init__(self, key_prefix=None, http_error_code=None):
        self.key_prefix = key_prefix
        self.http_error_code = http_error_code

    def to_xml(self):
        inner_text = []
        if self.key_prefix is not None:
            inner_text.append(tag('KeyPrefixEquals', self.key_prefix))
        if self.http_error_code is not None:
            inner_text.append(
                tag('HttpErrorCodeReturnedEquals',
                self.http_error_code))
        return tag('Condition', '\n'.join(inner_text))


class Redirect(object):
    """

    :ivar hostname: The host name to use in the redirect request.

    :ivar protocol: The protocol to use in the redirect request.  Can be either
    'http' or 'https'.

    :ivar replace_key: The specific object key to use in the redirect request.
        For example, redirect request to error.html.

    :ivar replace_key_prefix: The object key prefix to use in the redirect
        request. For example, to redirect requests for all pages with prefix
        docs/ (objects in the docs/ folder) to documents/, you can set a
        condition block with KeyPrefixEquals set to docs/ and in the Redirect
        set ReplaceKeyPrefixWith to /documents.

    :ivar http_redirect_code: The HTTP redirect code to use on the response.

    """
    def __init__(self, hostname=None, protocol=None, replace_key=None,
                 replace_key_prefix=None, http_redirect_code=None):
        self.hostname = hostname
        self.protocol = protocol
        self.replace_key = replace_key
        self.replace_key_prefix = replace_key_prefix
        self.http_redirect_code = http_redirect_code

    def to_xml(self):
        inner_text = []
        if self.hostname is not None:
            inner_text.append(tag('HostName', self.hostname))
        if self.protocol is not None:
            inner_text.append(tag('Protocol', self.protocol))
        if self.replace_key is not None:
            inner_text.append(tag('ReplaceKeyWith', self.replace_key))
        if self.replace_key_prefix is not None:
            inner_text.append(tag('ReplaceKeyPrefixWith',
                                  self.replace_key_prefix))
        if self.http_redirect_code is not None:
            inner_text.append(tag('HttpRedirectCode', self.http_redirect_code))
        return tag('Redirect', '\n'.join(inner_text))
