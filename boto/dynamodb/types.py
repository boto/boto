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
"""
Some utility functions to deal with mapping Amazon DynamoDB types to
Python types and vice-versa.
"""
import base64


def is_num(n):
    types = (int, long, float, bool)
    return isinstance(n, types) or n in types


def is_str(n):
    return isinstance(n, basestring) or (isinstance(n, type) and
                                         issubclass(n, basestring))


def is_binary(n):
    return isinstance(n, Binary)


def convert_num(s):
    if '.' in s:
        n = float(s)
    else:
        n = int(s)
    return n


def convert_binary(n):
    return Binary(base64.b64decode(n))


def get_dynamodb_type(val):
    """
    Take a scalar Python value and return a string representing
    the corresponding Amazon DynamoDB type.  If the value passed in is
    not a supported type, raise a TypeError.
    """
    dynamodb_type = None
    if is_num(val):
        dynamodb_type = 'N'
    elif is_str(val):
        dynamodb_type = 'S'
    elif isinstance(val, (set, frozenset)):
        if False not in map(is_num, val):
            dynamodb_type = 'NS'
        elif False not in map(is_str, val):
            dynamodb_type = 'SS'
        elif False not in map(is_binary, val):
            dynamodb_type = 'BS'
    elif isinstance(val, Binary):
        dynamodb_type = 'B'
    if dynamodb_type is None:
        msg = 'Unsupported type "%s" for value "%s"' % (type(val), val)
        raise TypeError(msg)
    return dynamodb_type


def dynamize_value(val):
    """
    Take a scalar Python value and return a dict consisting
    of the Amazon DynamoDB type specification and the value that
    needs to be sent to Amazon DynamoDB.  If the type of the value
    is not supported, raise a TypeError
    """
    def _str(val):
        """
        DynamoDB stores booleans as numbers. True is 1, False is 0.
        This function converts Python booleans into DynamoDB friendly
        representation.
        """
        if isinstance(val, bool):
            return str(int(val))
        return str(val)

    dynamodb_type = get_dynamodb_type(val)
    if dynamodb_type == 'N':
        val = {dynamodb_type: _str(val)}
    elif dynamodb_type == 'S':
        val = {dynamodb_type: val}
    elif dynamodb_type == 'NS':
        val = {dynamodb_type: [str(n) for n in val]}
    elif dynamodb_type == 'SS':
        val = {dynamodb_type: [n for n in val]}
    elif dynamodb_type == 'B':
        val = {dynamodb_type: val.encode()}
    elif dynamodb_type == 'BS':
        val = {dynamodb_type: [n.encode() for n in val]}
    return val


class Binary(object):
    def __init__(self, value):
        self.value = value

    def encode(self):
        return base64.b64encode(self.value)

    def __eq__(self, other):
        if isinstance(other, Binary):
            return self.value == other.value
        else:
            return self.value == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'Binary(%s)' % self.value

    def __str__(self):
        return self.value

    def __hash__(self):
        return hash(self.value)
