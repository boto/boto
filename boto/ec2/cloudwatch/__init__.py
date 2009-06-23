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
"""
This module provides an interface to the Elastic Compute Cloud (EC2)
CloudWatch service from AWS.

The 5 Minute How-To Guide
-------------------------
First, make sure you have something to monitor.  You can either create a
LoadBalancer or enable monitoring on an existing EC2 instance.  To enable
monitoring, you can either call the monitor_instance method on the
EC2Connection object or call the monitor method on the Instance object.

It takes a while for the monitoring data to start accumulating but once
it does, you can do this:

>>> import boto
>>> c = boto.connect_cloudwatch()
>>> metrics = c.list_metrics()
>>> metrics
[Metric:NetworkIn,
 Metric:NetworkOut,
 Metric:NetworkOut(InstanceType,m1.small),
 Metric:NetworkIn(InstanceId,i-e573e68c),
 Metric:CPUUtilization(InstanceId,i-e573e68c),
 Metric:DiskWriteBytes(InstanceType,m1.small),
 Metric:DiskWriteBytes(ImageId,ami-a1ffb63),
 Metric:NetworkOut(ImageId,ami-a1ffb63),
 Metric:DiskWriteOps(InstanceType,m1.small),
 Metric:DiskReadBytes(InstanceType,m1.small),
 Metric:DiskReadOps(ImageId,ami-a1ffb63),
 Metric:CPUUtilization(InstanceType,m1.small),
 Metric:NetworkIn(ImageId,ami-a1ffb63),
 Metric:DiskReadOps(InstanceType,m1.small),
 Metric:DiskReadBytes,
 Metric:CPUUtilization,
 Metric:DiskWriteBytes(InstanceId,i-e573e68c),
 Metric:DiskWriteOps(InstanceId,i-e573e68c),
 Metric:DiskWriteOps,
 Metric:DiskReadOps,
 Metric:CPUUtilization(ImageId,ami-a1ffb63),
 Metric:DiskReadOps(InstanceId,i-e573e68c),
 Metric:NetworkOut(InstanceId,i-e573e68c),
 Metric:DiskReadBytes(ImageId,ami-a1ffb63),
 Metric:DiskReadBytes(InstanceId,i-e573e68c),
 Metric:DiskWriteBytes,
 Metric:NetworkIn(InstanceType,m1.small),
 Metric:DiskWriteOps(ImageId,ami-a1ffb63)]

The list_metrics call will return a list of all of the available metrics
that you can query against.  Each entry in the list is a Metric object.
As you can see from the list above, some of the metrics are generic metrics
and some have Dimensions associated with them (e.g. InstanceType=m1.small).
The Dimension can be used to refine your query.  So, for example, I could
query the metric Metric:CPUUtilization which would create the desired statistic
by aggregating cpu utilization data across all sources of information available
or I could refine that by querying the metric
Metric:CPUUtilization(InstanceId,i-e573e68c) which would use only the data
associated with the instance identified by the instance ID i-e573e68c.

Because for this example, I'm only monitoring a single instance, the set
of metrics available to me are fairly limited.  If I was monitoring many
instances, using many different instance types and AMI's and also several
load balancers, the list of available metrics would grow considerably.

Once you have the list of available metrics, you can actually
query the CloudWatch system for that metric.  Let's choose the CPU utilization
metric for our instance.

>>> m = metrics[5]
>>> m
Metric:CPUUtilization(InstanceId,i-e573e68c)

The Metric object has a query method that lets us actually perform
the query against the collected data in CloudWatch.  To call that,
we need a start time and end time to control the time span of data
that we are interested in.  For this example, let's say we want the
data for the previous hour:

>>> import datetime
>>> end = datetime.datetime.now()
>>> start = end - datetime.timedelta(hours=1)

We also need to supply the Statistic that we want reported and
the Units to use for the results.  The Statistic can be one of these
values:

['Minimum', 'Maximum', 'Sum', 'Average', 'Samples']

And Units must be one of the following:

['Seconds', 'Percent', 'Bytes', 'Bits', 'Count',
'Bytes/Second', 'Bits/Second', 'Count/Second']

The query method also takes an optional parameter, period.  This
parameter controls the granularity (in seconds) of the data returned.
The smallest period is 60 seconds and the value must be a multiple
of 60 seconds.  So, let's ask for the average as a percent:

>>> datapoints = m.query(start, end, 'Average', 'Percent')
>>> len(datapoints)
60

Our period was 60 seconds and our duration was one hour so
we should get 60 data points back and we can see that we did.
Each element in the datapoints list is a DataPoint object
which is a simple subclass of a Python dict object.  Each
Datapoint object contains all of the information available
about that particular data point.

>>> d = datapoints[0]
>>> d
{u'Average': 0.0,
 u'Samples': 1.0,
 u'Timestamp': u'2009-05-21T19:55:00Z',
 u'Unit': u'Percent'}

My server obviously isn't very busy right now!
"""
from boto.connection import AWSQueryConnection
from boto.ec2.cloudwatch.metric import Metric
from boto.ec2.cloudwatch.datapoint import Datapoint
import boto
import datetime

class CloudWatchConnection(AWSQueryConnection):

    APIVersion = boto.config.get('Boto', 'cloudwatch_version', '2009-05-15')
    Endpoint = boto.config.get('Boto', 'cloudwatch_endpoint', 'monitoring.amazonaws.com')
    SignatureVersion = '2'

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, host=Endpoint, debug=0,
                 https_connection_factory=None, path='/'):
        """
        Init method to create a new connection to EC2 Monitoring Service.
        
        B{Note:} The host argument is overridden by the host specified in the boto configuration file.        
        """
        AWSQueryConnection.__init__(self, aws_access_key_id, aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                                    host, debug, https_connection_factory, path)

    def build_list_params(self, params, items, label):
        if isinstance(items, str):
            items = [items]
        for i in range(1, len(items)+1):
            params[label % i] = items[i-1]
            
    def get_metric_statistics(self, period, start_time, end_time, measure_name,
                              namespace, statistics=None, dimensions=None, unit=None):
        """
        Get time-series data for one or more statistics of a given metric.
        
        @type measure_name: string
        @param measure_name: CPUUtilization|NetworkIO-in|NetworkIO-out|DiskIO-ALL-read|
                             DiskIO-ALL-write|DiskIO-ALL-read-bytes|DiskIO-ALL-write-bytes
        
        @rtype: list
        @return: A list of L{Images<boto.ec2.image.Image>}
        """
        params = {'Period' : period,
                  'MeasureName' : measure_name,
                  'Namespace' : namespace,
                  'StartTime' : start_time.isoformat(),
                  'EndTime' : end_time.isoformat()}
        if dimensions:
            i = 1
            for name in dimensions:
                params['Dimensions.member.%d.Name' % i] = name
                params['Dimensions.member.%d.Value' % i] = dimensions[name]
                i += 1
        if statistics:
            self.build_list_params(params, statistics, 'Statistics.member.%d')
        return self.get_list('GetMetricStatistics', params, [('member', Datapoint)])

    def list_metrics(self):
        """
        Returns a list of the valid metrics for which there is recorded data available.
        """
        response = self.make_request('ListMetrics')
        body = response.read()
        return self.get_list('ListMetrics', None, [('member', Metric)])
        

    
