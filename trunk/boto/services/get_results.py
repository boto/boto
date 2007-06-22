#!/usr/bin/env python
import getopt, sys, os, time
from datetime import datetime, timedelta
from boto.services.service import Service

class ResultProcessor:

    TimeFormat = '%a, %d %b %Y %H:%M:%S %Z'
    LogFileName = 'log.csv'

    def __init__(self, queue_name):
        self.queue_name = queue_name
        self.service = Service(output_queue_name=queue_name,
                               read_userdata=False)
        self.log_fp = None
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

    def log_message(self, msg, path):
        keys = msg.keys()
        keys.sort()
        if not self.log_fp:
            self.log_fp = open(os.path.join(path, self.LogFileName), 'w')
            line = ','.join(keys)
            self.log_fp.write(line+'\n')
        values = []
        for key in keys:
            value = msg[key]
            if value.find(',') > 0:
                value = '"%s"' % value
            values.append(value)
        line = ','.join(values)
        self.log_fp.write(line+'\n')

    def get_results(self, path, get_file=True):
        total_files = 0
        total_time = 0
        if not os.path.isdir(path):
            os.mkdir(path)
        m = self.service.get_result(path, original_name=True, get_file=get_file)
        while m:
            total_files += 1
            self.log_message(m, path)
            self.calculate_stats(m)
            m = self.service.get_result(path, original_name=True,
                                        get_file=get_file)
        if self.log_fp:
            self.log_fp.close()
        print '%d results successfully retrieved.' % total_files
        if total_files > 0:
            self.avg_time = float(self.total_time)/total_files
            print 'Minimum Processing Time: %d' % self.min_time.seconds
            print 'Maximum Processing Time: %d' % self.max_time.seconds
            print 'Average Processing Time: %f' % self.avg_time
            self.elapsed_time = self.latest_time-self.earliest_time
            print 'Elapsed Time: %d' % self.elapsed_time.seconds
            tput = 1.0 / ((self.elapsed_time.seconds/60.0) / total_files)
            print 'Throughput: %f transactions / minute' % tput
        
def usage():
    print 'get_results.py  [-q queuename] [-n] path'
    print '\tif -n is specified, the result files will not be retrieved'
    print '\tfrom S3, otherwise the result files will be downloaded to'
    print '\tthe specified path'
  
def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hnq:',
                                   ['help', 'no_retrieve', 'queue'])
    except:
        usage()
        sys.exit(2)
    queue_name = None
    notify = False
    get_file = True
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        if o in ('-n', '--no-retrieve'):
            get_file = False
        if o in ('-q', '--queue'):
            queue_name = a
    if len(args) == 0:
        usage()
        sys.exit()
    path = args[0]
    if len(args) > 1:
        tags = args[1]
    s = ResultProcessor(queue_name)
    s.get_results(path, get_file)
    return 1

if __name__ == "__main__":
    main()
