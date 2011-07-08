# Copyright (c) 2006-2011 Mitch Garnaat http://garnaat.org/
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

['Minimum', 'Maximum', 'Sum', 'Average', 'SampleCount']

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
 u'SampleCount': 1.0,
 u'Timestamp': u'2009-05-21T19:55:00Z',
 u'Unit': u'Percent'}

My server obviously isn't very busy right now!
"""
try:
    import simplejson as json
except ImportError:
    import json

from boto.connection import AWSQueryConnection
from boto.ec2.cloudwatch.metric import Metric
from boto.ec2.cloudwatch.alarm import MetricAlarm, AlarmHistoryItem
from boto.ec2.cloudwatch.datapoint import Datapoint
from boto.regioninfo import RegionInfo
import boto

import logging
log = logging.getLogger(__name__)

RegionData = {
    'us-east-1' : 'monitoring.us-east-1.amazonaws.com',
    'us-west-1' : 'monitoring.us-west-1.amazonaws.com',
    'eu-west-1' : 'monitoring.eu-west-1.amazonaws.com',
    'ap-northeast-1' : 'monitoring.ap-northeast-1.amazonaws.com',
    'ap-southeast-1' : 'monitoring.ap-southeast-1.amazonaws.com'}

def regions():
    """
    Get all available regions for the CloudWatch service.

    :rtype: list
    :return: A list of :class:`boto.RegionInfo` instances
    """
    regions = []
    for region_name in RegionData:
        region = RegionInfo(name=region_name,
                            endpoint=RegionData[region_name],
                            connection_cls=CloudWatchConnection)
        regions.append(region)
    return regions

def connect_to_region(region_name, **kw_params):
    """
    Given a valid region name, return a
    :class:`boto.ec2.cloudwatch.CloudWatchConnection`.

    :param str region_name: The name of the region to connect to.

    :rtype: :class:`boto.ec2.CloudWatchConnection` or ``None``
    :return: A connection to the given region, or None if an invalid region
        name is given
    """
    for region in regions():
        if region.name == region_name:
            return region.connect(**kw_params)
    return None


class CloudWatchConnection(AWSQueryConnection):

    APIVersion = boto.config.get('Boto', 'cloudwatch_version', '2010-08-01')
    DefaultRegionName = boto.config.get('Boto', 'cloudwatch_region_name',
                                        'us-east-1')
    DefaultRegionEndpoint = boto.config.get('Boto',
                                            'cloudwatch_region_endpoint',
                                            'monitoring.amazonaws.com')


    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None, path='/'):
        """
        Init method to create a new connection to EC2 Monitoring Service.

        B{Note:} The host argument is overridden by the host specified in the
        boto configuration file.
        """
        if not region:
            region = RegionInfo(self, self.DefaultRegionName,
                                self.DefaultRegionEndpoint)
        self.region = region

        AWSQueryConnection.__init__(self, aws_access_key_id,
                                    aws_secret_access_key, 
                                    is_secure, port, proxy, proxy_port,
                                    proxy_user, proxy_pass,
                                    self.region.endpoint, debug,
                                    https_connection_factory, path)

    def _required_auth_capability(self):
        return ['ec2']

    def build_list_params(self, params, items, label):
        if isinstance(items, str):
            items = [items]
        for i, item in enumerate(items, 1):
            if isinstance(item, dict):
                for k,v in item.iteritems():
                    params[label % (i, 'Name')] = k
                    params[label % (i, 'Value')] = v
            else:
                params[label % i] = item

    def get_metric_statistics(self, period, start_time, end_time, metric_name,
                              namespace, statistics, dimensions=None,
                              unit=None):
        """
        Get time-series data for one or more statistics of a given metric.

        :type period: integer
        :param period: The granularity, in seconds, of the returned datapoints.
                       Period must be at least 60 seconds and must be a multiple
                       of 60. The default value is 60.

        :type start_time: datetime
        :param start_time: The time stamp to use for determining the first
                           datapoint to return. The value specified is
                           inclusive; results include datapoints with the
                           time stamp specified.

        :type end_time: datetime
        :param end_time: The time stamp to use for determining the last
                         datapoint to return. The value specified is
                         exclusive; results will include datapoints up to
                         the time stamp specified.

        :type metric_name: string
        :param metric_name: The metric name.
        :rtype: list
        """
        params = {'Period' : period,
                  'MetricName' : metric_name,
                  'Namespace' : namespace,
                  'StartTime' : start_time.isoformat(),
                  'EndTime' : end_time.isoformat()}
        self.build_list_params(params, statistics, 'Statistics.member.%d')
        if dimensions:
            for i, name in enumerate(dimensions, 1):
                params['Dimensions.member.%d.Name' % i] = name
                params['Dimensions.member.%d.Value' % i] = dimensions[name]
        return self.get_list('GetMetricStatistics', params,
                             [('member', Datapoint)])

    def list_metrics(self, next_token=None):
        """
        Returns a list of the valid metrics for which there is recorded
        data available.

        :type next_token: string
        :param next_token: A maximum of 500 metrics will be returned at one
                           time.  If more results are available, the
                           ResultSet returned will contain a non-Null
                           next_token attribute.  Passing that token as a
                           parameter to list_metrics will retrieve the
                           next page of metrics.
        """
        params = {}
        if next_token:
            params['NextToken'] = next_token
        return self.get_list('ListMetrics', params, [('member', Metric)])
    
    def put_metric_data(self, namespace, name, value=None, timestamp=None, 
                        unit=None, dimensions=None, statistics=None):
        """
        Publishes metric data points to Amazon CloudWatch. Amazon Cloudwatch 
        associates the data points with the specified metric. If the specified 
        metric does not exist, Amazon CloudWatch creates the metric.

        :type namespace: string
        :param namespace: The namespace of the metric.

        :type name: string
        :param name: The name of the metric.

        :type value: int
        :param value: The value for the metric.

        :type timestamp: datetime
        :param timestamp: The time stamp used for the metric. If not specified, 
                          the default value is set to the time the metric data 
                          was received.
        
        :type unit: string
        :param unit: The unit of the metric.  Valid Values: Seconds | 
                     Microseconds | Milliseconds | Bytes | Kilobytes | 
                     Megabytes | Gigabytes | Terabytes | Bits | Kilobits | 
                     Megabits | Gigabits | Terabits | Percent | Count | 
                     Bytes/Second | Kilobytes/Second | Megabytes/Second | 
                     Gigabytes/Second | Terabytes/Second | Bits/Second | 
                     Kilobits/Second | Megabits/Second | Gigabits/Second | 
                     Terabits/Second | Count/Second | None
        
        :type dimensions: dict
        :param dimensions: Add extra name value pairs to associate 
                           with the metric, i.e.:
                           {'name1': value1, 'name2': value2}
        
        :type statistics: dict
        :param statistics: Use a statistic set instead of a value, for example
                           {'maximum': 30, 'minimum': 1,
                            'samplecount': 100, 'sum': 10000}
        """
        params = {'Namespace': namespace}
        metric_data = {'MetricName': name}

        if timestamp:
            metric_data['Timestamp'] = timestamp.isoformat()
        
        if unit:
            metric_data['Unit'] = unit
        
        if dimensions:
            for i, (name, val) in enumerate(dimensions.iteritems(), 1):
                metric_data['Dimensions.member.%d.Name' % i] = name
                metric_data['Dimensions.member.%d.Value' % i] = val
        
        if statistics:
            metric_data['StatisticValues.Maximum'] = statistics['maximum']
            metric_data['StatisticValues.Minimum'] = statistics['minimum']
            metric_data['StatisticValues.SampleCount'] = statistics['samplecount']
            metric_data['StatisticValues.Sum'] = statistics['sum']
            if value != None:
                log.warn('You supplied a value and statistics for a metric.  Posting statistics and not value.')

        elif value != None:
            metric_data['Value'] = value
        else:
            raise Exception('Must specify a value or statistics to put.')

        for k, v in metric_data.iteritems():
            params['MetricData.member.1.%s' % (k)] = v

        return self.get_status('PutMetricData', params)


    def describe_alarms(self, action_prefix=None, alarm_name_prefix=None,
                        alarm_names=None, max_records=None, state_value=None,
                        next_token=None):
        """
        Retrieves alarms with the specified names. If no name is specified, all
        alarms for the user are returned. Alarms can be retrieved by using only
        a prefix for the alarm name, the alarm state, or a prefix for any
        action.

        :type action_prefix: string
        :param action_name: The action name prefix.

        :type alarm_name_prefix: string
        :param alarm_name_prefix: The alarm name prefix. AlarmNames cannot
                                  be specified if this parameter is specified.

        :type alarm_names: list
        :param alarm_names: A list of alarm names to retrieve information for.

        :type max_records: int
        :param max_records: The maximum number of alarm descriptions
                            to retrieve.

        :type state_value: string
        :param state_value: The state value to be used in matching alarms.

        :type next_token: string
        :param next_token: The token returned by a previous call to
                           indicate that there is more data.

        :rtype list
        """
        params = {}
        if action_prefix:
            params['ActionPrefix'] = action_prefix
        if alarm_name_prefix:
            params['AlarmNamePrefix'] = alarm_name_prefix
        elif alarm_names:
            self.build_list_params(params, alarm_names, 'AlarmNames.member.%s')
        if max_records:
            params['MaxRecords'] = max_records
        if next_token:
            params['NextToken'] = next_token
        if state_value:
            params['StateValue'] = state_value
        return self.get_list('DescribeAlarms', params,
                             [('member', MetricAlarm)])

    def describe_alarm_history(self, alarm_name=None,
                               start_date=None, end_date=None,
                               max_records=None, history_item_type=None,
                               next_token=None):
        """
        Retrieves history for the specified alarm. Filter alarms by date range
        or item type. If an alarm name is not specified, Amazon CloudWatch
        returns histories for all of the owner's alarms.

        Amazon CloudWatch retains the history of deleted alarms for a period of
        six weeks. If an alarm has been deleted, its history can still be
        queried.

        :type alarm_name: string
        :param alarm_name: The name of the alarm.

        :type start_date: datetime
        :param start_date: The starting date to retrieve alarm history.

        :type end_date: datetime
        :param end_date: The starting date to retrieve alarm history.

        :type history_item_type: string
        :param history_item_type: The type of alarm histories to retreive
                                  (ConfigurationUpdate | StateUpdate | Action)

        :type max_records: int
        :param max_records: The maximum number of alarm descriptions
                            to retrieve.

        :type next_token: string
        :param next_token: The token returned by a previous call to indicate
                           that there is more data.

        :rtype list
        """
        params = {}
        if alarm_name:
            params['AlarmName'] = alarm_name
        if start_date:
            params['StartDate'] = start_date.isoformat()
        if end_date:
            params['EndDate'] = end_date.isoformat()
        if history_item_type:
            params['HistoryItemType'] = history_item_type
        if max_records:
            params['MaxRecords'] = max_records
        if next_token:
            params['NextToken'] = next_token
        return self.get_list('DescribeAlarmHistory', params,
                             [('member', AlarmHistoryItem)])

    def describe_alarms_for_metric(self, metric_name, namespace, period=None,
                                   statistic=None, dimensions=None, unit=None):
        """
        Retrieves all alarms for a single metric. Specify a statistic, period,
        or unit to filter the set of alarms further.

        :type metric_name: string
        :param metric_name: The name of the metric

        :type namespace: string
        :param namespace: The namespace of the metric.

        :type period: int
        :param period: The period in seconds over which the statistic
                       is applied.

        :type statistic: string
        :param statistic: The statistic for the metric.

        :type dimensions: list

        :type unit: string

        :rtype list
        """
        params = {'MetricName' : metric_name,
                  'Namespace' : namespace}
        if period:
            params['Period'] = period
        if statistic:
            params['Statistic'] = statistic
        if dimensions:
            self.build_list_params(params, dimensions,
                                   'Dimensions.member.%s.%s')
        if unit:
            params['Unit'] = unit
        return self.get_list('DescribeAlarmsForMetric', params,
                             [('member', MetricAlarm)])

    def put_metric_alarm(self, alarm):
        """
        Creates or updates an alarm and associates it with the specified Amazon
        CloudWatch metric. Optionally, this operation can associate one or more
        Amazon Simple Notification Service resources with the alarm.

        When this operation creates an alarm, the alarm state is immediately
        set to INSUFFICIENT_DATA. The alarm is evaluated and its StateValue is
        set appropriately. Any actions associated with the StateValue is then
        executed.

        When updating an existing alarm, its StateValue is left unchanged.

        :type alarm: boto.ec2.cloudwatch.alarm.MetricAlarm
        :param alarm: MetricAlarm object.
        """
        params = {
                    'AlarmName'             :       alarm.name,
                    'MetricName'            :       alarm.metric,
                    'Namespace'             :       alarm.namespace,
                    'Statistic'             :       alarm.statistic,
                    'ComparisonOperator'    :       alarm.comparison,
                    'Threshold'             :       alarm.threshold,
                    'EvaluationPeriods'     :       alarm.evaluation_periods,
                    'Period'                :       alarm.period,
                 }
        if alarm.actions_enabled is not None:
            params['ActionsEnabled'] = alarm.actions_enabled
        if alarm.alarm_actions:
            self.build_list_params(params, alarm.alarm_actions,
                                   'AlarmActions.member.%s')
        if alarm.description:
            params['AlarmDescription'] = alarm.description
        if alarm.dimensions:
            self.build_list_params(params, alarm.dimensions,
                                   'Dimensions.member.%s.%s')
        if alarm.insufficient_data_actions:
            self.build_list_params(params, alarm.insufficient_data_actions,
                                   'InsufficientDataActions.member.%s')
        if alarm.ok_actions:
            self.build_list_params(params, alarm.ok_actions,
                                   'OKActions.member.%s')
        if alarm.unit:
            params['Unit'] = alarm.unit
        alarm.connection = self
        return self.get_status('PutMetricAlarm', params)
    create_alarm = put_metric_alarm
    update_alarm = put_metric_alarm

    def delete_alarms(self, alarms):
        """
        Deletes all specified alarms. In the event of an error, no
        alarms are deleted.

        :type alarms: list
        :param alarms: List of alarm names.
        """
        params = {}
        self.build_list_params(params, alarms, 'AlarmNames.member.%s')
        return self.get_status('DeleteAlarms', params)

    def set_alarm_state(self, alarm_name, state_reason, state_value,
                        state_reason_data=None):
        """
        Temporarily sets the state of an alarm. When the updated StateValue
        differs from the previous value, the action configured for the
        appropriate state is invoked. This is not a permanent change. The next
        periodic alarm check (in about a minute) will set the alarm to its
        actual state.

        :type alarm_name: string
        :param alarm_name: Descriptive name for alarm.

        :type state_reason: string
        :param state_reason: Human readable reason.

        :type state_value: string
        :param state_value: OK | ALARM | INSUFFICIENT_DATA

        :type state_reason_data: string
        :param state_reason_data: Reason string (will be jsonified).
        """
        params = {'AlarmName' : alarm_name,
                  'StateReason' : state_reason,
                  'StateValue' : state_value}
        if state_reason_data:
            params['StateReasonData'] = json.dumps(state_reason_data)

        return self.get_status('SetAlarmState', params)

    def enable_alarm_actions(self, alarm_names):
        """
        Enables actions for the specified alarms.

        :type alarms: list
        :param alarms: List of alarm names.
        """
        params = {}
        self.build_list_params(params, alarm_names, 'AlarmNames.member.%s')
        return self.get_status('EnableAlarmActions', params)

    def disable_alarm_actions(self, alarm_names):
        """
        Disables actions for the specified alarms.

        :type alarms: list
        :param alarms: List of alarm names.
        """
        params = {}
        self.build_list_params(params, alarm_names, 'AlarmNames.member.%s')
        return self.get_status('DisableAlarmActions', params)

