#!/usr/bin/env python
# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
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
#

try:
    import paramiko
    import time
    from boto.manage.cmdshell import SSHClient, sshclient_from_instance
except ImportError:
    paramiko = None
    time = None
    SSHClient = None
    sshclient_from_instance = None

from tests.compat import mock, unittest

def patch_sshclient_with(mock_constructor):
    unpatched_sshclient = paramiko.SSHClient

    def patched_constructor():
        return mock_constructor(unpatched_sshclient)

    paramiko.SSHClient = patched_constructor
    paramiko.RSAKey.from_private_key_file = mock.Mock()

def mock_with_transport(unpatched_sshclient):
    mock_transport = mock.Mock()

    client = unpatched_sshclient()

    client.connect = mock.Mock(name='connect')
    client.get_transport = mock.Mock(return_value=mock_transport)

    return client

class TestSSHTimeout(unittest.TestCase):
    @unittest.skipIf(not paramiko, 'Paramiko missing')
    def test_timeout(self):
        def client_mock(unpatched_sshclient):
            client = unpatched_sshclient()
            client.connect = mock.Mock(name='connect')
            return client

        patch_sshclient_with(client_mock)

        server = mock.Mock()
        test = SSHClient(server)

        self.assertEqual(test._ssh_client.connect.call_args[1]['timeout'], None)

        test2 = SSHClient(server, timeout=30)

        self.assertEqual(test2._ssh_client.connect.call_args[1]['timeout'], 30)

class TestSSHRetries(unittest.TestCase):
    @mock.patch('time.sleep', return_value=None)
    @unittest.skipIf(not paramiko, 'Paramiko missing')
    def test_retries(self, patched_time_sleep):
        client_tmp = paramiko.SSHClient

        def client_mock(unpatched_sshclient):
            client = unpatched_sshclient()

            # When attempting connection, always throw EOFError; we'll make
            # sure the connection gets retried the specified number of times
            client.connect = mock.Mock(name='connect', side_effect=EOFError())

            return client

        patch_sshclient_with(client_mock)

        server = mock.Mock()

        test = SSHClient(server, num_retries=3)

        self.assertEqual(test._ssh_client.connect.call_count, 3)

    @unittest.skipIf(not paramiko, 'Paramiko missing')
    def test_is_connected(self):
        patch_sshclient_with(mock_with_transport)

        server = mock.Mock()
        test = SSHClient(server)

        self.assertTrue(server.is_connected())

        def negative_mock(unpatched_sshclient):
            client = unpatched_sshclient()

            client.connect = mock.Mock(name='connect')
            client.get_transport = mock.Mock(return_value=None)

            return client

        patch_sshclient_with(negative_mock)

        test = SSHClient(server)

        self.assertFalse(test.is_connected())

    @unittest.skipIf(not paramiko, 'Paramiko missing')
    def test_sshclient_from_instance_close(self):
        patch_sshclient_with(mock_with_transport)

        instance = mock.Mock()
        instance.id = 42
        instance.dns_name = 'test.server.blah'

        server = sshclient_from_instance(instance, '/dev/null')

        # This shouldn't throw an exception
        server.close()
