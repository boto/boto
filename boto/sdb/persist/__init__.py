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

import boto
from boto.utils import find_class
from boto.exception import SDBPersistanceError

__sdb = None
__domain = None
__s3_conn = None
        
def set_domain(domain_name, aws_access_key_id=None, aws_secret_access_key=None):
    """
    Set the domain in which persisted objects will be stored
    """
    global __sdb, __domain
    __sdb = boto.connect_sdb(aws_access_key_id=aws_access_key_id,
                             aws_secret_access_key=aws_secret_access_key)
    __domain = __sdb.lookup(domain_name)
    if not __domain:
        __domain = __sdb.create_domain(domain_name)

def get_domain():
    if __domain == None:
        # check to see if a default domain is set in boto config
        domain_name = boto.config.get('Persist', 'default_domain', None)
        if domain_name:
            boto.log.info('No SimpleDB domain set, using default_domain: %s' % domain_name)
            set_domain(domain_name)
        else:
            boto.log.warning('No SimpleDB domain set, persistance is disabled')
    return __domain

def get_s3_connection():
    global __s3_conn
    if __s3_conn == None:
        __s3_conn = boto.connect_s3()
    return __s3_conn

def revive_object_from_id(id):
    domain = get_domain()
    attrs = domain.get_attributes(id, ['__module__', '__type__', '__lineage__'])
    cls = find_class(attrs['__module__'], attrs['__type__'])
    return cls(id)

def object_lister(cls, query_lister):
    for item in query_lister:
        if cls:
            yield cls(item.name)
        else:
            yield revive_object_from_id(item.name)

