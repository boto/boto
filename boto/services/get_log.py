#!/usr/bin/env python
import getopt, sys, imp
import boto

def usage():
    print 'SYNOPSIS'
    print '\tget_log.py -l log_queue_name -o log_file_name'
    sys.exit()

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hl:o::',
                                   ['logqueue', 'logfilename'])
    except:
        usage()
    log_queue_name = None
    log_file_name = None
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        if o in ('-l', '--logqueue'):
            log_queue_name = a
        if o in ('-o', '--logfilename'):
            log_file_name = a
    c = boto.connect_sqs()
    q = c.get_queue(log_queue_name)
    q.dump(log_file_name)

if __name__ == "__main__":
    main()

