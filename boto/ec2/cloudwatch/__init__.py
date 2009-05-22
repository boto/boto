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
"""
from boto.connection import AWSQueryConnection
from boto.ec2.cloudwatch.metric import Metric
from boto.ec2.cloudwatch.datapoint import Datapoint
import boto
import datetime

class CloudWatchConnection(AWSQueryConnection):

    APIVersion = boto.config.get('Boto', 'cloudwatch_version', '2009-05-15')
    Endpoint = boto.config.get('Boto', 'cloudwatch_endpoint', 'monitoring.amazonaws.com')
    SignatureVersion = '1'
    #ResponseError = EC2ResponseError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=True, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, host=Endpoint, debug=0,
                 https_connection_factory=None):
        """
        Init method to create a new connection to EC2 Monitoring Service.
        
        B{Note:} The host argument is overridden by the host specified in the boto configuration file.        
        """
        AWSQueryConnection.__init__(self, aws_access_key_id, aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                                    host, debug, https_connection_factory)

    def build_list_params(self, params, items, label):
        if isinstance(items, str):
            items = [items]
        for i in range(1, len(items)+1):
            params[label % i] = items[i-1]
            
    def get_metric_statistics(self, period, start_time, end_time, measure_name,
                              namespace, statistics=None, dimension=None, unit=None):
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
        if dimension:
            for name in dimension:
                params['Dimension.Name'] = name
                params['Dimension.Value'] = dimension[name]
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
        

    
