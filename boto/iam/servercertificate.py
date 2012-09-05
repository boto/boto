# Copyright (c) 2012 Gertjan Oude Lohuis, Byte Internet http://byte.nl/
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


class ServerCertificate(object):
    """
    Represents an IAM ServerCertificate
    """
    
    # Note: ServerCertificateName is used as unique identifier

    def __init__(self, connection=None, name=None):
        self.connection  = connection
        self.name        = name
        self.arn         = None
        self.body        = None
        self.chain       = None
        self.id          = None
        self.path        = None
        self.upload_date = None
    
    def __repr__(self):
        return 'ServerCertificate:%s' % self.name
    
    def startElement(self, name, attrs, connection):
        pass
    
    def endElement(self, name, value, connection):
        if name == 'Arn':
            self.arn = value
        elif name == 'CertificateBody':
            self.body = value
        elif name == 'CertificateChain':
            self.chain = value
        elif name == 'Path':
            self.path = value
        elif name == 'ServerCertificateId':
            self.id = value
        elif name == 'ServerCertificateName':
            self.name = value
        elif name == 'UploadDate':
            self.upload_date = value
        else:
            setattr(self, name, value)
    
    def modify(self, new_certname=None, new_path=None):
        """
        Updates the name and/or the path of the specified server certificate.
        
        :type new_cert_name: string
        :param new_cert_name: The new name for the server certificate.
            Include this only if you are updating the
            server certificate's name.
        
        :type new_path: string
        :param new_path: If provided, the path of the certificate will be
            changed to this path.
        """
        rs = self.connection.update_server_cert(self.name,
            new_certname, new_path)

        if rs:
            if new_certname:
                self.name = new_certname
            if new_path:
                self.path = new_path

        return rs
