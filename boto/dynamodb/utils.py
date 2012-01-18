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
Some utility functions to deal with mapping DynamoDB types to
Python types and vice-versa.
"""

def is_num(n):
    return (isinstance(n, (int, long, float)))

def is_str(n):
    return isinstance(n, basestring)

def get_dynamodb_type(val):
    """
    Take a scalar Python value and return a string representing
    the corresponding DynamoDB type.  If the value passed in is
    not a supported type, raise a TypeError.
    """
    if is_num(val):
        dynamodb_type = 'N'
    elif is_str(val):
        dynamodb_type = 'S'
    elif isinstance(val, list):
        if False not in map(is_num, val):
            dynamodb_type = 'NS'
        elif False not in map(is_str, val):
            dynamodb_type = 'SS'
    else:
        raise TypeError('Unsupported type')
    return dynamodb_type

def dynamize_value(val):
    """
    Take a scalar Python value and return a dict consisting
    of the DynamoDB type specification and the value that
    needs to be sent to DynamoDB.  If the type of the value
    is not supported, raise a TypeError
    """
    dynamodb_type = get_dynamodb_type(val)
    if dynamodb_type == 'N':
        val = {dynamodb_type : str(val)}
    elif dynamodb_type == 'S':
        val = {dynamodb_type : val}
    elif dynamodb_type == 'NS':
        val = {dynamodb_type : [ str(n) for n in val]}
    elif dynamodb_type == 'SS':
        val = {dynamodb_type : val}
    return val

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
        except TypeError:
            return float(dct['N'])
    if 'SS' in dct:
        return dct['SS']
    if 'NS' in dct:
        try:
            return map(int, dct['NS'])
        except TypeError:
            return map(float, dct['NS'])
    return dct

