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
Represents an SQS Topic
"""

class Topic:
  
    def __init__(self, connection=None, arn=None):
        self.connection = connection
        self.arn = arn
        
    
    def __repr__(self):
        return 'Topic(%s)' % self.arn
    
    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'TopicArn':
            self.arn = value
        else:
            setattr(self, name, value)
            
    def get_attributes(self):
        """
        Retrieves attributes about this topic
        """
        return self.connection.get_topic_attributes(self)
    
    def set_attribute(self, attribute, value):
        """
        Set a new value for an attribute of the Topic.
        
        :type topic: string
        :param topic: The ARN of the topic.

        :type attr_name: string
        :param attr_name: The name of the attribute you want to set.
                          Only a subset of the topic's attributes are mutable.
                          Valid values: Policy | DisplayName

        :type attr_value: string
        :param attr_value: The new value for the attribute.
        """
        return self.connection.set_topic_attributes(self, attribute, value)
    
    def delete(self):
        """
        Delete the topic.
        """
        return self.connection.delete_topic(self)
    
    def subscribe(self, protocol, endpoint):
        """
        Subscribes endpoint to the topic
        """
        return self.connection.subscribe(self, protocol, endpoint)
    
    def subscribe_sqs_queue(self, queue):
        """
        Subscribes sqs queue to the topic
        """
        return self.connection.subscribe_sqs_queue(self, queue)
    
    def publish(self, message, subject=None):
        """
        Publishes message to topic
        """
        return self.connection.publish(self, message, subject)
    
    def add_permission(self, label, account_ids, actions):
        """
        Adds a statement to a topic's access control policy, granting
        access for the specified AWS accounts to the specified actions.
        
        :type label: string
        :param label: A unique identifier for the new policy statement.

        :type account_ids: list of strings
        :param account_ids: The AWS account ids of the users who will be
                            give access to the specified actions.

        :type actions: list of strings
        :param actions: The actions you want to allow for each of the
                        specified principal(s).
        """
        self.connection.add_permission(self, label, account_ids, actions)
        
    def remove_permission(self, label):
        """
        Removes a statement from a topic's access control policy.

        :type label: string
        :param label: A unique identifier for the policy statement
                      to be removed.
        """
        self.connection.remove_permission(self, label)
        