# Copyright (c) 2006-2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010, Eucalyptus Systems, Inc.
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

import user
import key
from boto import handler
import xml.sax

class Part(object):

    def __init__(self, parent=None):
        self.parent = parent
        self.part_number = None
        self.last_modified = None
        self.etag = None
        self.size = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'PartNumber':
            self.part_number = value
        elif name == 'LastModified':
            self.last_modified = value
        elif name == 'ETag':
            self.etag = value
        elif name == 'Size':
            self.size = int(value)
        else:
            setattr(self, name, value)
        
class MultiPartUpload(object):
    
    def __init__(self, parent=None):
        self.parent = parent
        self.bucket_name = None
        self.key_name = None
        self.id = id
        self.initiator = None
        self.owner = None
        self.storage_class = None
        self.initiated = None
        self.parts = []

    def __repr__(self):
        return '<MultiPartUpload %s>' % self.id

    def startElement(self, name, attrs, connection):
        if name == 'Initiator':
            self.initiator = user.User(self)
            return self.initiator
        elif name == 'Owner':
            self.owner = user.User(self)
            return self.owner
        elif name == 'Part':
            part = Part(self.parent)
            self.parts.append(part)
            return part
        return None

    def endElement(self, name, value, connection):
        if name == 'Bucket':
            self.bucket_name = value
        elif name == 'Key':
            self.key_name = value
        elif name == 'UploadId':
            self.id = value
        elif name == 'StorageClass':
            self.storage_class = value
        elif name == 'Initiated':
            self.initiated = value
        else:
            setattr(self, name, value)

    def list_parts(self):
        query_args = 'uploadId=%s' % self.id
        response = self.parent.connection.make_request('GET', self.parent.name,
                                                       self.key_name,
                                                       query_args=query_args)
        body = response.read()
        if response.status == 200:
            h = handler.XmlHandler(self, self)
            xml.sax.parseString(body, h)
            return self.parts

    def upload_part_from_file(self, fp, part_num, headers=None, replace=True,
                               cb=None, num_cb=10, policy=None, md5=None,
                               reduced_redundancy=False):
        query_args = 'uploadId=%s&partNumber=%d' % (self.id, part_num)
        key = self.parent.new_key(self.key_name)
        key.set_contents_from_file(fp, headers, replace, cb, num_cb, policy,
                                   md5, reduced_redundancy, query_args)

class MultiPartUploadList(object):

    def __init__(self, parent=None):
        self.parent = parent
        self.bucket = None
        self.key_marker = None
        self.upload_marker = None
        self.next_key_marker = None
        self.next_upload_id_marker = None
        self.max_uploads = None
        self.is_truncated = None
        self.uploads = []

    def startElement(self, name, attrs, connection):
        if name == 'Upload':
            upload = MultiPartUpload(self.parent)
            self.uploads.append(upload)
            return upload
        return None

    def endElement(self, name, value, connection):
        if name == 'Bucket':
            self.bucket = value
        elif name == 'KeyMarker':
            self.key_marker = value
        elif name == 'UploadId':
            self.id = value
        elif name == 'NextKeyMarker':
            self.next_key_marker = value
        elif name == 'NextUploadIdMarker':
            self.next_upload_id_marker = value
        elif name == 'MaxUploads':
            self.max_uploads = int(value)
        elif name == 'IsTruncated':
            self.is_truncated = value
        else:
            setattr(self, name, value)

