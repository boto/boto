.. cloudwatch_tut:

==========
CloudWatch
==========

First, make sure you have something to monitor.  You can either create a
LoadBalancer or enable monitoring on an existing EC2 instance.  To enable
monitoring, you can either call the monitor_instance method on the
EC2Connection object or call the monitor method on the Instance object.

It takes a while for the monitoring data to start accumulating but once
it does, you can do this::

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
metric for our instance.::

    >>> m = metrics[5]
    >>> m
    Metric:CPUUtilization(InstanceId,i-e573e68c)

The Metric object has a query method that lets us actually perform
the query against the collected data in CloudWatch.  To call that,
we need a start time and end time to control the time span of data
that we are interested in.  For this example, let's say we want the
data for the previous hour::

    >>> import datetime
    >>> end = datetime.datetime.now()
    >>> start = end - datetime.timedelta(hours=1)

We also need to supply the Statistic that we want reported and
the Units to use for the results.  The Statistic can be one of these
values::

    ['Minimum', 'Maximum', 'Sum', 'Average', 'SampleCount']

And Units must be one of the following::

    ['Seconds', 'Percent', 'Bytes', 'Bits', 'Count',
    'Bytes/Second', 'Bits/Second', 'Count/Second']

The query method also takes an optional parameter, period.  This
parameter controls the granularity (in seconds) of the data returned.
The smallest period is 60 seconds and the value must be a multiple
of 60 seconds.  So, let's ask for the average as a percent::

    >>> datapoints = m.query(start, end, 'Average', 'Percent')
    >>> len(datapoints)
    60

Our period was 60 seconds and our duration was one hour so
we should get 60 data points back and we can see that we did.
Each element in the datapoints list is a DataPoint object
which is a simple subclass of a Python dict object.  Each
Datapoint object contains all of the information available
about that particular data point.::

    >>> d = datapoints[0]
    >>> d
    {u'Average': 0.0,
     u'SampleCount': 1.0,
     u'Timestamp': u'2009-05-21T19:55:00Z',
     u'Unit': u'Percent'}

My server obviously isn't very busy right now!