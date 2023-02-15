# Copyleft (c) hankjohn.net
# Usage:
# sqs=boto.sqs.connect_to_region('us-east-1')
# bucket=boto.s3.connect_to_region('us-east-1').get_bucket('username.sqs.bucket')
# conn=SQS3Connection(sqs,bucket)
# q=conn.create_queue('sqs3')
# conn.send_message(q, 'hello, world1' * 1024 * 1024)
# msg=conn.receive_message(q, number_messages=10, wait_time_seconds=20)
# for m in msg:
#     print m.get_body()
#     conn.delete_message(q, m)
    
import os
import json
import uuid
import base64
from boto.sqs.connection import SQSConnection

class SQS3Connection(SQSConnection):
    """
    A Connection to the SQS and S3 Service.
    """
    MESSAGE_MAX_LIFE_CYCLE = 3600 * 24 * 14
    KEY_S3_KEY = 's3_key'
    KEY_S3_URL = 's3_url'
    def __init__(self, sqs, s3bucket):
        self.__dict__ = sqs.__dict__
        self.s3bucket = s3bucket

    def _message_to_s3(self, message_content):
        s3_key_str = str(uuid.uuid4())
        s3_key = self.s3bucket.new_key(s3_key_str)
        s3_key.set_contents_from_string(message_content)
        s3_message_url = s3_key.generate_url(self.MESSAGE_MAX_LIFE_CYCLE)
        message_encoded = base64.b64encode(
                json.dumps({
                    self.KEY_S3_KEY : s3_key_str,
                    self.KEY_S3_URL : s3_message_url
                    })
                )
        return message_encoded

    def send_message(self, queue, message_content, **kwargs):
        """
        First send message to S3,
        Then send the s3 url and key to SQS
        """
        message_encoded = self._message_to_s3(message_content)
        return SQSConnection.send_message(self, queue, message_encoded, **kwargs)

    def receive_message(self, *args, **kwargs):
        """
        First receive message from SQS,
        Then read data from S3.
        """
        messages = SQSConnection.receive_message(self, *args, **kwargs)
        for message in messages:
            try:
                message.from_s3 = False
                s3_pointer = json.loads(message.get_body())
                message.s3_key = self.s3bucket.get_key(s3_pointer[self.KEY_S3_KEY])
                if not message.s3_key is None:
                    message.set_body(message.s3_key.get_contents_as_string())
                message.from_s3 = True
            except ValueError:
                message.s3_key = None
            except TypeError:
                message.s3_key = None
        return messages

    def delete_message(self, queue, message):
        """
        First delete message from SQS,
        Then delete the key from S3.
        """
        response = SQSConnection.delete_message(self, queue, message)
        if not message.s3_key is None:
            message.s3_key.delete()
        return response
        
    def send_message_batch(self, queue, messages):
        """
        Firt send messages to S3,
        Then send the url and key to SQS.
        """
        for message : messages:
            message[1] = self._message_to_s3(message[1])
        return SQSConnection.send_message_batch(self, queue, messages)
        
    def delete_message_batch(self, queue, messages):
        """
        First delete messages from SQS
        Then delete the keys from S3.
        """
        response = SQSConnection.delete_message_batch(self, queue, messages)
        for message in messages:
            if not message.s3_key is None:
                message.s3_key.delete()
        return response
