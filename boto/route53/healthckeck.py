# Copyright (c) 2013 PressLabs SRL, Calin Don
# www.presslabs.com
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


class Healthcheck(object):
    """
    A Route53 Healthcheck.

    :ivar Route53Connection route53connection
    :ivar str id: The ID of the healthcheck
    :ivar str type: Type of the heathcheck ('tcp' or 'http')
    :ivar str ip: The target ip of the check
    :ivar int port: The target port of the check
    :ivar str path: The path of 'http' check
    :ivar str host: The host header for 'http' check
    """
    def __init__(self, route53connection, check_dict):
        self.route53connection = route53connection
        id = check_dict['Id']
        check_dict = check_dict['HealthCheckConfig']
        for key in check_dict:
            if key == 'FullyQualifiedDomainName':
                self.__setattr__('host', check_dict[key])
            elif key == 'IPAddress':
                self.__setattr__('ip', check_dict[key])
            elif key == 'ResourcePath':
                self.__setattr__('path', check_dict[key])
            elif key == 'Type':
                self.__setattr__('type', check_dict[key].lower())
            elif key == 'Port':
                self.__setattr__('port', int(check_dict[key]))
            else:
                self.__setattr__(key.lower(), check_dict[key])
        self.id = id

    def __repr__(self):
        return '<Healthcheck:%s (%s:%d)>' % (self.id, self.ip, self.port)

    def delete(self):
        """ Request AWS to delete this healthcheck """
        self.route53connection.delete_healthcheck(self.id)
