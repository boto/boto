# Copyright (c) 2006-2009 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2011 Amazon.com, Inc. or its affiliates.
# All Rights Reserved
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

from boto.resultset import ResultSet


class Template:
    def __init__(self, connection=None):
        self.connection = connection
        self.description = None
        self.template_parameters = None

    def startElement(self, name, attrs, connection):
        if name == "Parameters":
            self.template_parameters = ResultSet([('member',
                                                   TemplateParameter)])
            return self.template_parameters
        else:
            return None

    def endElement(self, name, value, connection):
        if name == "Description":
            self.description = value
        else:
            setattr(self, name, value)


class TemplateParameter:
    def __init__(self, parent):
        self.parent = parent
        self.default_value = None
        self.description = None
        self.no_echo = None
        self.parameter_key = None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == "DefaultValue":
            self.default_value = value
        elif name == "Description":
            self.description = value
        elif name == "NoEcho":
            self.no_echo = bool(value)
        elif name == "ParameterKey":
            self.parameter_key = value
        else:
            setattr(self, name, value)
