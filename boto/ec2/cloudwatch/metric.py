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

from boto.ec2.cloudwatch.alarm import MetricAlarm

class Dimension(dict):

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'Name':
            self._name = value
        elif name == 'Value':
            if self._name in self:
                self[self._name].append(value)
            else:
                self[self._name] = [value]
        else:
            setattr(self, name, value)

class Metric(object):

    Statistics = ['Minimum', 'Maximum', 'Sum', 'Average', 'SampleCount']
    Units = ['Seconds', 'Microseconds', 'Milliseconds', 'Bytes', 'Kilobytes',
             'Megabytes', 'Gigabytes', 'Terabytes', 'Bits', 'Kilobits',
             'Megabits', 'Gigabits', 'Terabits', 'Percent', 'Count',
             'Bytes/Second', 'Kilobytes/Second', 'Megabytes/Second',
             'Gigabytes/Second', 'Terabytes/Second', 'Bits/Second',
             'Kilobits/Second', 'Megabits/Second', 'Gigabits/Second',
             'Terabits/Second', 'Count/Second', None]

    def __init__(self, connection=None):
        self.connection = connection
        self.name = None
        self.namespace = None
        self.dimensions = None

    def __repr__(self):
        return 'Metric:%s' % self.name

    def startElement(self, name, attrs, connection):
        if name == 'Dimensions':
            self.dimensions = Dimension()
            return self.dimensions

    def endElement(self, name, value, connection):
        if name == 'MetricName':
            self.name = value
        elif name == 'Namespace':
            self.namespace = value
        else:
            setattr(self, name, value)

    def query(self, start_time, end_time, statistics, unit=None, period=60):
        if not isinstance(statistics, list):
            statistics = [statistics]
        return self.connection.get_metric_statistics(period,
                                                     start_time,
                                                     end_time,
                                                     self.name,
                                                     self.namespace,
                                                     statistics,
                                                     self.dimensions,
                                                     unit)

    def create_alarm(self, name, comparison, threshold,
                     period, evaluation_periods,
                     statistic, enabled=True, description=None,
                     dimensions=None, alarm_actions=None, ok_actions=None,
                     insufficient_data_actions=None, unit=None):
        if not dimensions:
            dimensions = self.dimensions
        alarm = MetricAlarm(self.connection, name, self.name,
                            self.namespace, statistic, comparison,
                            threshold, period, evaluation_periods,
                            unit, description, dimensions,
                            alarm_actions, insufficient_data_actions,
                            ok_actions)
        if self.connection.put_metric_alarm(alarm):
            return alarm

    def describe_alarms(self, period=None, statistic=None,
                        dimensions=None, unit=None):
        return self.connection.describe_alarms_for_metric(self.name,
                                                          self.namespace,
                                                          period,
                                                          statistic,
                                                          dimensions,
                                                          unit)


    
