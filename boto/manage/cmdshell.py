# Copyright (c) 2006-2009 Mitch Garnaat http://garnaat.org/
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

from boto.mashups.interactive import interactive_shell
import boto
import os
import time
import shutil
import StringIO
import paramiko
import socket
import subprocess


class SSHClient(object):

    def __init__(self, server, host_key_file='~/.ssh/known_hosts', uname='root'):
        self.server = server
        self.host_key_file = host_key_file
        self.uname = uname
        self._pkey = paramiko.RSAKey.from_private_key_file(server.ssh_key_file)
        self._ssh_client = paramiko.SSHClient()
        self._ssh_client.load_system_host_keys()
        self._ssh_client.load_host_keys(os.path.expanduser(host_key_file))
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect()

    def connect(self):
        retry = 0
        while retry < 5:
            try:
                self._ssh_client.connect(self.server.hostname, username=self.uname, pkey=self._pkey)
                return
            except socket.error, (value,message):
                if value == 61:
                    print 'SSH Connection refused, will retry in 5 seconds'
                    time.sleep(5)
                    retry += 1
                else:
                    raise
            except paramiko.BadHostKeyException:
                print "%s has an entry in ~/.ssh/known_hosts and it doesn't match" % self.server.hostname
                print 'Edit that file to remove the entry and then hit return to try again'
                raw_input('Hit Enter when ready')
                retry += 1
            except EOFError:
                print 'Unexpected Error from SSH Connection, retry in 5 seconds'
                time.sleep(5)
                retry += 1
        print 'Could not establish SSH connection'

    def get_file(self, src, dst):
        sftp_client = self._ssh_client.open_sftp()
        sftp_client.get(src, dst)

    def put_file(self, src, dst):
        sftp_client = self._ssh_client.open_sftp()
        sftp_client.put(src, dst)

    def listdir(self, path):
        sftp_client = self._ssh_client.open_sftp()
        return sftp_client.listdir(path)

    def open_sftp(self):
        return self._ssh_client.open_sftp()

    def isdir(self, path):
        status = self.run('[ -d %s ] || echo "FALSE"' % path)
        if status[1].startswith('FALSE'):
            return 0
        return 1

    def exists(self, path):
        status = self.run('[ -a %s ] || echo "FALSE"' % path)
        if status[1].startswith('FALSE'):
            return 0
        return 1

    def shell(self):
        channel = self._ssh_client.invoke_shell()
        interactive_shell(channel)

    def run(self, command):
        boto.log.info('running:%s on %s' % (command, self.server.instance_id))
        log_fp = StringIO.StringIO()
        status = 0
        try:
            t = self._ssh_client.exec_command(command)
        except paramiko.SSHException:
            status = 1
        log_fp.write(t[1].read())
        log_fp.write(t[2].read())
        t[0].close()
        t[1].close()
        t[2].close()
        boto.log.info('output: %s' % log_fp.getvalue())
        return (status, log_fp.getvalue())

    def close(self):
        transport = self._ssh_client.get_transport()
        transport.close()
        self.server.reset_cmdshell()

class LocalClient(object):

    def __init__(self, server, host_key_file=None, uname='root'):
        self.server = server
        self.host_key_file = host_key_file
        self.uname = uname

    def get_file(self, src, dst):
        shutil.copyfile(src, dst)

    def put_file(self, src, dst):
        shutil.copyfile(src, dst)

    def listdir(self, path):
        return os.listdir(path)

    def isdir(self, path):
        return os.path.isdir(path)

    def exists(self, path):
        return os.path.exists(path)

    def shell(self):
        raise NotImplementedError, 'shell not supported with LocalClient'

    def run(self):
        boto.log.info('running:%s' % self.command)
        log_fp = StringIO.StringIO()
        process = subprocess.Popen(self.command, shell=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while process.poll() == None:
            time.sleep(1)
            t = process.communicate()
            log_fp.write(t[0])
            log_fp.write(t[1])
        boto.log.info(log_fp.getvalue())
        boto.log.info('output: %s' % log_fp.getvalue())
        return (process.returncode, log_fp.getvalue())

    def close(self):
        pass

def start(server):
    instance_id = boto.config.get('Instance', 'instance-id', None)
    if instance_id == server.instance_id:
        return LocalClient(server)
    else:
        return SSHClient(server)
