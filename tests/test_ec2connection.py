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
Some unit tests for the EC2Connection
"""

import unittest
import time
import os
from boto.connection import EC2Connection

class EC2ConnectionTest (unittest.TestCase):

    def test_1_basic(self):
        print '--- running EC2Connection tests ---'
        c = EC2Connection()
        # create a new security group
        group_name = 'test-%d' % int(time.time())
        group_desc = 'This is a security group created during unit testing'
        status = c.create_security_group(group_name, group_desc)
        assert status
        # now get a listing of all security groups and look for our new one
        rs = c.describe_security_groups()
        found = False
        for g in rs:
            if g.name == group_name:
                found = True
        assert found
        # now pass arg to filter results to only our new group
        rs = c.describe_security_groups([group_name])
        assert len(rs) == 1
        group = rs[0]
        # now delete the security group
        status = c.delete_security_group(group_name)
        # now make sure it's really gone
        rs = c.describe_security_groups()
        found = False
        for g in rs:
            if g.name == group_name:
                found = True
        assert not found
        
        
        print '--- tests completed ---'
