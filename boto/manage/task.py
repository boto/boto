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

    def check(self, msg, vtimeout):
        """
        Determine if the Task needs to run right now or not.  If it does, run it and if it
        doesn't, do nothing.
        """
        need_to_run = False
        # get current time in UTC
        now = datetime.datetime.utcnow()
        boto.log.info('checking Task[%s]' % self.name)
        boto.log.info('now=%s' % now)
        boto.log.info('last_executed=%s' % self.last_executed)
        if self.hour == '*':
            # An hourly task.
            # If it's never been run before, run it now.
            if not self.last_executed:
                need_to_run = True
            else:
                delta = now - self.last_executed
                print 'delta=', delta
                if delta.seconds >= 60*60:
                    need_to_run = True
                else:
                    seconds_to_add = 60*60 - delta.seconds
        else:
            hour = int(self.hour)
            if hour == now.hour:
                if self.last_executed:
                    delta = now - self.last_executed
                    boto.log.info('delta=%s' % delta)
                    if delta.days >= 1:
                        need_to_run = True
                else:
                    need_to_run = True
        if need_to_run:
            self.run(msg, vtimeout)
            self.last_executed = now
            self.put()
            q = msg.queue
            msg.delete()
            self.schedule(q)
        elif self.hour == '*':
            boto.log.info('seconds_to_add: %s' % seconds_to_add-vtimeout)
            msg.change_visibility(seconds_to_add)
            
    def schedule(self, queue):
        msg = queue.new_message(self.id)
        queue.write(msg)
        
    def run(self, msg, vtimeout=60):
        boto.log.info('Task[%s] - running:%s' % (self.name, self.command))
        log_fp = StringIO.StringIO()
        process = subprocess.Popen(self.command, shell=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        nsecs = 5
        while process.poll() == None:
            boto.log.info('nsecs=%s, vtimeout=%s' % (nsecs, vtimeout))
            if nsecs >= vtimeout:
                boto.log.info('Task[%s] - extending timeout by %d seconds' % (self.name, vtimeout))
                msg.change_visibility(vtimeout)
                nsecs = 5
            time.sleep(5)
            nsecs += 5
        t = process.communicate()
        log_fp.write(t[0])
        log_fp.write(t[1])
        boto.log.info('Task[%s] - output: %s' % (self.name, log_fp.getvalue()))
        self.last_status = process.returncode
        self.last_output = log_fp.getvalue()[0:1023]

class TaskPoller:

    def __init__(self, queue_name):
        self.sqs = boto.connect_sqs()
        self.queue = self.sqs.lookup(queue_name)

    def poll(self, wait=60, vtimeout=60):
        while 1:
            m = self.queue.read(vtimeout)
            if m:
                task = Task.get_by_id(m.get_body())
                if task:
                    boto.log.info('Task[%s] - calling check' % task.name)
                    task.check(m, vtimeout)
            else:
                time.sleep(wait)

        

    

    
