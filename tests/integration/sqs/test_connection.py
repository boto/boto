# Copyright (c) 2006-2010 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2010, Eucalyptus Systems, Inc.
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

"""
Some unit tests for the SQSConnection
"""

import time
from threading import Timer
from tests.unit import unittest

from boto.sqs.connection import SQSConnection
from boto.sqs.message import MHMessage
from boto.exception import SQSError


class SQSConnectionTest(unittest.TestCase):

    sqs = True

    def test_1_basic(self):
        print '--- running SQSConnection tests ---'
        c = SQSConnection()
        rs = c.get_all_queues()
        num_queues = 0
        for q in rs:
            num_queues += 1

        # try illegal name
        try:
            queue = c.create_queue('bad*queue*name')
            self.fail('queue name should have been bad')
        except SQSError:
            pass

        # now create one that should work and should be unique (i.e. a new one)
        queue_name = 'test%d' % int(time.time())
        timeout = 60
        queue = c.create_queue(queue_name, timeout)
        time.sleep(60)
        rs = c.get_all_queues()
        i = 0
        for q in rs:
            i += 1
        assert i == num_queues + 1
        assert queue.count_slow() == 0

        # check the visibility timeout
        t = queue.get_timeout()
        assert t == timeout, '%d != %d' % (t, timeout)

        # now try to get queue attributes
        a = q.get_attributes()
        assert 'ApproximateNumberOfMessages' in a
        assert 'VisibilityTimeout' in a
        a = q.get_attributes('ApproximateNumberOfMessages')
        assert 'ApproximateNumberOfMessages' in a
        assert 'VisibilityTimeout' not in a
        a = q.get_attributes('VisibilityTimeout')
        assert 'ApproximateNumberOfMessages' not in a
        assert 'VisibilityTimeout' in a

        # now change the visibility timeout
        timeout = 45
        queue.set_timeout(timeout)
        time.sleep(60)
        t = queue.get_timeout()
        assert t == timeout, '%d != %d' % (t, timeout)

        # now add a message
        message_body = 'This is a test\n'
        message = queue.new_message(message_body)
        queue.write(message)
        time.sleep(60)
        assert queue.count_slow() == 1
        time.sleep(90)

        # now read the message from the queue with a 10 second timeout
        message = queue.read(visibility_timeout=10)
        assert message
        assert message.get_body() == message_body

        # now immediately try another read, shouldn't find anything
        message = queue.read()
        assert message == None

        # now wait 30 seconds and try again
        time.sleep(30)
        message = queue.read()
        assert message

        # now delete the message
        queue.delete_message(message)
        time.sleep(30)
        assert queue.count_slow() == 0

        # try a batch write
        num_msgs = 10
        msgs = [(i, 'This is message %d' % i, 0) for i in range(num_msgs)]
        queue.write_batch(msgs)

        # try to delete all of the messages using batch delete
        deleted = 0
        while deleted < num_msgs:
            time.sleep(5)
            msgs = queue.get_messages(num_msgs)
            if msgs:
                br = queue.delete_message_batch(msgs)
                deleted += len(br.results)

        # create another queue so we can test force deletion
        # we will also test MHMessage with this queue
        queue_name = 'test%d' % int(time.time())
        timeout = 60
        queue = c.create_queue(queue_name, timeout)
        queue.set_message_class(MHMessage)
        time.sleep(30)

        # now add a couple of messages
        message = queue.new_message()
        message['foo'] = 'bar'
        queue.write(message)
        message_body = {'fie': 'baz', 'foo': 'bar'}
        message = queue.new_message(body=message_body)
        queue.write(message)
        time.sleep(30)

        m = queue.read()
        assert m['foo'] == 'bar'

        # now delete that queue and messages
        c.delete_queue(queue, True)

        print '--- tests completed ---'

    def test_sqs_timeout(self):
        c = SQSConnection()
        queue_name = 'test_sqs_timeout_%s' % int(time.time())
        queue = c.create_queue(queue_name)
        self.addCleanup(c.delete_queue, queue, True)
        start = time.time()
        poll_seconds = 2
        response = queue.read(visibility_timeout=None,
                              wait_time_seconds=poll_seconds)
        total_time = time.time() - start
        self.assertTrue(total_time > poll_seconds,
                        "SQS queue did not block for at least %s seconds: %s" %
                        (poll_seconds, total_time))
        self.assertIsNone(response)

        # Now that there's an element in the queue, we should not block for 2
        # seconds.
        c.send_message(queue, 'test message')
        start = time.time()
        poll_seconds = 2
        message = c.receive_message(
            queue, number_messages=1,
            visibility_timeout=None, attributes=None,
            wait_time_seconds=poll_seconds)[0]
        total_time = time.time() - start
        self.assertTrue(total_time < poll_seconds,
                        "SQS queue blocked longer than %s seconds: %s" %
                        (poll_seconds, total_time))
        self.assertEqual(message.get_body(), 'test message')

        attrs = c.get_queue_attributes(queue, 'ReceiveMessageWaitTimeSeconds')
        self.assertEqual(attrs['ReceiveMessageWaitTimeSeconds'], '0')

    def test_sqs_longpoll(self):
        c = SQSConnection()
        queue_name = 'test_sqs_longpoll_%s' % int(time.time())
        queue = c.create_queue(queue_name)
        self.addCleanup(c.delete_queue, queue, True)
        messages = []

        # The basic idea is to spawn a timer thread that will put something
        # on the queue in 5 seconds and verify that our long polling client
        # sees the message after waiting for approximately that long.
        def send_message():
            messages.append(
                queue.write(queue.new_message('this is a test message')))

        t = Timer(5.0, send_message)
        t.start()
        self.addCleanup(t.join)

        start = time.time()
        response = queue.read(wait_time_seconds=10)
        end = time.time()

        t.join()
        self.assertEqual(response.id, messages[0].id)
        self.assertEqual(response.get_body(), messages[0].get_body())
        # The timer thread should send the message in 5 seconds, so
        # we're giving +- .5 seconds for the total time the queue
        # was blocked on the read call.
        self.assertTrue(4.5 <= (end - start) <= 5.5)
