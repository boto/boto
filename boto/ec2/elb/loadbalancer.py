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

from boto.ec2.elb.healthcheck import HealthCheck
from boto.ec2.elb.instancestate import InstanceState
from boto.ec2.elb.listener import Listener
from boto.ec2.elb.listelement import ListElement
from boto.ec2.zone import Zone
from boto.ec2.instanceinfo import InstanceInfo
from boto.resultset import ResultSet

class LoadBalancer(object):
    """
    Represents an EC2 Load Balancer
    """

    def __init__(self, connection=None, name=None, endpoints=None):
        self.connection = connection
        self.name = name
        self.listeners = None
        self.health_check = None
        self.dns_name = None
        self.created_time = None
        self.instances = None
        self.availability_zones = ListElement()

    def __repr__(self):
        return 'LoadBalancer:%s' % self.name

    def startElement(self, name, attrs, connection):
        if name == 'HealthCheck':
            self.health_check = HealthCheck(self)
            return self.health_check
        elif name == 'Listeners':
            self.listeners = ResultSet([('member', Listener)])
            return self.listeners
        elif name == 'AvailabilityZones':
            return self.availability_zones
        elif name == 'Instances':
            self.instances = ResultSet([('member', InstanceInfo)])
            return self.instances
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'LoadBalancerName':
            self.name = value
        elif name == 'DNSName':
            self.dns_name = value
        elif name == 'CreatedTime':
            self.created_time = value
        elif name == 'InstanceId':
            self.instances.append(value)
        else:
            setattr(self, name, value)

    def enable_zones(self, zones):
        """
        Enable availability zones to this Access Point.
        All zones must be in the same region as the Access Point.

        @type zones: string or List of strings
        @param zones: The name of the zone(s) to add.

        """
        if isinstance(zones, str) or isinstance(zones, unicode):
            zones = [zones]
        new_zones = self.connection.enable_availability_zones(self.name, zones)
        self.availability_zones = new_zones

    def disable_zones(self, zones):
        """
        Disable availability zones from this Access Point.

        @type zones: string or List of strings
        @param zones: The name of the zone(s) to add.

        """
        if isinstance(zones, str) or isinstance(zones, unicode):
            zones = [zones]
        new_zones = self.connection.disable_availability_zones(self.name, zones)
        self.availability_zones = new_zones

    def register_instances(self, instances):
        """
        Add instances to this Load Balancer
        All instances must be in the same region as the Load Balancer.
        Adding endpoints that are already registered with the Load Balancer
        has no effect.

        @type zones: string or List of instance id's
        @param zones: The name of the endpoint(s) to add.

        """
        if isinstance(instances, str) or isinstance(instances, unicode):
            instances = [instances]
        new_instances = self.connection.register_instances(self.name, instances)
        self.instances = new_instances

    def deregister_instances(self, instances):
        """
        Remove instances from this Load Balancer.
        Removing instances that are not registered with the Load Balancer
        has no effect.

        @type zones: string or List of instance id's
        @param zones: The name of the endpoint(s) to add.

        """
        if isinstance(instances, str) or isinstance(instances, unicode):
            instances = [instances]
        new_instances = self.connection.deregister_instances(self.name, instances)
        self.instances = new_instances

    def delete(self):
        """
        Delete this load balancer
        """
        return self.connection.delete_load_balancer(self.name)

    def configure_health_check(self, health_check):
        self.connection.configure_health_check(self.name, health_check)

    def get_instance_health(self, instances=None):
        self.connection.describe_instance_health(self.name, instances)

