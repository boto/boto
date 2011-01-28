# Copyright (c) 2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010, Eucalyptus Systems, Inc.
# All rights reserved.
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

"""
Represents a hosted zone within Route 53.
"""
from boto.route53.change_info import ChangeInfo

class NameServers(list):
    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'NameServer':
            self.append(value)

class HostedZone(object):

    def __init__(self, connection=None, id=None, name=None, owner=None,
                 version=None, caller_reference=None, comment=None):
        self.connection = connection
        self.id = id
        self.name = name
        self.owner = owner
        self.version = version
        self.caller_reference = caller_reference
        self.comment = comment
        self.name_servers = NameServers()

    def __repr__(self):
        return 'HostedZone:%s' % self.id

    def startElement(self, name, attrs, connection):
        if name == 'ChangeInfo':
            self.change_info = ChangeInfo(self.connection)
            return self.change_info
        elif name == 'NameServers':
            self.name_servers = NameServers()
            return self.name_servers
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'Id':
            self.id = value.replace("/hostedzone/", "")
        elif name == 'Name':
            self.name = value
        elif name == 'Owner':
            self.owner = value
        elif name == 'Version':
            self.version = value
        elif name == 'CallerReference':
            self.caller_reference = value
        elif name == 'Comment':
            self.comment = value
        else:
            setattr(self, name, value)

    def records(self, type=None, name=None, maxitems=None):
        """
        Retrieve the resource record sets defined for this hosted
        zone.

        :type type: str
        :param type: The type of resource record set to begin the record
                     listing from.  Valid choices are:

                     * A
                     * AAAA
                     * CNAME
                     * MX
                     * NS
                     * PTR
                     * SOA
                     * SPF
                     * SRV
                     * TXT

        :type name: str
        :param name: The first name in the lexicographic ordering of domain
                     names to be retrieved

        :type maxitems: int
        :param maxitems: The maximum number of records
        """
        return self.connection.get_all_rrsets(self.id, type, name, maxitems)

    def delete(self):
        """
        Delete the hosted zone.

        :rtype: :class:`boto.route53.change_info.ChangeInfo`
        :return: The ChangeInfo result of the operation
        """
        return self.connection.delete_hosted_zone(self.id)
