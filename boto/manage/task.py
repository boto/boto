# Copyright (c) 2006-2009 Mitch Garnaat http://garnaat.org/
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

import boto
from boto.sdb.db.property import *
from boto.sdb.db.model import Model
import datetime, subprocess, StringIO, time

def check_hour(val):
    if val == '*':
        return
    if int(val) < 0 or int(val) > 23:
        raise ValueError
    
class Task(Model):

    """
    A scheduled, repeating task that can be executed by any participating servers.
    The scheduling is similar to cron jobs.  Each task has an hour attribute.
    The allowable values for hour are [0-23|*].

    To keep the operation reasonably efficient and not cause excessive polling,
    the minimum granularity of a Task is hourly.  Some examples:
    
         hour='*' - the task would be executed each hour
         hour='3' - the task would be executed at 3AM GMT each day.
         
    """
    name = StringProperty()
    hour = StringProperty(required=True, validator=check_hour, default='*')
    command = StringProperty(required=True)
    last_executed = DateTimeProperty()
    last_status = IntegerProperty()
    last_output = StringProperty()

    def check(self, msg):
        """
        Determine if the Task needs to run right now or not.  If it does, run it and if it
        doesn't, do nothing.
        """
        need_to_run = False
        # get current time in UTC
        now = datetime.datetime.utcnow()
        if self.hour == '*':
            # run the task hourly
            # if it's never been run before, run it now
            if not self.last_executed:
                need_to_run = True
            else:
                delta = now - self.last_executed
                if delta.seconds >= 60*60:
                    need_to_run = True
        else:
            hour = int(self.hour)
            next = datetime.datetime(now.year, now.month, now.day, hour)
            delta = now - next
            if delta.days >= 0:
                need_to_run = True
        if need_to_run:
            self.run()
            self.last_executed = now
            self.put()
            q = msg.queue
            msg.delete()
            self.schedule(q)

    def schedule(self, queue):
        msg = queue.new_message(self.id)
        queue.write(msg)
        
    def run(self):
        boto.log.info('running:%s' % self.command)
        log_fp = StringIO.StringIO()
        process = subprocess.Popen(self.command, shell=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while process.poll() == None:
            time.sleep(1)
            t = process.communicate()
            log_fp.write(t[0])
            log_fp.write(t[1])
        boto.log.info(log_fp.getvalue())
        boto.log.info('output: %s' % log_fp.getvalue())
        self.last_status = process.returncode
        self.last_log = log_fp.getvalue()[0:1023]

class TaskPoller:

    def __init__(self, queue_name):
        self.sqs = boto.connect_sqs()
        self.queue = self.sqs.lookup(queue_name)

    def poll(self, wait=60):
        while 1:
            m = self.queue.read(60*5)
            if m:
                task = Task.get_by_id(m.get_body())
                if task:
                    task.check(m)
            else:
                time.sleep(wait)

        

    

    
