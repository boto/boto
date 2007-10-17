#!/usr/bin/env python
import getopt, sys, os, time, mimetypes
from boto.services.service import Service

def submit_cb(bytes_so_far, total_bytes):
    print '%d bytes transferred / %d bytes total' % (bytes_so_far, total_bytes)

class FileSubmitter:

    def __init__(self, bucket_name, queue_name, cb=None, num_cb=0,
                 gen_key=False):
        self.bucket_name = bucket_name
        self.queue_name = queue_name
        preserve = not gen_key
        self.service = Service(input_queue_name=queue_name,
                               read_userdata=False, preserve_file_name=preserve)
        self.cb = cb
        self.num_cb = num_cb

    def submit_path(self, path, tags=None, batch=None, ignore_dirs=[]):
        total = 0
        metadata = {}
        if tags:
            metadata['Tags'] = tags
        if not batch:
            l = []
            for t in time.gmtime():
                l.append(str(t))
            metadata['Batch'] = '_'.join(l)
        else:
            metadata['Batch'] = batch
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for ignore in ignore_dirs:
                    if ignore in dirs:
                        dirs.remove(ignore)
                for file in files:
                    fullpath = os.path.join(root, file)
                    self.service.submit_file(fullpath, self.bucket_name,
                                             metadata, self.cb, self.num_cb)
                    total += 1
        elif os.path.isfile(path):
            self.service.submit_file(path, self.bucket_name, metadata,
                                     self.cb, self.num_cb)
            total += 1
        else:
            print 'problem with %s' % path
        print '%d files successfully submitted.' % total

def usage():
    print 'submit_files.py  [-b bucketname] [-g] [-p] [-q queuename] path [tags]'
  
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
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        if o in ('-b', '--bucket'):
            bucket_name = a
        if o in ('-g', '--gen_key'):
            gen_key = True
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
    s = FileSubmitter(bucket_name, queue_name, cb=cb, num_cb=num_cb,
                      gen_key=gen_key)
    s.submit_path(path, tags, ignore_dirs=['.svn'])
    return 1

if __name__ == "__main__":
    main()
