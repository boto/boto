# Copyright (c) 2010 Chris Moyer http://coredumped.org/
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

"""
Represents a Route 53 ChangeBatch for making changes to record sets.
"""
from boto.route53.record import Record

class ChangeBatch(object):

    ChangeResourceRecordSetsBody = """<?xml version="1.0" encoding="UTF-8"?>
    <ChangeResourceRecordSetsRequest xmlns="https://route53.amazonaws.com/doc/2010-10-01/">
            <ChangeBatch>
                <Comment>%(comment)s</Comment>
                <Changes>%(changes)s</Changes>
            </ChangeBatch>
    </ChangeResourceRecordSetsRequest>"""

    ChangeXML = """<Change>
        <Action>%(action)s</Action>
        %(record)s
    </Change>"""

    def __init__(self, connection=None, hosted_zone_id=None, comment=None):
        """
        Init method to create a new ChangeBatch for Route 53.

        :type connection: :class:`boto.route53.Route53Connection`
        :param connection: Optional connection object. If this isn't given
                           and the ChangeBatch is committed, a connection will
                           attempt to be obtained.

        :type hosted_zone_id: string
        :param hosted_zone_id: The zone ID for this ChangeBatch to modify. This
                               is required to commit.

        :type comment: string
        :param comment: Optional comment to associate with the ChangeBatch.
        """
        self.connection = connection
        self.hosted_zone_id = hosted_zone_id
        self.comment = comment
        self.changes = []

    def __repr__(self):
        return '<ChangeBatch: %s>' % self.hosted_zone_id

    def add_change(self, action, name, type, ttl=600, value=''):
        """
        Add a change for the given record information. Returns the
        record which will be changed.

        :type action: string
        :param action: The type of change to be made. Valid choices are:

                       * CREATE
                       * DELETE

        :type name: string
        :param name: The name you wish to perform the action on.

        :type type: string
        :param type: The type of record.

        :type ttl: int
        :param ttl: Optional TTL for the record.

        :type value: string
        :param value: Optional value for the record.

        :rtype: :class:`boto.route53.record.Record`
        :return: The record that will be changed.
        """
        record = Record(self.connection, name, type, ttl, value)
        self.changes.append((action, record))
        return record

    def to_xml(self):
        """
        Returns the XML representation for this ChangeBatch.

        :rtype: string
        :return: The XML representation for this ChangeBatch.
        """
        changes_xml = ''
        for change in self.changes:
            params = { "action": change[0], "record": change[1].to_xml() }
            changes_xml += self.ChangeXML % params

        params = { "comment": self.comment, "changes": changes_xml }
        return self.ChangeResourceRecordSetsBody % params

    def commit(self):
        """
        Commits the ChangeBatch.

        :rtype: :class:`boto.route53.change_info.ChangeInfo`
        :return: The ChangeInfo result of the operation.
        """
        if not self.connection:
            import boto
            self.connection = boto.connect_route53()

        return self.connection.change_rrsets(self.hosted_zone_id, self.to_xml())
