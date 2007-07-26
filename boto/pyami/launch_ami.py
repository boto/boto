#!/usr/bin/env python
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
#
import getopt, sys, imp
import boto
from boto.utils import get_instance_userdata

def usage():
    print 'SYNOPSIS'
    print '\tlaunch_ami.py -m module -c class_name -a ami_id -b bucket_name [-k key_name]  [-n num_instances]  [-w working_dir]'
    sys.exit()

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'a:b:c:hk:m:rw:',
                                   ['ami', 'bucket', 'class', 'help',
                                    'keypair', 'module', 'numinstances',
                                    'reload', 'working_dir'])
    except:
        usage()
    params = {'module_name' : None,
              'class_name' : None,
              'bucket_name' : None,
              'keypair' : None,
              'ami' : None,
              'working_dir' : None}
    reload = None
    ami = None
    for o, a in opts:
        if o in ('-a', '--ami'):
            params['ami'] = a
        if o in ('-b', '--bucket'):
            params['bucket_name'] = a
        if o in ('-c', '--class'):
            params['class_name'] = a
        if o in ('-h', '--help'):
            usage()
        if o in ('-k', '--keypair'):
            params['keypair'] = a
        if o in ('-m', '--module'):
            params['module_name'] = a
        if o in ('-n', '--num_instances'):
            params['num_instances'] = int(a)
        if o in ('-r', '--reload'):
            reload = True
        if o in ('-w', '--working_dir'):
            params['working_dir'] = a

    # check required fields
    required = ['ami', 'bucket_name', 'class_name', 'module_name']
    for pname in required:
        if pname not in params.keys():
            print '%s is required' % pname
            usage()
    # first copy the desired module file to S3 bucket
    if reload:
        print 'Reloading module %s to S3' % params['module_name']
    else:
        print 'Copying module %s to S3' % params['module_name']
    l = imp.find_module(params['module_name'])
    c = boto.connect_s3()
    bucket = c.get_bucket(params['bucket_name'])
    key = bucket.new_key(params['module_name']+'.py')
    key.set_contents_from_file(l[0])
    params['script_md5'] = key.md5
    # we have everything we need, now build userdata string
    l = []
    for k, v in params.items():
        if v:
            l.append('%s=%s' % (k, v))
    c = boto.connect_ec2()
    l.append('aws_access_key_id=%s' % c.aws_access_key_id)
    l.append('aws_secret_access_key=%s' % c.aws_secret_access_key)
    s = '|'.join(l)
    if not reload:
        rs = c.get_all_images([params['ami']])
        img = rs[0]
        r = img.run(user_data=s, key_name=params['keypair'],
                    max_count=params.get('num_instances', 1))
        print 'AMI: %s - %s (Started)' % (params['ami'], img.location)
        print 'Reservation %s contains the following instances:' % r.id
        for i in r.instances:
            print '\t%s' % i.id

if __name__ == "__main__":
    main()

