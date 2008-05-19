# Copyright (c) 2006,2007,2008 Mitch Garnaat http://garnaat.org/
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

import warnings
import boto
from boto.utils import find_class
from boto.exception import SDBPersistanceError

class Context:
    """
    Holds SDB Connection and Domain objects in a thread-safe manner.
    """

    def __init__(self, domain_name=None, aws_access_key_id=None, aws_secret_access_key=None):
        if not domain_name:
            # check to see if a default domain is set in boto config
            domain_name = boto.config.get('Persist', 'default_domain', None)
            boto.log.info('No SimpleDB domain specified, using default_domain: %s' % domain_name)
        self.domain_name = domain_name
        self.sdb_conn = boto.connect_sdb(aws_access_key_id=aws_access_key_id,
                                         aws_secret_access_key=aws_secret_access_key)
        if self.domain_name:
            self.domain = self.sdb_conn.lookup(self.domain_name)
            if not self.domain:
                self.domain = self.sdb_conn.create_domain(self.domain_name)
        else:
            boto.log.warning('No SimpleDB domain set, persistance is disabled')
            self.domain = None

def get_context(domain_name=None, aws_access_key_id=None, aws_secret_access_key=None):
    return Context(domain_name, aws_access_key_id, aws_secret_access_key)

def set_domain(domain_name):
    """
    Set the default domain in which persisted objects will be stored.
    """
    warnings.warn('set_domain is deprecated, create a Context object instead',
                  DeprecationWarning, stacklevel=2)
    boto.config.set('Persist', 'default_domain', domain_name)

def get_domain():
    warnings.warn('get_domain is deprecated, create a Context object instead',
                  DeprecationWarning, stacklevel=2)
    context = get_context()
    return context.domain

def revive_object_from_id(id, context=None):
    if not context:
        context = get_context()
    attrs = context.domain.get_attributes(id, ['__module__', '__type__', '__lineage__'])
    try:
        cls = find_class(attrs['__module__'], attrs['__type__'])
        return cls(id, context)
    except:
        return None

def object_lister(cls, query_lister, context=None):
    for item in query_lister:
        if cls:
            yield cls(item.name, context)
        else:
            o = revive_object_from_id(item.name, context)
            if o:
                yield o
                

