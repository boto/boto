# Copyright 2010 Google Inc.
# All rights reserved.
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

import os
import tempfile
import atexit


class CAcerts:
    """This allows boto to work when imported from zip file using
    zipimport module.
    """
    def __init__(self):
        cacerts_file = os.path.join(os.path.dirname(__file__), "cacerts.txt")
        try:
            __loader__
        except NameError:
            self.cacerts_file = os.path.abspath(cacerts_file)
        else:
            def cleanup(f):
                f.close()

            self.cacerts_temp = tempfile.NamedTemporaryFile()
            self.cacerts_temp.write(__loader__.get_data(cacerts_file))
            self.cacerts_temp.flush()

            atexit.register(cleanup, self.cacerts_temp)

            self.cacerts_file = self.cacerts_temp.name

