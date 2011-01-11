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

class Dimensions(dict):

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'Name':
            self._name = value
        elif name == 'Value':
            self[self._name] = value
        elif name != 'Dimensions' and name != 'member':
            self[name] = value

class Metric(object):

    Statistics = ['Minimum', 'Maximum', 'Sum', 'Average', 'SampleCount']
    Units = ['Seconds', 'Percent', 'Bytes', 'Bits', 'Count',
             'Bytes/Second', 'Bits/Second', 'Count/Second']

    def __init__(self, connection=None):
        self.connection = connection
        self.name = None
        self.namespace = None
        self.dimensions = None

    def __repr__(self):
        s = 'Metric:%s' % self.name
        if self.dimensions:
            for name,value in self.dimensions.items():
                s += '(%s,%s)' % (name, value)
        return s

    def startElement(self, name, attrs, connection):
        if name == 'Dimensions':
            self.dimensions = Dimensions()
            return self.dimensions

    def endElement(self, name, value, connection):
        if name == 'MetricName':
            self.name = value
        elif name == 'Namespace':
            self.namespace = value
        else:
            setattr(self, name, value)

    def query(self, start_time, end_time, statistic, unit=None, period=60):
        return self.connection.get_metric_statistics(period, start_time, end_time,
                                                     self.name, self.namespace, [statistic],
                                                     self.dimensions, unit)

    def describe_alarms(self, period=None, statistic=None, dimensions=None, unit=None):
        return self.connection.describe_alarms_for_metric(self.name,
                                                          self.namespace,
                                                          period,
                                                          statistic,
                                                          dimensions,
                                                          unit)

