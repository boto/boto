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

class Batch(object):
    """
    :ivar table: The Table object from which the item is retrieved.

    :ivar keys: A list of scalar or tuple values.  Each element in the
        list represents one Item to retrieve.  If the schema for the
        table has both a HashKey and a RangeKey, each element in the
        list should be a tuple consisting of (hash_key, range_key).  If
        the schema for the table contains only a HashKey, each element
        in the list should be a scalar value of the appropriate type
        for the table schema.
        
    :ivar attributes_to_get: A list of attribute names.
        If supplied, only the specified attribute names will
        be returned.  Otherwise, all attributes will be returned.
    """

    def __init__(self, table, keys, attributes_to_get=None):
        self.table = table
        self.keys = keys
        self.attributes_to_get = attributes_to_get
        
class BatchList(list):
    """
    A subclass of a list object that contains a collection of
    :class:`boto.dynamodb.batch.Batch` objects.
    """

    def __init__(self, layer2):
        list.__init__(self)
        self.layer2 = layer2

    def add_batch(self, table, keys, attributes_to_get=None):
        """
        Add a Batch to this BatchList.
        
        :type table: :class:`boto.dynamodb.table.Table`
        :param table: The Table object in which the items are contained.

        :type keys: list
        :param keys: A list of scalar or tuple values.  Each element in the
            list represents one Item to retrieve.  If the schema for the
            table has both a HashKey and a RangeKey, each element in the
            list should be a tuple consisting of (hash_key, range_key).  If
            the schema for the table contains only a HashKey, each element
            in the list should be a scalar value of the appropriate type
            for the table schema.
        
        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.
        """
        self.append(Batch(table, keys, attributes_to_get))

    def submit(self):
        return self.layer2.batch_get_item(self)

        

