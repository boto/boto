#!/usr/bin/env python
import getopt, sys, imp
import boto
from boto.utils import get_instance_userdata

def usage():
    print 'start_service.py -m module -c class_name [-r] [-a ami_id] [-w working_dir] [-i input_queue_name] [-o output_queue_name]'
    sys.exit()

def get_userdata(params):
    module_name = None
    class_name = None
    d = get_instance_userdata(sep='|')
    params.update(d)

def find_class(params):
    modules = params['module_name'].split('.')
    path = None
    for module_name in modules:
        fp, pathname, description = imp.find_module(module_name, path)
        module = imp.load_module(module_name, fp, pathname, description)
        if hasattr(module, '__path__'):
            path = module.__path__
    return getattr(module, params['class_name'])
  
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'a:c:hi:k:m:o:rw:',
                                   ['ami', 'class', 'help', 'inputqueue',
                                    'keypair', 'module', 'outputqueue',
                                    'remote', 'working_dir'])
    except:
        usage()
    params = {'module_name' : None,
              'class_name' : None,
              'input_queue_name' : None,
              'output_queue_name' : None,
              'working_dir' : None,
              'keypair' : None,
              'ami' : None}
    remote = None
    ami = None
    for o, a in opts:
        if o in ('-a', '--ami'):
            params['ami'] = a
        if o in ('-c', '--class'):
            params['class_name'] = a
        if o in ('-h', '--help'):
            usage()
        if o in ('-i', '--inputqueue'):
            params['input_queue_name'] = a
        if o in ('-k', '--keypair'):
            params['keypair'] = a
        if o in ('-m', '--module'):
            params['module_name'] = a
        if o in ('-o', '--outputqueue'):
            params['output_queue_name'] = a
        if o in ('-r', '--remote'):
            remote = True
        if o in ('-w', '--working_dir'):
            params['working_dir'] = a
    if remote:
        # check required fields
        required = ['module_name', 'class_name', 'input_queue_name',
                    'output_queue_name', 'ami']
        for pname in required:
            if pname not in params.keys():
                print '%s is required' % pname
                usage()
        # we have everything we need, now build userdata string
        l = []
        for k, v in params.items():
            if v:
                l.append('%s=%s' % (k, v))
        c = boto.connect_ec2()
        c.set_debug(1)
        l.append('aws_access_key_id=%s' % c.aws_access_key_id)
        l.append('aws_secret_access_key=%s' % c.aws_secret_access_key)
        s = '|'.join(l)
        print s
        if params['ami']:
            rs = c.get_all_images([params['ami']])
            img = rs[0]
            r = img.run(user_data=s, key_name=params['keypair'])
            print r.id
        else:
            print '-a option is required'
            usage()
    else:
        get_userdata(params)
        cls = find_class(params)
        s = cls(working_dir=params['working_dir'],
                input_queue_name=params['input_queue_name'],
                output_queue_name=params['output_queue_name'])
        s.run()

if __name__ == "__main__":
    main()

