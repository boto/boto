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
import getopt, sys
from boto.connection import SQSConnection
from boto.exception import SQSError

def usage():
    print 'cq.py [-c] [-q queue_name] [-o output_file]'
  
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hcq:o:',
                                   ['help', 'clear', 'queue', 'output'])
    except:
        usage()
        sys.exit(2)
    queue_name = ''
    output_file = ''
    clear = False
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        if o in ('-q', '--queue'):
            queue_name = a
        if o in ('-o', '--output'):
            output_file = a
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
        elif output_file:
            q.dump(output_file)
        else:
            print q.id, q.count()

if __name__ == "__main__":
    main()
        
