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
    message_id = StringProperty()

    def __init__(self, id=None, **kw):
        Model.__init__(self, id, **kw)
        self.hourly = self.hour == '*'
        self.daily = self.hour != '*'
        self.now = datetime.datetime.utcnow()
        
    def check(self, msg, vtimeout):
        """
        Determine if the Task needs to run right now or not.
        If it's an hourly task and it's never been run, run it now.
        If it's a daily task and it's never been run and the hour is right, run it now.        
        """
        need_to_run = False
        new_vtimeout = 0
        boto.log.info('checking Task[%s]-now=%s, last=%s' % (self.name, self.now, self.last_executed))

        if self.hourly and not self.last_executed:
            need_to_run = True
        elif self.daily and not self.last_executed:
            if int(self.hour) == self.now.hour:
                need_to_run = True
        else:
            delta = self.now - self.last_executed
            if self.hourly:
                if delta.seconds >= 60*60:
                    need_to_run = True
                else:
                    new_vtimeout = 60*60 - delta.seconds
            else:
                if delta.days >= 1:
                    need_to_run = True
                else:
                    new_vtimeout = min(60*60*24-delta.seconds, 43200)
        if need_to_run:
            self.run(msg, vtimeout)
            self.last_executed = self.now
            q = msg.queue
            self.schedule(q)
            msg.delete()
        elif new_vtimeout > 0:
            boto.log.info('new_vtimeout: %d' % new_vtimeout)
            msg.change_visibility(new_vtimeout)
            
    def schedule(self, queue):
        msg = queue.new_message(self.id)
        msg = queue.write(msg)
        self.message_id = msg.id
        self.put()
        
    def run(self, msg, vtimeout=60):
        boto.log.info('Task[%s] - running:%s' % (self.name, self.command))
        log_fp = StringIO.StringIO()
        process = subprocess.Popen(self.command, shell=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        nsecs = 5
        current_timeout = vtimeout
        while process.poll() == None:
            boto.log.info('nsecs=%s, timeout=%s' % (nsecs, current_timeout))
            if nsecs >= current_timeout:
                current_timeout += vtimeout
                boto.log.info('Task[%s] - setting timeout to %d seconds' % (self.name, current_timeout))
                msg.change_visibility(current_timeout)
            time.sleep(5)
            nsecs += 5
        t = process.communicate()
        log_fp.write(t[0])
        log_fp.write(t[1])
        boto.log.info('Task[%s] - output: %s' % (self.name, log_fp.getvalue()))
        self.last_status = process.returncode
        self.last_output = log_fp.getvalue()[0:1023]

class TaskPoller(object):

    def __init__(self, queue_name):
        self.sqs = boto.connect_sqs()
        self.queue = self.sqs.lookup(queue_name)

    def poll(self, wait=60, vtimeout=60):
        while 1:
            m = self.queue.read(vtimeout)
            if m:
                task = Task.get_by_id(m.get_body())
                if task:
                    if not task.message_id or m.id == task.message_id:
                        boto.log.info('Task[%s] - read message %s' % (task.name, m.id))
                        task.check(m, vtimeout)
                    else:
                        boto.log.info('Task[%s] - found extraneous message, ignoring' % task.name)
            else:
                time.sleep(wait)

        

    

    
