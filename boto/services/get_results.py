#!/usr/bin/env python
import getopt, sys, os, time
from datetime import datetime, timedelta
from boto.services.service import Service

class ResultProcessor:

    TimeFormat = '%a, %d %b %Y %H:%M:%S %Z'

    def __init__(self, queue_name):
        self.queue_name = queue_name
        self.service = Service(output_queue_name=queue_name,
                               read_userdata=False)
        self.num_files = 0
        self.total_time = 0
        self.min_time = timedelta.max
        self.max_time = timedelta.min
        self.earliest_time = datetime.max
        self.latest_time = datetime.min

    def calculate_stats(self, msg):
        start_time = datetime(*time.strptime(msg['Service-Read'],
                                             self.TimeFormat)[0:6])
        end_time = datetime(*time.strptime(msg['Service-Write'],
                                           self.TimeFormat)[0:6])
        elapsed_time = end_time - start_time
        if elapsed_time > self.max_time:
            self.max_time = elapsed_time
        if elapsed_time < self.min_time:
            self.min_time = elapsed_time
        self.total_time += elapsed_time.seconds
        if start_time < self.earliest_time:
            self.earliest_time = start_time
        if end_time > self.latest_time:
            self.latest_time = end_time

    def get_results(self, path):
        total_files = 0
        total_time = 0
        if not os.path.isdir(path):
            os.mkdir(path)
        fp = open(os.path.join(path, 'messages.txt'), 'w')
        m = self.service.get_result(path, original_name=True)
        while m:
            total_files += 1
            fp.write(m.get_body())
            fp.write('\n')
            self.calculate_stats(m)
            m = self.service.get_result(path, original_name=True)
        fp.close()
        print '%d results successfully retrieved.' % total_files
        self.avg_time = self.total_time/total_files
        print 'Minimum Processing Time: %f' % self.min_time
        print 'Maximum Processing Time: %f' % self.max_time
        print 'Average Processing Time: %f' % self.avg_time
        self.elapsed_time = self.latest_time-self.earliest_time
        print 'Elapsed Time: %f' % self.elapsed_time.seconds
        
def usage():
    print 'get_results.py  [-q queuename] path'
  
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hq:',
                                   ['help', 'queue'])
    except:
        usage()
        sys.exit(2)
    queue_name = None
    notify = False
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        if o in ('-q', '--queue'):
            queue_name = a
    if len(args) == 0:
        usage()
        sys.exit()
    path = args[0]
    if len(args) > 1:
        tags = args[1]
    s = ResultProcessor(queue_name)
    s.get_results(path)
    return 1

if __name__ == "__main__":
    main()
