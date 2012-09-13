# Copyright (c) 2009 Mitch Garnaat http://garnaat.org/
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
This module represents an interface to the EC2 VPC Service from AWS.
"""

from .connection import VPCConnection
from boto.regioninfo import RegionInfo

RegionData = {
    'us-east-1': 'ec2.us-east-1.amazonaws.com',
    'us-west-1': 'ec2.us-west-1.amazonaws.com',
    'us-west-2': 'ec2.us-west-2.amazonaws.com',
    'sa-east-1': 'ec2.sa-east-1.amazonaws.com',
    'eu-west-1': 'ec2.eu-west-1.amazonaws.com',
    'ap-northeast-1': 'ec2.ap-northeast-1.amazonaws.com',
    'ap-southeast-1': 'ec2.ap-southeast-1.amazonaws.com'}


def regions():
    """
    Get all available regions for the VPCConnection service.

    :rtype: list
    :return: A list of :class:`boto.RegionInfo` instances
    """
    regions = []
    for region_name in RegionData:
        region = RegionInfo(name=region_name,
                            endpoint=RegionData[region_name],
                            connection_cls=VPCConnection)
        regions.append(region)
    return regions


def connect_to_region(region_name, **kw_params):
    """
    Given a valid region name, return a
    :class:`boto.ec2.VPCConnection`.

    :param str region_name: The name of the region to connect to.

    :rtype: :class:`boto.ec2.VPCConnection` or ``None``
    :return: A connection to the given region, or None if an invalid region
        name is given
    """
    for region in regions():
        if region.name == region_name:
            return region.connect(**kw_params)
    return None
