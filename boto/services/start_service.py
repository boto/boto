#!/usr/bin/env python
import getopt, sys, os, StringIO
import boto
from boto.pyami.config import Config

def usage():
    print 'SYNOPSIS'
    print '\tstart_service.py -a ami_id [-k key_name] [-n num_instances] config_file'
    sys.exit()

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'a:hk:n:',
                                   ['ami', 'help', 'keypair', 'numinstances'])
    except:
        usage()
    ami = None
    keypair = None
    num_instances = 1
    for o, a in opts:
        if o in ('-a', '--ami'):
            ami = a
        if o in ('-h', '--help'):
            usage()
        if o in ('-k', '--keypair'):
            keypair = a
        if o in ('-n', '--num_instances'):
            num_instances = int(a)
    # check required fields
    if not ami:
        print 'ami is required'
        usage()
    # check the config file path
    if len(args) != 1:
        print usage()
    path = args[0]
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        print '%s not found' % path
        usage()
    ec2 = boto.connect_ec2()
    config = Config(path=path)
    if not config.has_section('Credentials'):
        config.add_section('Credentials')
        config.set('Credentials', 'aws_access_key_id', ec2.aws_access_key_id)
        config.set('Credentials', 'aws_secret_access_key', ec2.aws_secret_access_key)
    s = StringIO.StringIO()
    config.write(s)
    print s.getvalue()
    rs = ec2.get_all_images([ami])
    img = rs[0]
    r = img.run(user_data=s.getvalue(), key_name=keypair,
                max_count=num_instances)
    print 'Server %s (Started)' % ami
    print 'Reservation %s contains the following instances:' % r.id
    for i in r.instances:
        print '\t%s' % i.id

if __name__ == "__main__":
    main()

