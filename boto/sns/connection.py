# Copyright (c) 2010 Mitch Garnaat http://garnaat.org/
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
from xml.etree import ElementTree
import uuid

from boto.connection import AWSQueryConnection
from boto.regioninfo import RegionInfo
from boto.exception import BotoServerError
from boto.sns.topic import Topic
from boto.sns.attributes import Attributes
from boto.sns.result import PublishResult
from boto.sns.subscription import Subscription

try:
    import simplejson as json
except ImportError:
    import json

class SNSConnection(AWSQueryConnection):

    DefaultRegionName = 'us-east-1'
    DefaultRegionEndpoint = 'sns.us-east-1.amazonaws.com'
    APIVersion = '2010-03-31'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None, path='/',
                 security_token=None, sqs_protocol='sqs'):
        if not region:
            region = RegionInfo(self, self.DefaultRegionName,
                                self.DefaultRegionEndpoint,
                                connection_cls=SNSConnection)
        self.region = region
        self.sqs_protocol = sqs_protocol
        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port,
                                    proxy_user, proxy_pass,
                                    self.region.endpoint, debug,
                                    https_connection_factory, path,
                                    security_token=security_token)

    def _required_auth_capability(self):
        return ['sns']

    def _credentials_expired(self, response):
        if response.status != 403:
            return False
        try:
            for _, node in ElementTree.iterparse(response, events=['start']):
                if node.tag.endswith('Code'):
                    if node.text == 'InvalidAccessKeyId':
                        return True
        except ElementTree.ParseError:
            return False
        return False

    def get_all_topics(self, next_token=None):
        """
        :type next_token: string
        :param next_token: Token returned by the previous call to
                           this method.

        """
        params = {}
        if next_token:
            params['NextToken'] = next_token
        return self.get_list('ListTopics', params, [('Topics', Topic)])
        
    def get_topic_attributes(self, topic):
        """
        Get attributes of a Topic

        :type topic: A :class:`boto.sns.topic.Topic` object.
        :param topic: The topic to get attributes for.

        """
        params = {'TopicArn' : topic.arn}
        return self.get_object('GetTopicAttributes', params, Attributes)
        
    def set_topic_attributes(self, topic, attr_name, attr_value):
        """
        Set attributes of a Topic

        :type topic: A :class:`boto.sns.topic.Topic` object.
        :param topic: The topic to set attributes on.

        :type attr_name: string
        :param attr_name: The name of the attribute you want to set.
                          Only a subset of the topic's attributes are mutable.
                          Valid values: Policy | DisplayName

        :type attr_value: string
        :param attr_value: The new value for the attribute.

        """
        params = {'TopicArn' : topic.arn,
                  'AttributeName' : attr_name,
                  'AttributeValue' : attr_value}
        return self.get_status('SetTopicAttributes', params)
        
    def add_permission(self, topic, label, account_ids, actions):
        """
        Adds a statement to a topic's access control policy, granting
        access for the specified AWS accounts to the specified actions.

        :type topic: A :class:`boto.sns.topic.Topic` object.
        :param topic: The topic to grant access on.

        :type label: string
        :param label: A unique identifier for the new policy statement.

        :type account_ids: list of strings
        :param account_ids: The AWS account ids of the users who will be
                            give access to the specified actions.

        :type actions: list of strings
        :param actions: The actions you want to allow for each of the
                        specified principal(s).
        """
        params = {'TopicArn' : topic.arn,
                  'Label' : label}
        self.build_list_params(params, account_ids, 'AWSAccountId')
        self.build_list_params(params, actions, 'ActionName')
        return self.get_status('AddPermission', params)
        
    def remove_permission(self, topic, label):
        """
        Removes a statement from a topic's access control policy.

        :type topic: A :class:`boto.sns.topic.Topic` object.
        :param topic: The topic to remove from.

        :type label: string
        :param label: A unique identifier for the policy statement
                      to be removed.

        """
        params = {'TopicArn' : topic.arn,
                  'Label' : label}
        return self.get_status('RemovePermission', params)
        
    def create_topic(self, topic):
        """
        Create a new Topic.

        :type topic: string
        :param topic: The name of the new topic.

        """
        params = {'Name': topic}
        try:
            return self.get_object('CreateTopic', params, Topic)
        except BotoServerError:
            return None

    def delete_topic(self, topic):
        """
        Delete an existing topic

        :type topic: A :class:`boto.sns.topic.Topic` object.
        :param topic: Topic to delete

        """
        return self.get_status('DeleteTopic', {'TopicArn':topic.arn})

    def publish(self, topic, message, subject=None):
        """
        Publish to a Topic

        :type topic: A :class:`boto.sns.topic.Topic` object.
        :param topic: The Topic to publish to.

        :type message: string
        :param message: The message you want to send to the topic.
                        Messages must be UTF-8 encoded strings and
                        be at most 4KB in size.

        :type subject: string
        :param subject: Optional parameter to be used as the "Subject"
                        line of the email notifications.

        """
        params = {'TopicArn' : topic.arn,
                  'Message' : message}
        if subject:
            params['Subject'] = subject
        try:
            return self.get_object('Publish', params, PublishResult)
        except BotoServerError:
            return None
        
    def subscribe(self, topic, protocol, endpoint):
        """
        Subscribe to a Topic.

        :type topic: A :class:`boto.sns.topic.Topic` object.
        :param topic: The topic to subscribe to.

        :type protocol: string
        :param protocol: The protocol used to communicate with
                         the subscriber.  Current choices are:
                         email|email-json|http|https|sqs

        :type endpoint: string
        :param endpoint: The location of the endpoint for
                         the subscriber.
                         * For email, this would be a valid email address
                         * For email-json, this would be a valid email address
                         * For http, this would be a URL beginning with http
                         * For https, this would be a URL beginning with https
                         * For sqs, this would be the ARN of an SQS Queue

        """
        params = {'TopicArn' : topic.arn,
                  'Protocol' : protocol,
                  'Endpoint' : endpoint}
        try:
            return self.get_object('Subscribe', params, Subscription)
        except BotoServerError:
            return None


    def subscribe_sqs_queue(self, topic, queue):
        """
        Subscribe an SQS queue to a topic.

        This is convenience method that handles most of the complexity involved
        in using an SQS queue as an endpoint for an SNS topic.  To achieve this
        the following operations are performed:
        
        * The correct ARN is constructed for the SQS queue and that ARN is
          then subscribed to the topic.
        * A JSON policy document is contructed that grants permission to
          the SNS topic to send messages to the SQS queue.
        * This JSON policy is then associated with the SQS queue using
          the queue's set_attribute method.  If the queue already has
          a policy associated with it, this process will add a Statement to
          that policy.  If no policy exists, a new policy will be created.
          
        :type topic: A :class:`boto.sns.topic.Topic` object.
        :param topic: The topic to subscribe to.

        :type queue: A boto Queue object
        :param queue: The queue you wish to subscribe to the SNS Topic.
        """
        
        queue_attributes = queue.get_attributes(['Policy', 'QueueArn'])
        if 'QueueArn' not in queue_attributes:
            return None
        if 'Policy' not in queue_attributes or len(queue_attributes['Policy']) == 0:
            policy = {}
        else:
            policy = json.loads(queue_attributes['Policy'])
        
        if 'Id' not in policy:
            policy['Id'] = str(uuid.uuid4())
        if 'Version' not in policy:
            policy['Version'] = '2008-10-17'
        if 'Statement' not in policy:
            policy['Statement'] = []
        statement = {'Action' : 'SQS:SendMessage',
                     'Effect' : 'Allow',
                     'Principal' : {'AWS' : '*'},
                     'Resource' : queue_attributes['QueueArn'],
                     'Sid' : str(uuid.uuid4()),
                     'Condition' : {'StringLike' : {'aws:SourceArn' : topic.arn}}}
        policy['Statement'].append(statement)
        if queue.set_attribute('Policy', json.dumps(policy)):
            return self.subscribe(topic, self.sqs_protocol, queue_attributes['QueueArn'])
        else:
            return None

    def confirm_subscription(self, topic, token,
                             authenticate_on_unsubscribe=False):
        """
        Get properties of a Topic

        :type topic: A :class:`boto.sns.topic.Topic` object.
        :param topic: The topic which is subscribed to.

        :type token: string
        :param token: Short-lived token sent to and endpoint during
                      the Subscribe operation.

        :type authenticate_on_unsubscribe: bool
        :param authenticate_on_unsubscribe: Optional parameter indicating
                                            that you wish to disable
                                            unauthenticated unsubscription
                                            of the subscription.

        """
        params = {'TopicArn' : topic.arn,
                  'Token' : token}
        if authenticate_on_unsubscribe:
            params['AuthenticateOnUnsubscribe'] = 'true'
        
        return self.get_object('ConfirmSubscription', params, Subscription)
        
    def unsubscribe(self, subscription):
        """
        Allows endpoint owner to delete subscription.
        Confirmation message will be delivered.

        :type subscription: A :class:`boto.sns.subscription.Subscription` object.
        :param subscription: The subscription to be deleted.

        """
        return self.get_status('Unsubscribe', {'SubscriptionArn' : subscription.arn})
        
    def get_all_subscriptions(self, next_token=None):
        """
        Get list of all subscriptions.

        :type next_token: string
        :param next_token: Token returned by the previous call to
                           this method.

        """
        params = {}
        if next_token:
            params['NextToken'] = next_token
            
        return self.get_list('ListSubscriptions', params, [('Subscriptions', Subscription)])
        
    def get_all_subscriptions_by_topic(self, topic, next_token=None):
        """
        Get list of all subscriptions to a specific topic.

        :type topic: A :class:`boto.sns.topic.Topic` object.
        :param topic: The topic for which you wish to
                      find subscriptions.

        :type next_token: string
        :param next_token: Token returned by the previous call to
                           this method.

        """
        params = {'TopicArn' : topic.arn}
        if next_token:
            params['NextToken'] = next_token
        return self.get_list('ListSubscriptionsByTopic', params, [('Subscriptions', Subscription)])
