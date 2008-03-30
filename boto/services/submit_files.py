#!/usr/bin/env python
import getopt, sys, mimetypes, os
from boto.services.submit import Submitter

usage_string = """
SYNOPSIS
    submit_files.py [-a access_key] [-s secret_key] -b bucket_name -q queue_name
                    [-c num_cb] [-i ignore_dirs] [-n] [-p prefix] path

    Where
        access_key - Your AWS Access Key ID.  If not supplied, boto will
                     use the value of the environment variable
                     AWS_ACCESS_KEY_ID
        secret_key - Your AWS Secret Access Key.  If not supplied, boto
                     will use the value of the environment variable
                     AWS_SECRET_ACCESS_KEY
        bucket_name - The name of the S3 bucket the file(s) should be
                      copied to.
        path - A path to a directory or file that represents the items
               to be uploaded.  If the path points to an individual file,
               that file will be uploaded to the specified bucket.  If the
               path points to a directory, s3_it will recursively traverse
               the directory and upload all files to the specified bucket.
        ignore_dirs - a comma-separated list of directory names that will
                      be ignored and not uploaded to S3.
        num_cb - The number of progress callbacks to display.  The default
                 is zero which means no callbacks.  If you supplied a value
                 of "-c 10" for example, the progress callback would be
                 called 10 times for each file transferred.
        prefix - A file path prefix that will be stripped from the full
                 path of the file when determining the key name in S3.
                 For example, if the full path of a file is:
                     /home/foo/bar/fie.baz
                 and the prefix is specified as "-p /home/foo/" the
                 resulting key name in S3 will be:
                     /bar/fie.baz
                 The prefix must end in a trailing separator and if it
                 does not then one will be added.

     If the -n option is provided, no files will be transferred to S3 but
     informational messages will be printed about what would happen.
"""
def usage():
    print usage_string
    sys.exit()
  
def submit_cb(bytes_so_far, total_bytes):
    print '%d bytes transferred / %d bytes total' % (bytes_so_far, total_bytes)

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'a:b:c::hi:np:q:s:v',
                                   ['access_key', 'bucket', 'callback', 'help', 'ignore',
                                    'no_op', 'prefix', 'queue', 'secret_key'])
    except:
        usage()
        sys.exit(2)
    ignore_dirs = []
    aws_access_key_id = None
    aws_secret_access_key = None
    bucket_name = None
    queue_name = None
    cb = None
    num_cb = 0
    no_op = False
    prefix = '/'
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        if o in ('-a', '--access_key'):
            aws_access_key_id = a
        if o in ('-b', '--bucket'):
            bucket_name = a
        if o in ('-c', '--callback'):
            num_cb = int(a)
            cb = submit_cb
        if o in ('-i', '--ignore'):
            ignore_dirs = a.split(',')
        if o in ('-n', '--no_op'):
            no_op = True
        if o in ('-p', '--prefix'):
            prefix = a
            if prefix[-1] != os.sep:
                prefix = prefix + os.sep
        if o in ('-q', '--queue'):
            queue_name = a
        if o in ('-s', '--secret_key'):
            aws_secret_access_key = a
    if len(args) != 1:
        print usage()
    path = args[0]
    # mimetypes doesn't know about flv files, let's clue it in
    mimetypes.add_type('video/x-flv', '.flv')
    s = Submitter(bucket_name, queue_name)
    s.submit_path(path, None, ignore_dirs, cb, num_cb, True, prefix)
    return 1

if __name__ == "__main__":
    main()
