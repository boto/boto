# Copyright (c) 2010 Hunter Blanks http://artifex.org/~hblanks/
# All rights reserved.
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

"""
Initial, and very limited, unit tests for CloudWatchConnection.
"""

import datetime
import time
import unittest

from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.cloudwatch.metric import Metric

class CloudWatchConnectionTest(unittest.TestCase):

    def test_build_list_params(self):
        c = CloudWatchConnection()
        params = {}
        c.build_list_params(
            params, ['thing1', 'thing2', 'thing3'], 'ThingName%d')
        expected_params = {
            'ThingName1': 'thing1',
            'ThingName2': 'thing2',
            'ThingName3': 'thing3'
            }
        self.assertEqual(params, expected_params)

    def test_build_put_params_one(self):
        c = CloudWatchConnection()
        params = {}
        c.build_put_params(params, name="N", value=1, dimensions={"D": "V"})
        expected_params = {
            'MetricData.member.1.MetricName': 'N',
            'MetricData.member.1.Value': 1,
            'MetricData.member.1.Dimensions.member.1.Name': 'D',
            'MetricData.member.1.Dimensions.member.1.Value': 'V',
            }
        self.assertEqual(params, expected_params)

    def test_build_put_params_multiple_metrics(self):
        c = CloudWatchConnection()
        params = {}
        c.build_put_params(params, name=["N", "M"], value=[1, 2], dimensions={"D": "V"})
        expected_params = {
            'MetricData.member.1.MetricName': 'N',
            'MetricData.member.1.Value': 1,
            'MetricData.member.1.Dimensions.member.1.Name': 'D',
            'MetricData.member.1.Dimensions.member.1.Value': 'V',
            'MetricData.member.2.MetricName': 'M',
            'MetricData.member.2.Value': 2,
            'MetricData.member.2.Dimensions.member.1.Name': 'D',
            'MetricData.member.2.Dimensions.member.1.Value': 'V',
            }
        self.assertEqual(params, expected_params)

    def test_build_put_params_multiple_dimensions(self):
        c = CloudWatchConnection()
        params = {}
        c.build_put_params(params, name="N", value=[1, 2], dimensions=[{"D": "V"}, {"D": "W"}])
        expected_params = {
            'MetricData.member.1.MetricName': 'N',
            'MetricData.member.1.Value': 1,
            'MetricData.member.1.Dimensions.member.1.Name': 'D',
            'MetricData.member.1.Dimensions.member.1.Value': 'V',
            'MetricData.member.2.MetricName': 'N',
            'MetricData.member.2.Value': 2,
            'MetricData.member.2.Dimensions.member.1.Name': 'D',
            'MetricData.member.2.Dimensions.member.1.Value': 'W',
            }
        self.assertEqual(params, expected_params)

    def test_build_put_params_invalid(self):
        c = CloudWatchConnection()
        params = {}
        try:
            c.build_put_params(params, name=["N", "M"], value=[1, 2, 3])
        except:
            pass
        else:
            self.fail("Should not accept lists of different lengths.")

    def test_get_metric_statistics(self):
        c = CloudWatchConnection()
        m = c.list_metrics()[0]
        end = datetime.datetime.now()
        start = end - datetime.timedelta(hours=24*14)
        c.get_metric_statistics(
            3600*24, start, end, m.name, m.namespace, ['Average', 'Sum'])

    def test_put_metric_data(self):
        c = CloudWatchConnection()
        now = datetime.datetime.now()
        name, namespace = 'unit-test-metric', 'boto-unit-test'
        c.put_metric_data(namespace, name, 5, now, 'Bytes')

        # Uncomment the following lines for a slower but more thorough
        # test. (Hurrah for eventual consistency...)
        #
        # metric = Metric(connection=c)
        # metric.name = name
        # metric.namespace = namespace
        # time.sleep(60)
        # l = metric.query(
        #     now - datetime.timedelta(seconds=60),
        #     datetime.datetime.now(),
        #     'Average')
        # assert l
        # for row in l:
        #     self.assertEqual(row['Unit'], 'Bytes')
        #     self.assertEqual(row['Average'], 5.0)

if __name__ == '__main__':
    unittest.main()
