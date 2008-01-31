# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
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
High-level abstraction of an EC2 server
"""
import boto
from boto.mashups.iobject import IObject
from boto.pyami.config import Config
from boto.pyami.loadboto import MetadataConfigPath
from boto.mashups.interactive import interactive_shell
from boto.sdb.persist.object import SDBObject
from boto.sdb.persist.property import *
import os, time, tempfile

class ServerSet(list):

    def __getattr__(self, name):
        results = []
        is_callable = False
        for server in self:
            try:
                val = getattr(server, name)
                if callable(val):
                    is_callable = True
                results.append(val)
            except:
                results.append(None)
        if is_callable:
            self.map_list = results
            return self.map
        return results

    def map(self, *args):
        results = []
        for fn in self.map_list:
            results.append(fn(*args))
        return results

class Server(SDBObject):

    ec2 = boto.connect_ec2()

    @classmethod
    def Inventory(cls):
        """
        Returns a list of Server instances, one for each Server object
        persisted in the db
        """
        l = ServerSet()
        rs = cls.list()
        for server in rs:
            l.append(server)
        return l

    @classmethod
    def Register(cls, name, instance_id, description=''):
        s = cls()
        s.name = name
        s.instance_id = instance_id
        s.description = description
        s.save()
        return s

    def __init__(self, id=None, name=None):
        SDBObject.__init__(self, id)
        self.name = name
        self.reservation = None
        self._instance = None
        self._ssh_client = None
        self._pkey = None
        self._config = None

    name = StringProperty()
    instance_id = StringProperty()
    description = StringProperty()

    def setReadOnly(self, value):
        raise AttributeError

    def getInstance(self):
        if not self._instance:
            if self.instance_id:
                rs = self.ec2.get_all_instances([self.instance_id])
                if len(rs) > 0:
                    self.reservation = rs[0]
                    self._instance = self.reservation.instances[0]
        return self._instance

    instance = property(getInstance, setReadOnly, None, 'The Instance for the server')
    
    def getAMI(self):
        if self.instance:
            return self.instance.image_id

    ami = property(getAMI, setReadOnly, None, 'The AMI for the server')
    
    def getStatus(self):
        if self.instance:
            self.instance.update()
            return self.instance.state

    status = property(getStatus, setReadOnly, None,
                      'The status of the server')
    
    def getHostname(self):
        if self.instance:
            return self.instance.public_dns_name

    hostname = property(getHostname, setReadOnly, None,
                        'The public DNS name of the server')

    def getConsoleOutput(self):
        if self.instance:
            return self.instance.get_console_output()

    console_output = property(getConsoleOutput, setReadOnly, None,
                              'Retrieve the console output for server')

    def getGroups(self):
        if self.reservation:
            return self.reservation.groups
        else:
            return None

    groups = property(getGroups, setReadOnly, None,
                      'The Security Groups controlling access to this server')

    def getConfig(self):
        if not self._config:
            remote_file = MetadataConfigPath
            local_file = '%s.ini' % self.instance.id
            self.get_file(remote_file, local_file)
            self._config = Config(local_file)
        return self._config

    def setConfig(self, config):
        local_file = '%s.ini' % self.instance.id
        fp = open(local_file)
        config.write(fp)
        fp.close()
        self.put_file(local_file, MetadataConfigPath)
        self._config = config

    config = property(getConfig, setConfig, None,
                      'The instance data for this server')

    def unregister(self):
        boto.mashups.persistance.delete(self.name)

    def stop(self):
        self.instance.stop()

    def reboot(self):
        self.instance.reboot()

    def get_ssh_client(self, key_file=None, host_key_file='~/.ssh/known_hosts',
                       uname='root'):
        import paramiko
        if not self.instance:
            print 'No instance yet!'
            return
        if not self._ssh_client:
            if not key_file:
                iobject = IObject()
                key_file = iobject.get_filename('Path to OpenSSH Key file')
            self._pkey = paramiko.RSAKey.from_private_key_file(key_file)
            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.load_system_host_keys()
            self._ssh_client.load_host_keys(os.path.expanduser(host_key_file))
            self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._ssh_client.connect(self.instance.public_dns_name,
                                     username=uname, pkey=self._pkey)
        return self._ssh_client

    def get_file(self, remotepath, localpath):
        ssh_client = self.get_ssh_client()
        sftp_client = ssh_client.open_sftp()
        sftp_client.get(remotepath, localpath)

    def put_file(self, localpath, remotepath):
        ssh_client = self.get_ssh_client()
        sftp_client = ssh_client.open_sftp()
        sftp_client.put(localpath, remotepath)

    def listdir(self, remotepath):
        ssh_client = self.get_ssh_client()
        sftp_client = ssh_client.open_sftp()
        return sftp_client.listdir(remotepath)

    def shell(self):
        ssh_client = self.get_ssh_client()
        channel = ssh_client.invoke_shell()
        interactive_shell(channel)

    def bundle_image(self, prefix, key_file, cert_file, size):
        print 'bundling image...'
        print '\tcopying cert and pk over to /mnt directory on server'
        ssh_client = self.get_ssh_client()
        sftp_client = ssh_client.open_sftp()
        path, name = os.path.split(key_file)
        remote_key_file = '/mnt/%s' % name
        self.put_file(key_file, remote_key_file)
        path, name = os.path.split(cert_file)
        remote_cert_file = '/mnt/%s' % name
        self.put_file(cert_file, remote_cert_file)
        print '\tdeleting %s' % MetadataConfigPath
        # delete the metadata.ini file if it exists
        try:
            sftp_client.remove(MetadataConfigPath)
        except:
            pass
        command = 'ec2-bundle-vol '
        command += '-c %s -k %s ' % (remote_cert_file, remote_key_file)
        command += '-u %s ' % self.reservation.owner_id
        command += '-p %s ' % prefix
        command += '-s %d ' % size
        command += '-d /mnt '
        if self.instance.instance_type == 'm1.small':
            command += '-r i386'
        else:
            command += '-r x86_64'
        print '\t%s' % command
        t = ssh_client.exec_command(command)
        response = t[1].read()
        print '\t%s' % response
        print '\t%s' % t[2].read()
        print '...complete!'

    def upload_bundle(self, bucket, prefix):
        print 'uploading bundle...'
        command = 'ec2-upload-bundle '
        command += '-m /mnt/%s.manifest.xml ' % prefix
        command += '-b %s ' % bucket
        command += '-a %s ' % self.ec2.aws_access_key_id
        command += '-s %s ' % self.ec2.aws_secret_access_key
        print '\t%s' % command
        ssh_client = self.get_ssh_client()
        t = ssh_client.exec_command(command)
        response = t[1].read()
        print '\t%s' % response
        print '\t%s' % t[2].read()
        print '...complete!'

    def create_image(self, bucket=None, prefix=None, key_file=None, cert_file=None, size=None):
        iobject = IObject()
        if not bucket:
            bucket = iobject.get_string('Name of S3 bucket')
        if not prefix:
            prefix = iobject.get_string('Prefix for AMI file')
        if not key_file:
            key_file = iobject.get_filename('Path to RSA private key file')
        if not cert_file:
            cert_file = iobject.get_filename('Path to RSA public cert file')
        if not size:
            size = iobject.get_int('Size (in MB) of bundled image')
        self.bundle_image(prefix, key_file, cert_file, size)
        self.upload_bundle(bucket, prefix)
        print 'registering image...'
        self.image_id = self.ec2.register_image('%s/%s.manifest.xml' % (bucket, prefix))
        return self.image_id

    def install_package(self, package_name):
        print 'installing %s...' % package_name
        command = 'yum -y install %s' % package_name
        print '\t%s' % command
        ssh_client = self.get_ssh_client()
        t = ssh_client.exec_command(command)
        response = t[1].read()
        print '\t%s' % response
        print '\t%s' % t[2].read()
        print '...complete!'

    
