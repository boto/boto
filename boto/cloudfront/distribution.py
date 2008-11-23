# Copyright (c) 2006-2008 Mitch Garnaat http://garnaat.org/
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

import uuid

class Distribution:

    def __init__(self, connection=None, config=None, domain_name='',
                 id='', last_modified_time=None, status=''):
        self.connection = connection
        self.config = config
        self.domain_name = domain_name
        self.id = id
        self.last_modified_time = last_modified_time
        self.status = status
        self.etag = None
        
    def startElement(self, name, attrs, connection):
        if name == 'DistributionConfig':
            self.config = DistributionConfig()
            return self.config
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'Id':
            self.id = value
        elif name == 'LastModifiedTime':
            self.last_modified_time = value
        elif name == 'Status':
            self.status = value
        elif name == 'DomainName':
            self.domain_name = value
        else:
            setattr(self, name, value)

    def update(self, enabled=None, cnames=None, comment=None):
        new_config = DistributionConfig(self.connection, self.config.origin,
                                        self.config.enabled, self.config.caller_reference,
                                        self.config.cnames, self.config.comment)
        if enabled != None:
            new_config.enabled = enabled
        if cnames != None:
            new_config.cnames = cnames
        if comment != None:
            new_config.comment = comment
        self.etag = self.connection.set_distribution_config(self.id, self.etag, new_config)
        self.config = new_config

    def enable(self):
        self.update(enabled=True)

    def disable(self):
        self.update(enabled=False)

    def delete(self):
        self.connection.delete_distribution(self.id, self.etag)
            
class DistributionConfig:

    def __init__(self, connection=None, origin='', enabled=False,
                 caller_reference='', cnames=None, comment=''):
        self.connection = connection
        self.origin = origin
        self.enabled = enabled
        if caller_reference:
            self.caller_reference = caller_reference
        else:
            self.caller_reference = str(uuid.uuid4())
        self.cnames = []
        if cnames:
            self.cnames = cnames
        self.comment = comment

    def to_xml(self):
        s = '<?xml version="1.0" encoding="UTF-8"?>\n'
        s += '<DistributionConfig xmlns="http://cloudfront.amazonaws.com/doc/2008-06-30/">\n'
        s += '  <Origin>%s</Origin>\n' % self.origin
        s += '  <CallerReference>%s</CallerReference>\n' % self.caller_reference
        for cname in self.cnames:
            s += '  <CNAME>%s</CNAME>\n' % cname
        if self.comment:
            s += '  <Comment>%s</Comment>\n' % self.comment
        s += '  <Enabled>'
        if self.enabled:
            s += 'true'
        else:
            s += 'false'
        s += '</Enabled>\n'
        s += '</DistributionConfig>\n'
        return s

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'CNAME':
            self.cnames.append(value)
        elif name == 'Origin':
            self.origin = value
        elif name == 'Comment':
            self.comment = value
        elif name == 'Enabled':
            if value.lower() == 'true':
                self.enabled = True
            else:
                self.enabled = False
        elif name == 'CallerReference':
            self.caller_reference = value
        else:
            setattr(self, name, value)

            
class DistributionSummary:

    def __init__(self, connection=None, domain_name='', id='',
                 last_modified_time=None, status='', origin='',
                 cname='', comment='', enabled=False):
        self.connection = connection
        self.domain_name = domain_name
        self.id = id
        self.last_modified_time = last_modified_time
        self.status = status
        self.origin = origin
        self.enabled = enabled
        self.cnames = []
        if cname:
            self.cnames.append(cname)
        self.comment = comment
        self.etag = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'Id':
            self.id = value
        elif name == 'Status':
            self.status = value
        elif name == 'LastModifiedTime':
            self.last_modified_time = value
        elif name == 'DomainName':
            self.domain_name = value
        elif name == 'Origin':
            self.origin = value
        elif name == 'CNAME':
            self.cnames.append(value)
        elif name == 'Comment':
            self.comment = value
        elif name == 'Enabled':
            if value.lower() == 'true':
                self.enabled = True
            else:
                self.enabled = False
        else:
            setattr(self, name, value)

    def get_distribution(self):
        return self.connection.get_distribution_info(self.id)

        
