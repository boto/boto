# Copyright (c) 2010 Mitch Garnaat http://garnaat.org/
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

from boto.connection import AWSQueryConnection
from boto.sdb.regioninfo import SDBRegionInfo
import boto
import uuid
try:
    import json
except ImportError:
    import simplejson as json

#boto.set_stream_logger('sns')

class SNSConnection(AWSQueryConnection):

    DefaultRegionName = 'us-east-1'
    DefaultRegionEndpoint = 'sns.us-east-1.amazonaws.com'
    APIVersion = '2010-03-31'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None, path='/', converter=None):
        if not region:
            region = SDBRegionInfo(self, self.DefaultRegionName, self.DefaultRegionEndpoint)
        self.region = region
        AWSQueryConnection.__init__(self, aws_access_key_id, aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                                    self.region.endpoint, debug, https_connection_factory, path)

    def _required_auth_capability(self):
        return ['sns']

    def get_all_topics(self, next_token=None):
        """
        :type next_token: string
        :param next_token: Token returned by the previous call to
                           this method.

        """
        params = {'ContentType' : 'JSON'}
        if next_token:
            params['NextToken'] = next_token
        response = self.make_request('ListTopics', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)
        
    def get_topic_attributes(self, topic):
        """
        Get attributes of a Topic

        :type topic: string
        :param topic: The ARN of the topic.

        """
        params = {'ContentType' : 'JSON',
                  'TopicArn' : topic}
        response = self.make_request('GetTopicAttributes', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)
        
    def add_permission(self, topic, label, account_ids, actions):
        """
        Adds a statement to a topic's access control policy, granting
        access for the specified AWS accounts to the specified actions.

        :type topic: string
        :param topic: The ARN of the topic.

        :type label: string
        :param label: A unique identifier for the new policy statement.

        :type account_ids: list of strings
        :param account_ids: The AWS account ids of the users who will be
                            give access to the specified actions.

        :type actions: list of strings
        :param actions: The actions you want to allow for each of the
                        specified principal(s).

        """
        params = {'ContentType' : 'JSON',
                  'TopicArn' : topic,
                  'Label' : label}
        self.build_list_params(params, account_ids, 'AWSAccountId')
        self.build_list_params(params, actions, 'ActionName')
        response = self.make_request('AddPermission', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)
        
    def remove_permission(self, topic, label):
        """
        Removes a statement from a topic's access control policy.

        :type topic: string
        :param topic: The ARN of the topic.

        :type label: string
        :param label: A unique identifier for the policy statement
                      to be removed.

        """
        params = {'ContentType' : 'JSON',
                  'TopicArn' : topic,
                  'Label' : label}
        response = self.make_request('RemovePermission', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)
        
    def create_topic(self, topic):
        """
        Create a new Topic.

        :type topic: string
        :param topic: The name of the new topic.

        """
        params = {'ContentType' : 'JSON',
                  'Name' : topic}
        response = self.make_request('CreateTopic', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)

    def delete_topic(self, topic):
        """
        Delete an existing topic

        :type topic: string
        :param topic: The ARN of the topic

        """
        params = {'ContentType' : 'JSON',
                  'TopicArn' : topic}
        response = self.make_request('DeleteTopic', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)



    def publish(self, topic, message, subject=None):
        """
        Get properties of a Topic

        :type topic: string
        :param topic: The ARN of the new topic.

        :type message: string
        :param message: The message you want to send to the topic.
                        Messages must be UTF-8 encoded strings and
                        be at most 4KB in size.

        :type subject: string
        :param subject: Optional parameter to be used as the "Subject"
                        line of the email notifications.

        """
        params = {'ContentType' : 'JSON',
                  'TopicArn' : topic,
                  'Message' : message}
        if subject:
            params['Subject'] = subject
        response = self.make_request('Publish', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)
        
    def subscribe(self, topic, protocol, endpoint):
        """
        Subscribe to a Topic.

        :type topic: string
        :param topic: The name of the new topic.

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

        :rtype: :class:`boto.sdb.domain.Domain` object
        :return: The newly created domain
        """
        params = {'ContentType' : 'JSON',
                  'TopicArn' : topic,
                  'Protocol' : protocol,
                  'Endpoint' : endpoint}
        response = self.make_request('Subscribe', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)

    def subscribe_sqs_queue(self, topic, queue):
        """
        Subscribe an SQS queue to a topic.

        This is convenience method that handles most of the complexity involved
        in using ans SQS queue as an endpoint for an SNS topic.  To achieve this
        the following operations are performed:
        
        * The correct ARN is constructed for the SQS queue and that ARN is
          then subscribed to the topic.
        * A JSON policy document is contructed that grants permission to
          the SNS topic to send messages to the SQS queue.
        * This JSON policy is then associated with the SQS queue using
          the queue's set_attribute method.  If the queue already has
          a policy associated with it, this process will add a Statement to
          that policy.  If no policy exists, a new policy will be created.
          
        :type topic: string
        :param topic: The name of the new topic.

        :type queue: A boto Queue object
        :param queue: The queue you wish to subscribe to the SNS Topic.
        """
        t = queue.id.split('/')
        q_arn = 'arn:aws:sqs:%s:%s:%s' % (queue.connection.region.name,
                                          t[1], t[2])
        resp = self.subscribe(topic, 'sqs', q_arn)
        policy = queue.get_attributes('Policy')
        if 'Version' not in policy:
            policy['Version'] = '2008-10-17'
        if 'Statement' not in policy:
            policy['Statement'] = []
        statement = {'Action' : 'SQS:SendMessage',
                     'Effect' : 'Allow',
                     'Principal' : {'AWS' : '*'},
                     'Resource' : q_arn,
                     'Sid' : str(uuid.uuid4()),
                     'Condition' : {'StringLike' : {'aws:SourceArn' : topic}}}
        policy['Statement'].append(statement)
        queue.set_attribute('Policy', json.dumps(policy))
        return resp

    def confirm_subscription(self, topic, token,
                             authenticate_on_unsubscribe=False):
        """
        Get properties of a Topic

        :type topic: string
        :param topic: The ARN of the new topic.

        :type token: string
        :param token: Short-lived token sent to and endpoint during
                      the Subscribe operation.

        :type authenticate_on_unsubscribe: bool
        :param authenticate_on_unsubscribe: Optional parameter indicating
                                            that you wish to disable
                                            unauthenticated unsubscription
                                            of the subscription.

        """
        params = {'ContentType' : 'JSON',
                  'TopicArn' : topic,
                  'Token' : token}
        if authenticate_on_unsubscribe:
            params['AuthenticateOnUnsubscribe'] = 'true'
        response = self.make_request('ConfirmSubscription', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)
        
    def unsubscribe(self, subscription):
        """
        Allows endpoint owner to delete subscription.
        Confirmation message will be delivered.

        :type subscription: string
        :param subscription: The ARN of the subscription to be deleted.

        """
        params = {'ContentType' : 'JSON',
                  'SubscriptionArn' : subscription}
        response = self.make_request('Unsubscribe', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)
        
    def get_all_subscriptions(self, next_token=None):
        """
        Get list of all subscriptions.

        :type next_token: string
        :param next_token: Token returned by the previous call to
                           this method.

        """
        params = {'ContentType' : 'JSON'}
        if next_token:
            params['NextToken'] = next_token
        response = self.make_request('ListSubscriptions', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)
        
    def get_all_subscriptions_by_topic(self, topic, next_token=None):
        """
        Get list of all subscriptions to a specific topic.

        :type topic: string
        :param topic: The ARN of the topic for which you wish to
                      find subscriptions.

        :type next_token: string
        :param next_token: Token returned by the previous call to
                           this method.

        """
        params = {'ContentType' : 'JSON',
                  'TopicArn' : topic}
        if next_token:
            params['NextToken'] = next_token
        response = self.make_request('ListSubscriptions', params, '/', 'GET')
        body = response.read()
        if response.status == 200:
            return json.loads(body)
        else:
            boto.log.error('%s %s' % (response.status, response.reason))
            boto.log.error('%s' % body)
            raise self.ResponseError(response.status, response.reason, body)
        
