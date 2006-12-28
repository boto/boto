#!/usr/bin/env python
import getopt, sys
from boto.connection import SQSConnection
from boto.exception import SQSError

def usage():
    print 'cq.py [-c] [-q queue_name]'
  
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hcq:',
                                   ['help', 'clear', 'queue'])
    except:
        usage()
        sys.exit(2)
    queue_name = ''
    clear = False
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        if o in ('-q', '--queue'):
            queue_name = a
        if o in ('-c', '--clear'):
            clear = True
    c = SQSConnection()
    if queue_name:
        try:
            rs = [c.create_queue(queue_name)]
        except SQSError, e:
            print 'An Error Occurred:'
            print '%s: %s' % (e.status, e.reason)
            print e.body
            sys.exit()
    else:
        try:
            rs = c.get_all_queues()
        except SQSError, e:
            print 'An Error Occurred:'
            print '%s: %s' % (e.status, e.reason)
            print e.body
            sys.exit()
    for q in rs:
        if clear:
            n = q.clear()
            print 'clearing %d messages from %s' % (n, q.id)
        else:
            print q.id, q.count()

if __name__ == "__main__":
    main()
        
