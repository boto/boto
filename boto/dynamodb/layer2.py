# Copyright (c) 2011 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2011 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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

from layer1 import Layer1
from table import Table

class Layer2(object):

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 host=None, debug=0):
        self.layer1 = Layer1(aws_access_key_id, aws_secret_access_key,
                             is_secure, port, proxy, proxy_port,
                             host, debug)

    def get_all_table_names(self):
        """
        Return a list of the names of all Tables associated with the
        current account and region.
        """
        return self.layer1.list_tables()

    def get_table(self, table_name):
        """
        Retrieve the Table object for an existing table.

        :type table_name: str
        :param table_name: The name of the desired table.

        :rtype: :class:`boto.dynamodb.table.Table`
        :return: A Table object representing the table.
        """
        response = self.layer1.describe_table(table_name)
        return Table(self.layer1,  response)
