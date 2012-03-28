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
#

from boto.rds.regioninfo import RDSRegionInfo


def regions():
    """
    Get all available regions for the RDS service.

    :rtype: list
    :return: A list of :class:`boto.rds.regioninfo.RDSRegionInfo`
    """
    return [RDSRegionInfo(name='us-east-1',
                          endpoint='rds.us-east-1.amazonaws.com'),
            RDSRegionInfo(name='eu-west-1',
                          endpoint='rds.eu-west-1.amazonaws.com'),
            RDSRegionInfo(name='us-west-1',
                          endpoint='rds.us-west-1.amazonaws.com'),
            RDSRegionInfo(name='us-west-2',
                          endpoint='rds.us-west-2.amazonaws.com'),
            RDSRegionInfo(name='sa-east-1',
                          endpoint='rds.sa-east-1.amazonaws.com'),
            RDSRegionInfo(name='ap-northeast-1',
                          endpoint='rds.ap-northeast-1.amazonaws.com'),
            RDSRegionInfo(name='ap-southeast-1',
                          endpoint='rds.ap-southeast-1.amazonaws.com')
            ]


def connect_to_region(region_name, **kw_params):
    """
    Given a valid region name, return a
    :class:`boto.ec2.connection.EC2Connection`.
    Any additional parameters after the region_name are passed on to
    the connect method of the region object.

    :type: str
    :param region_name: The name of the region to connect to.

    :rtype: :class:`boto.ec2.connection.EC2Connection` or ``None``
    :return: A connection to the given region, or None if an invalid region
             name is given
    """
    for region in regions():
        if region.name == region_name:
            return region.connect(**kw_params)
    return None
