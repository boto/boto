#!/usr/bin/env python

# Copyright (c) 2006 Mitch Garnaat http://garnaat.org/
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

import unittest
import time
from boto.connection import SQSConnection
from boto.message import Message
from boto.exception import SQSError

class SQSConnectionTest (unittest.TestCase):

    def test_1_basic(self):
        print '--- running SQSConnection tests ---'
        c = SQSConnection()
        rs = c.get_all_queues()
        num_queues = len(rs)
    
        # try illegal name
        try:
            queue = c.create_queue('bad_queue_name')
        except SQSError:
            pass
        else:
            fail('expected an SQSError')
        
        # now create one that should work and should be unique (i.e. a new one)
        queue_name = 'test%d' % int(time.time())
        timeout = 60
        queue = c.create_queue(queue_name, timeout)
        rs  = c.get_all_queues()
        assert len(rs) == num_queues+1
        assert queue.count() == 0

        # check the visibility timeout
        t = queue.get_timeout()
        assert int(t) == timeout, '%d != %d' % (int(t), timeout)
    
        # now add a message
        message_body = 'This is a test'
        message = Message(queue, message_body)
        queue.write(message)
        time.sleep(5)
        assert queue.count() == 1
        time.sleep(10)

        # now read the message from the queue
        message = queue.read()
        assert message
        assert message.get_body() == message_body

        # now delete the message
        queue.delete_message(message)
        time.sleep(5)
        assert queue.count() == 0

        # now delete that queue
        c.delete_queue(queue)
        rs = c.get_all_queues()
        assert len(rs) == num_queues

        print '--- tests completed ---'
    
