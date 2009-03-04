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

"""
High-level abstraction of an EC2 server
"""
from __future__ import with_statement
import boto.ec2
from boto.mashups.iobject import IObject
from boto.pyami.config import BotoConfigPath
from boto.sdb.db.model import Model, ModelMeta
from boto.sdb.db.property import *
from boto.manage import propget
import cmdshell
import os, time
import StringIO
from contextlib import closing

class ServerMeta(ModelMeta):

    def __init__(cls, name, bases, dict):
        super(ServerMeta, cls).__init__(name, bases, dict)
        installers = []
        for base in bases:
            l = []
            for key in base.__dict__:
                val = base.__dict__[key]
                if isinstance(val, Installer):
                    print 'Found %s_%s in %s' % (val.name, val.seq_no, base.__name__)
                    l.append(val)
            l.sort()
            installers.extend(l)
        for i in installers:
            print i.name
        
class Installer(object):

    def __init__ (self, seq_no, fn):
        self.instance_id = boto.config.get('Instance', 'instance-id', None)
        self.name = fn.__name__
        self.seq_no = seq_no
        self.fn = fn

    def __call__ (self, *args, **kws):
        if self.instance_id == self.obj.instance_id:
            ret_val = self.fn(self.obj, *args, **kws)
            return ret_val
        else:
            raise NotImplementedError, '%s is only available on the EC2 instance' % self.fn.__name__

    def __cmp__(self, other):
        return cmp(self.seq_no, other.seq_no)

    def __get__(descr, inst, instCls=None):
        descr.obj = inst
        return descr

def installer(seq_no):
    ret_val = lambda func: Installer(seq_no, func)
    return ret_val

InstanceTypes = ['m1.small', 'm1.large', 'm1.xlarge', 'c1.medium', 'c1.xlarge']

class Bundler(object):

    def __init__(self, server):
        self.server = server
        self.ssh_client = SSHClient(server)

    def bundle_image(self, prefix, key_file, cert_file, size, ssh_key):
        print 'bundling image...'
        print '\tcopying cert and pk over to /mnt directory on server'
        sftp_client = self.ssh_client.open_sftp()
        path, name = os.path.split(key_file)
        remote_key_file = '/mnt/%s' % name
        self.put_file(key_file, remote_key_file)
        path, name = os.path.split(cert_file)
        remote_cert_file = '/mnt/%s' % name
        self.put_file(cert_file, remote_cert_file)
        print '\tdeleting %s' % BotoConfigPath
        # delete the metadata.ini file if it exists
        try:
            sftp_client.remove(BotoConfigPath)
        except:
            pass
        command = 'ec2-bundle-vol '
        command += '-c %s -k %s ' % (remote_cert_file, remote_key_file)
        command += '-u %s ' % self._reservation.owner_id
        command += '-p %s ' % prefix
        command += '-s %d ' % size
        command += '-d /mnt '
        if self.instance.instance_type == 'm1.small' or self.instance_type == 'c1.medium':
            command += '-r i386'
        else:
            command += '-r x86_64'
        print '\t%s' % command
        t = ssh_client.exec_command(command)
        response = t[1].read()
        print '\t%s' % response
        print '\t%s' % t[2].read()
        print '...complete!'

    def upload_bundle(self, bucket, prefix, ssh_key):
        print 'uploading bundle...'
        command = 'ec2-upload-bundle '
        command += '-m /mnt/%s.manifest.xml ' % prefix
        command += '-b %s ' % bucket
        command += '-a %s ' % self.server.ec2.aws_access_key_id
        command += '-s %s ' % self.server.ec2.aws_secret_access_key
        print '\t%s' % command
        t = self.ssh_client.exec_command(command)
        response = t[1].read()
        print '\t%s' % response
        print '\t%s' % t[2].read()
        print '...complete!'

    def bundle(self, bucket=None, prefix=None, key_file=None, cert_file=None, size=None, ssh_key=None):
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
        if not ssh_key:
            ssh_key = iobject.get_filename('Path to SSH Private Key')
        self.bundle_image(prefix, key_file, cert_file, size, ssh_key)
        self.upload_bundle(bucket, prefix, ssh_key)
        print 'registering image...'
        self.image_id = self.server.ec2.register_image('%s/%s.manifest.xml' % (bucket, prefix))
        return self.image_id

class CommandLineGetter(object):

    def get_ami_list(self):
        my_amis = []
        for ami in self.ec2.get_all_images():
            # hack alert, need a better way to do this!
            if ami.location.find('pyami') >= 0:
                my_amis.append((ami.location, ami))
        return my_amis
    
    def get_region(self, params):
        if not params.get('region', None):
            prop = self.cls.find_property('region_name')
            params['region'] = propget.get(prop, choices=boto.ec2.regions)

    def get_name(self, params):
        if not params.get('name', None):
            prop = self.cls.find_property('name')
            params['name'] = propget.get(prop)

    def get_description(self, params):
        if not params.get('description', None):
            prop = self.cls.find_property('description')
            params['description'] = propget.get(prop)

    def get_instance_type(self, params):
        if not params.get('instance_type', None):
            prop = StringProperty(name='instance_type', verbose_name='Instance Type',
                                  choices=InstanceTypes)
            params['instance_type'] = propget.get(prop)

    def get_quantity(self, params):
        if not params.get('quantity', None):
            prop = IntegerProperty(name='quantity', verbose_name='Number of Instances')
            params['quantity'] = propget.get(prop)

    def get_zone(self, params):
        if not params.get('zone', None):
            prop = StringProperty(name='zone', verbose_name='EC2 Availability Zone',
                                  choices=self.ec2.get_all_zones)
            params['zone'] = propget.get(prop)
            
    def get_ami_id(self, params):
        if not params.get('ami', None):
            prop = StringProperty(name='ami', verbose_name='AMI',
                                  choices=self.get_ami_list)
            params['ami'] = propget.get(prop)

    def get_group(self, params):
        if not params.get('groups', None):
            prop = StringProperty(name='groups', verbose_name='EC2 Security Group',
                                  choices=self.ec2.get_all_security_groups)
            params['groups'] = [propget.get(prop)]

    def get_key(self, params):
        if not params.get('keypair', None):
            prop = StringProperty(name='keypair', verbose_name='EC2 KeyPair',
                                  choices=self.ec2.get_all_key_pairs)
            params['keypair'] = propget.get(prop)

    def get(self, cls, params):
        self.cls = cls
        self.get_region(params)
        self.ec2 = params['region'].connect()
        self.get_name(params)
        self.get_description(params)
        self.get_instance_type(params)
        self.get_zone(params)
        self.get_quantity(params)
        self.get_ami_id(params)
        self.get_group(params)
        self.get_key(params)

class Server(Model):

    __metaclass__ = ServerMeta
    
    #
    # The properties of this object consists of real properties for data that
    # is not already stored in EC2 somewhere (e.g. name, description) plus
    # calculated properties for all of the properties that are already in
    # EC2 (e.g. hostname, security groups, etc.)
    #
    name = StringProperty(unique=True, verbose_name="Name")
    description = StringProperty(verbose_name="Description")
    region_name = StringProperty(verbose_name="EC2 Region Name")
    instance_id = StringProperty(verbose_name="EC2 Instance ID")
    elastic_ip = StringProperty(verbose_name="EC2 Elastic IP Address")
    production = BooleanProperty(verbose_name="Is This Server Production", default=False)
    ami_id = CalculatedProperty(verbose_name="AMI ID", calculated_type=str, use_method=True)
    zone = CalculatedProperty(verbose_name="Availability Zone Name", calculated_type=str, use_method=True)
    hostname = CalculatedProperty(verbose_name="Public DNS Name", calculated_type=str, use_method=True)
    private_hostname = CalculatedProperty(verbose_name="Private DNS Name", calculated_type=str, use_method=True)
    groups = CalculatedProperty(verbose_name="Security Group Name", calculated_type=list, use_method=True)
    key_name = CalculatedProperty(verbose_name="Key Name", calculated_type=str, use_method=True)
    instance_type = CalculatedProperty(verbose_name="Instance Type", calculated_type=str, use_method=True)
    status = CalculatedProperty(verbose_name="Current Status", calculated_type=str, use_method=True)
    launch_time = CalculatedProperty(verbose_name="Server Launch Time", calculated_type=str, use_method=True)
    console_output = CalculatedProperty(verbose_name="Console Output", calculated_type=str, use_method=True)

    packages = []
    plugins = []

    @classmethod
    def make_config(cls, aws_access_key_id, aws_secret_access_key):
        cfg = StringIO.StringIO()
        cfg.write('[Credentials]\n')
        cfg.write('aws_access_key_id = %s\n' % aws_access_key_id)
        cfg.write('aws_secret_access_key = %s\n\n' % aws_secret_access_key)
        cfg.write('[DB_Server]\n')
        cfg.write('db_type = SimpleDB\n')
        cfg.write('db_name = %s\n' % cls._manager.domain.name)
        return cfg.getvalue()

    @classmethod
    def create(cls, **params):
        getter = CommandLineGetter()
        getter.get(cls, params)
        region = params.get('region')
        ec2 = region.connect()
        cfg = cls.make_config(ec2.aws_access_key_id, ec2.aws_secret_access_key)
        ami = params.get('ami')
        kp = params.get('keypair')
        groups = [g.name for g in params.get('groups')]
        zone = params.get('zone')
        reservation = ami.run(min_count=1,
                              max_count=params.get('quantity', 1),
                              key_name=kp.name,
                              security_groups=groups,
                              instance_type=params.get('instance_type'),
                              placement = zone.name,
                              user_data = cfg)
        l = []
        i = 0
        for instance in reservation.instances:
            s = cls()
            s.ec2 = ec2
            s.name = params.get('name') + '' if i==0 else str(i)
            s.description = params.get('description')
            s.region_name = region.name
            s.instance_id = instance.id
            s.put()
            l.append(s)
            i += 1
        return l
    
    @classmethod
    def create_from_instance_id(cls, instance_id, name, description=''):
        regions = boto.ec2.regions()
        for region in regions:
            ec2 = region.connect()
            try:
                rs = ec2.get_all_instances([instance_id])
            except:
                rs = []
            if len(rs) == 1:
                s = cls()
                s.ec2 = ec2
                s.name = name
                s.description = description
                s.region_name = region.name
                s.instance_id = instance_id
                s._reservation = rs[0]
                for instance in s._reservation.instances:
                    if instance.id == instance_id:
                        s._instance = instance
                s.put()
                return s
        return None

    def create_from_current_instances(cls):
        servers = []
        regions = boto.ec2.regions()
        for region in regions:
            ec2 = region.connect()
            rs = ec2.get_all_instances()
            for reservation in rs:
                for instance in reservation.instances:
                    try:
                        Server.find(instance_id=instance.id).next()
                        boto.log.info('Server for %s already exists' % instance.id)
                    except StopIteration:
                        s = cls()
                        s.ec2 = ec2
                        s.name = instance.id
                        s.region_name = region.name
                        s.instance_id = instance.id
                        s._reservation = reservation
                        s.put()
                        servers.append(s)
        return servers
    
    def __init__(self, id=None, **kw):
        Model.__init__(self, id, **kw)
        self.ssh_key_file = None
        self.ec2 = None
        self._cmdshell = None
        self._reservation = None
        self._instance = None
        self._setup_ec2()

    def _setup_ec2(self):
        if self.ec2 and self._instance and self._reservation:
            return
        if self.id:
            if self.region_name:
                for region in boto.ec2.regions():
                    if region.name == self.region_name:
                        self.ec2 = region.connect()
                        if self.instance_id and not self._instance:
                            rs = self.ec2.get_all_instances([self.instance_id])
                            if len(rs) >= 1:
                                for instance in rs[0].instances:
                                    if instance.id == self.instance_id:
                                        self._reservation = rs[0]
                                        self._instance = instance
                            
    def _status(self):
        status = ''
        if self._instance:
            self._instance.update()
            status = self._instance.state
        return status

    def _hostname(self):
        hostname = ''
        if self._instance:
            hostname = self._instance.public_dns_name
        return hostname

    def _private_hostname(self):
        hostname = ''
        if self._instance:
            hostname = self._instance.private_dns_name
        return hostname

    def _launch_time(self):
        lt = ''
        if self._instance:
            lt = self._instance.launch_time
        return lt

    def _console_output(self):
        co = ''
        if self._instance:
            co = self._instance.get_console_output()
        return co

    def _groups(self):
        gn = []
        if self._reservation:
            gn = self._reservation.groups
        return gn

    def _zone(self):
        zone = None
        if self._instance:
            zone = self._instance.placement
        return zone

    def _key_name(self):
        kn = None
        if self._instance:
            kn = self._instance.key_name
        return kn

    def put(self):
        Model.put(self)
        self._setup_ec2()

    def delete(self):
        if self.production:
            raise ValueError, "Can't delete a production server"
        #self.stop()
        Model.delete(self)

    def stop(self):
        if self.production:
            raise ValueError, "Can't delete a production server"
        if self._instance:
            self._instance.stop()

    def reboot(self):
        if self._instance:
            self._instance.reboot()

    def wait(self):
        while self.status != 'running':
            time.sleep(5)

    def get_ssh_key_file(self):
        if not self.ssh_key_file:
            ssh_dir = os.path.expanduser('~/.ssh')
            if os.path.isdir(ssh_dir):
                ssh_file = os.path.join(ssh_dir, '%s.pem' % self.key_name)
                if os.path.isfile(ssh_file):
                    self.ssh_key_file = ssh_file
            if not self.ssh_key_file:
                iobject = IObject()
                self.ssh_key_file = iobject.get_filename('Path to OpenSSH Key file')
        return self.ssh_key_file

    def get_cmdshell(self):
        if not self._cmdshell:
            self.get_ssh_key_file()
            self._cmdshell = cmdshell.start(self)
        return self._cmdshell

    def reset_cmdshell(self):
        self._cmdshell = None

    def run(self, command):
        with closing(self.get_cmdshell()) as cmd:
            status = cmd.run(command)
        return status

    def get_bundler(self, key_file=None):
        self.get_ssh_key_file()
        return SSHClient(self)

    def install(self, pkg):
        return self.run('apt-get -y install %s' % pkg)

class MySQLServer(Server):

    root_password = StringProperty(verbose_name="Root Password")

    def test(self):
        print 'MySQLServer.test'

    @installer('001')
    def test_mysql(self):
        print 'MySQLServer.test_mysql'

    
