# Copyright (c) 2009 Reza Lotun http://reza.lotun.name/
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

import weakref

from boto.ec2.autoscale.request import Request


class Trigger(object):
    """
    An auto scaling trigger.
    """

    def __init__(self, connection=None, name=None, autoscale_group=None,
                 dimensions=None, measure_name=None,
                 statistic=None, unit=None, period=60,
                 lower_threshold=None,
                 lower_breach_scale_increment=None,
                 upper_threshold=None,
                 upper_breach_scale_increment=None,
                 breach_duration=None):
        """
        Initialize an auto-scaling trigger object.
        
        :type name: str
        :param name: The name for this trigger
        
        :type autoscale_group: str
        :param autoscale_group: The name of the AutoScalingGroup that will be
                                associated with the trigger. The AutoScalingGroup
                                that will be affected by the trigger when it is
                                activated.
        
        :type dimensions: list
        :param dimensions: List of tuples, i.e.
                            ('ImageId', 'i-13lasde') etc.
        
        :type measure_name: str
        :param measure_name: The measure name associated with the metric used by
                             the trigger to determine when to activate, for
                             example, CPU, network I/O, or disk I/O.
        
        :type statistic: str
        :param statistic: The particular statistic used by the trigger when
                          fetching metric statistics to examine.
        
        :type period: int
        :param period: The period associated with the metric statistics in
                       seconds. Valid Values: 60 or a multiple of 60.
        
        :type unit: str
        :param unit: The unit of measurement.
        """
        self.name = name
        self.connection = connection
        self.dimensions = dimensions
        self.breach_duration = breach_duration
        self.upper_breach_scale_increment = upper_breach_scale_increment
        self.created_time = None
        self.upper_threshold = upper_threshold
        self.status = None
        self.lower_threshold = lower_threshold
        self.period = period
        self.lower_breach_scale_increment = lower_breach_scale_increment
        self.statistic = statistic
        self.unit = unit
        self.namespace = None
        if autoscale_group:
            self.autoscale_group = weakref.proxy(autoscale_group)
        else:
            self.autoscale_group = None
        self.measure_name = measure_name

    def __repr__(self):
        return 'Trigger:%s' % (self.name)

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'BreachDuration':
            self.breach_duration = value
        elif name == 'TriggerName':
            self.name = value
        elif name == 'Period':
            self.period = value
        elif name == 'CreatedTime':
            self.created_time = value
        elif name == 'Statistic':
            self.statistic = value
        elif name == 'Unit':
            self.unit = value
        elif name == 'Namespace':
            self.namespace = value
        elif name == 'AutoScalingGroupName':
            self.autoscale_group_name = value
        elif name == 'MeasureName':
            self.measure_name = value
        else:
            setattr(self, name, value)

    def update(self):
        """ Write out differences to trigger. """
        self.connection.create_trigger(self)

    def delete(self):
        """ Delete this trigger. """
        params = {
                  'TriggerName'          : self.name,
                  'AutoScalingGroupName' : self.autoscale_group_name,
                  }
        req =self.connection.get_object('DeleteTrigger', params,
                                        Request)
        self.connection.last_request = req
        return req

