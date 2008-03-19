#!/usr/bin/env python
import getopt, sys, mimetypes
from boto.services.submit import Submitter

def submit_cb(bytes_so_far, total_bytes):
    print '%d bytes transferred / %d bytes total' % (bytes_so_far, total_bytes)

def usage():
    print 'submit_files.py [-b bucketname] [-g] [-p] [-q queuename] path [tags]'
  
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hb:gp:q:',
                                   ['help', 'bucket', 'gen_key',
                                    'progress', 'queue'])
    except:
        usage()
        sys.exit(2)
    bucket_name = None
    queue_name = None
    cb = None
    num_cb = 0
    tags = ''
    notify = False
    gen_key = False
    ignore_dirs = ['.svn']
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        if o in ('-b', '--bucket'):
            bucket_name = a
        if o in ('-g', '--gen_key'):
            boto.config.setbool('Service', 'preserve_filename', False)
        if o in ('-p', '--progress'):
            num_cb = int(a)
            cb = submit_cb
        if o in ('-q', '--queue'):
            queue_name = a
    if len(args) == 0:
        usage()
        sys.exit()
    path = args[0]
    if len(args) > 1:
        tags = args[1]
    # mimetypes doesn't know about flv files, let's clue it in
    mimetypes.add_type('video/x-flv', '.flv')
    s = Submitter(bucket_name, queue_name)
    s.submit_path(path, tags, ignore_dirs, cb, num_cb, True)
    return 1

if __name__ == "__main__":
    main()
