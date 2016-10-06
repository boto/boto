# Copyright (c) 2016 Jonas B. Zimmermann
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
Provides ReviewPolicy, Parameter, and MapEntry classes, implementing
the AssignmentReviewPolicy and HITReviewPolicy data structures described in
http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_HITReviewPolicyDataStructureArticle.html.
To be used as arguments to boto.mturk.connection.create_hit.
"""


class ReviewPolicy(object):
    """ReviewPolicy. kind can be 'Assignment' or 'HIT'.
    paramters should be a list of Parameters.
    See http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_HITReviewPolicyDataStructureArticle.html
    """
    def __init__(self, kind='Assignment', policy_name="ScoreMyKnownAnswers/2011-09-01", parameters=None):
        self.kind = kind
        self.policy_name = policy_name
        self.parameters = parameters

    def get_as_params(self):
        prefix = '%sReviewPolicy' % (self.kind,)
        params = {
            '%s.PolicyName'%(prefix,): self.policy_name
        }
        if self.parameters is not None:
            for i, param in enumerate(self.parameters, 1):
                paramparams = param.get_as_params()
                for pp in paramparams:
                    params['%s.Parameter.%s.%s' % (prefix, i, pp) ] = paramparams[pp]
        return params

class Parameter(object):
    """Representation of a single Parameter
    A Parameter consists of a Key element (string) and either a Value (string) or one or several MapEntry structures.
    The argument map_entries should be a list of MapEntry elements.
    """
    def __init__(self, key, value=None, map_entries=None):
        self.key = key
        self.value = value
        self.map_entries = map_entries
    def get_as_params(self):
        params =  {
            "Key": self.key,
        }
        if self.map_entries is not None:
            for i, map_entry in enumerate(self.map_entries, 1):
                mapparams = map_entry.get_as_params()
                for mp in mapparams:
                    params['MapEntry.%s.%s' % (i, mp) ] = mapparams[mp]
        else:
            params['Value'] = self.value
        return params


class MapEntry(object):
    """Representation of a single MapEntry
    A MapEntry consists of a Key element (string) and one or several Values. The constructor should be called with
    either the value or the values argument set to a not-None value. The latter should be a list."""
    def __init__(self, key, value=None, values=None):
        self.key = key
        self.value = value
        self.values = values
    def get_as_params(self):
        params =  {
            "Key": self.key,
        }
        if self.values is not None:
            for i, value in enumerate(self.values, 1):
                params['Value.%d' % i] = value
        else:
            params['Value'] = self.value
        return params
