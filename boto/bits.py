# Copyright (c) 2006 Mitch Garnaat http://garnaat.org/
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

# State Constants
BITS_LOOSE=0      # Bits object not yet associated with a BitBucket object
BITS_NEED_READ=1  # data in the Bits object needs to be read from S3
BITS_NEED_WRITE=2 # data in the Bits object needs to be written to S3
BITS_IN_SYNC=3    # data in the Bits object is consistent with S3

class Bits:

    def __init__(self, filename=None):
        self.state = BITS_LOOSE
        self.metadata = {}
        self.bucket = None
        self.content_type = 'application/octet-stream'
        self.filename = filename
        self.etag = None
        self.key = None
        self.last_modified = None
        self.owner = None
        self.storage_class = None

    def __getattr__(self, name):
        if name == 'data':
            if self.state == BITS_NEED_READ:
                if self.bucket:
                    self.bucket.get_bits(self)
            return self._data
        elif name in self.metadata:
            return self.metadata[name]
        else:
            raise AttributeError

    def __setattr__(self, name, value):
        if name == 'data':
            self._data = value
            if value:
                self.__dict__['size'] = len(value)
            if self.bucket:
                self.bucket.send_bits(self)
        elif name == 'filename':
            self.__dict__[name] = value
            if value:
                self.sync()
        else:
            self.__dict__[name] = value

    def __getitem__(self, key):
        return self.metadata[key]

    def __setitem__(self, key, value):
        self.metadata[key] = value

    def __delitem__(self, key):
        del self.metadata[key]

    def _compute_md5(self):
        m = md5.new()
        p = open(self.filename, 'rb')
        s = p.read(8192)
        while s:
            m.update(s)
            s = p.read(8192)
        self.md5 = '"%s"' % m.hexdigest()
        p.close()

    def sync(self):
        if self.filename:
            if os.path.exists(self.filename):
                self.size = os.stat(self.filename).st_size
                self._compute_md5()
                self.content_type = mimetypes.guess_type(self.filename)[0]
                filter_bits(self)
                self.state = BITS_NEED_WRITE
                if self.bucket:
                    self.bucket.send_file(self)
            else:
                self.state = BITS_NEED_READ
                if self.bucket:
                    self.bucket.get_file(self, self.filename)
        else:
            self.state = BITS_NEED_WRITE
            self.bucket.send_bits(self)

    def get_url(self, expires_in=60):
        if self.bucket:
            return self.bucket.generate_url('get', self, expires_in)
        else:
            raise BitBucketError("Bits aren't associated with a BitBucket yet")

    def delete_url(self, expires_in=60):
        if self.bucket:
            return self.bucket.generate_url('delete', self, expires_in)
        else:
            raise BitBucketError("Bits aren't associated with a BitBucket yet")

    def set_canned_acl(self, policy):
        if policy not in _canned_access_policies:
            raise BitBucketError('Invalid acl_policy: %s' % policy)
        self.bucket.connection.set_canned_acl(self, policy)

    def get_acl(self, headers={}):
        path = '/%s/%s?acl' % (self.bucket.name,
                               urllib.quote.quote_plus(self.key))
        response = self.make_request('GET', path, headers)
        return response.read()

    def to_file(self, filename):
        if self.bucket != None:
            self.bucket.get_file(self, filename)
        else:
            raise BitBucketError("Bits aren't associated with a BitBucket yet")

