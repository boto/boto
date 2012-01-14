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

def item_object_hook(dct):
    """
    A custom object hook for use when decoding JSON item bodys.
    This hook will transform DynamoDB JSON responses to something
    that maps directly to native Python types.
    """
    if 'S' in dct:
        return dct['S']
    if 'N' in dct:
        try:
            return int(dct['N'])
        except ValueError:
            return float(dct['N'])
    if 'SS' in dct:
        return dct['SS']
    if 'NS' in dct:
        try:
            return map(int, dct['NS'])
        except ValueError:
            return map(float, dct['NS'])
    return dct

class Item(dict):

    def __init__(self, table, hash_key, range_key=None,
                 attributes_to_get=None, consistent_read=False):
        dict.__init__(self)
        self.table = table
        self.layer1 = table.layer1
        self.hash_key = hash_key
        self.range_key = range_key
        self.attributes_to_get = attributes_to_get
        self.reads_used = 0
        self.key = self.table.schema.build_key_from_values(self.hash_key,
                                                           self.range_key)
        response = self.layer1.get_item(self.table.name, self.key,
                                        self.attributes_to_get,
                                        consistent_read,
                                        object_hook=item_object_hook)
        self._update(response)
                                             
    def _update(self, response):
        """
        Populate the fields of the Item object with values
        from a JSON Item response that has been decoded to
        a Python dictionary.
        """
        self.update(response['Item'])
        self.reads_used = response['ReadsUsed']
        print response

    def delete(self):
        """
        Delete the item from DynamoDB.
        """
        response = self.layer1.delete_item(self.table.name, self.key)
