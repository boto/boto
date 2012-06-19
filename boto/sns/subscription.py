# Copyright (c) 2012 Derek McGowan
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
An SNS subscription
"""

from topic import Topic

class Subscription:
    def __init__(self, connection = None, arn = None):
        self.connection = connection
        self.arn = arn
    
    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'SubscriptionArn':
            self.arn = value
        elif name == 'TopicArn':
            self.topic = Topic(arn=value)
        elif name == 'Protocol':
            self.protocol = value
        elif name == 'Endpoint':
            self.endpoint = value
        elif name == 'Owner':
            self.owner = value
        else:
            setattr(self, name, value)
            
    def __repr__(self):
        return 'Subscription(%s)' % self.arn
    
    def unsubscribe(self):
        """
        Unsubscribe this subscription
        """
        self.connection.unsubscribe(self)
        