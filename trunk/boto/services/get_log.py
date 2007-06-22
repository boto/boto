#!/usr/bin/env python
import getopt, sys, imp
import boto
from boto.sqs.message import MHMessage

def usage():
    print 'SYNOPSIS'
    print '\tget_log.py -l log_queue_name -o log_file_name'
    sys.exit()

def compare_timestamps(x, y):
    return cmp(x['Timestamp'], y['Timestamp'])

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
    q.set_message_class(MHMessage)
    msgs = []
    msg = q.read()
    while msg:
        msgs.append(msg)
        q.delete_message(msg)
        msg = q.read()
    msgs.sort(compare_timestamps)
    fp = open(log_file_name, 'w')
    for msg in msgs:
        fp.write(msg.get_body())
        fp.write('\n-----------------------\n')
    fp.close()

if __name__ == "__main__":
    main()

