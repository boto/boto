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
load balancing service from AWS.
"""
from boto.connection import AWSQueryConnection
from boto.ec2.instanceinfo import InstanceInfo
from boto.ec2.elb.loadbalancer import LoadBalancer
from boto.ec2.elb.instancestate import InstanceState
from boto.ec2.elb.healthcheck import HealthCheck
import boto

class ELBConnection(AWSQueryConnection):

    APIVersion = boto.config.get('Boto', 'elb_version', '2009-05-15')
    Endpoint = boto.config.get('Boto', 'elb_endpoint', 'elasticloadbalancing.amazonaws.com')
    SignatureVersion = '1'
    #ResponseError = EC2ResponseError

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=False, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, host=Endpoint, debug=0,
                 https_connection_factory=None, path='/'):
        """
        Init method to create a new connection to EC2 Load Balancing Service.

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

    def get_all_load_balancers(self, load_balancer_names=None):
        """
        Retrieve all load balancers associated with your account.

        @type load_balancer_names: list
        @param load_balancer_names: A list of strings of load balancer names

        @rtype: list
        @return: A list of L{LoadBalancer<boto.ec2.elb.loadbalancer.LoadBalancer>}
        """
        params = {}
        if load_balancer_names:
            self.build_list_params(params, load_balancer_names, 'LoadBalancerName.%d')
        return self.get_list('DescribeLoadBalancers', params, [('member', LoadBalancer)])


    def create_load_balancer(self, name, zones, listeners):
        """
        Create a new load balancer for your account.

        @type name: string
        @param name: The mnemonic name associated with the new load balancer

        @type zones: List of strings
        @param zones: The names of the availability zone(s) to add.

        @type listeners: List of tuples
        @param listeners: Each tuple contains three values.
                          (LoadBalancerPortNumber, InstancePortNumber, Protocol)
                          where LoadBalancerPortNumber and InstancePortNumber are
                          integer values between 1 and 65535 and Protocol is a
                          string containing either 'TCP' or 'HTTP'.

        @rtype: L{AccessPoint<boto.ec2.elb.loadbalancer.LoadBalancer}
        @return: The newly created L{LoadBalancer<boto.ec2.elb.loadbalancer.LoadBalancer}
        """
        params = {'LoadBalancerName' : name}
        for i in range(0, len(listeners)):
            params['Listeners.member.%d.LoadBalancerPort' % (i+1)] = listeners[i][0]
            params['Listeners.member.%d.InstancePort' % (i+1)] = listeners[i][1]
            params['Listeners.member.%d.Protocol' % (i+1)] = listeners[i][2]
        self.build_list_params(params, zones, 'AvailabilityZones.member.%d')
        load_balancer = self.get_object('CreateLoadBalancer', params, LoadBalancer)
        load_balancer.name = name
        load_balancer.listeners = listeners
        load_balancer.availability_zones = zones
        return load_balancer

    def delete_load_balancer(self, name):
        """
        Delete a Load Balancer from your account.

        @type name: string
        @param name: The name of the Load Balancer to delete
        """
        params = {'LoadBalancerName': name}
        return self.get_status('DeleteLoadBalancer', params)

    def enable_availability_zones(self, load_balancer_name, zones_to_add):
        """
        Add availability zones to an existing Load Balancer
        All zones must be in the same region as the Load Balancer
        Adding zones that are already registered with the Load Balancer
        has no effect.

        @type load_balancer_name: string
        @param load_balancer_name: The name of the Load Balancer

        @type zones: List of strings
        @param zones: The name of the zone(s) to add.

        @rtype: List of strings
        @return: An updated list of zones for this Load Balancer.

        """
        params = {'LoadBalancerName' : load_balancer_name}
        self.build_list_params(params, zones_to_add, 'AvailabilityZones.member.%d')
        return self.get_list('EnableAvailabilityZonesForLoadBalancer', params, None)

    def disable_availability_zones(self, load_balancer_name, zones_to_remove):
        """
        Remove availability zones from an existing Load Balancer.
        All zones must be in the same region as the Load Balancer.
        Removing zones that are not registered with the Load Balancer
        has no effect.
        You cannot remove all zones from an Load Balancer.

        @type load_balancer_name: string
        @param load_balancer_name: The name of the Load Balancer

        @type zones: List of strings
        @param zones: The name of the zone(s) to remove.

        @rtype: List of strings
        @return: An updated list of zones for this Load Balancer.

        """
        params = {'LoadBalancerName' : load_balancer_name}
        self.build_list_params(params, zones_to_remove, 'AvailabilityZones.member.%d')
        return self.get_list('DisableAvailabilityZonesForLoadBalancer', params, None)

    def register_instances(self, load_balancer_name, instances):
        """
        Add new Instances to an existing Load Balancer.

        @type load_balancer_name: string
        @param load_balancer_name: The name of the Load Balancer

        @type instances: List of strings
        @param instances: The instance ID's of the EC2 instances to add.

        @rtype: List of strings
        @return: An updated list of instances for this Load Balancer.

        """
        params = {'LoadBalancerName' : load_balancer_name}
        self.build_list_params(params, instances, 'Instances.member.%d.InstanceId')
        return self.get_list('RegisterInstancesWithLoadBalancer', params, [('member', InstanceInfo)])

    def deregister_instances(self, load_balancer_name, instances):
        """
        Remove Instances from an existing Load Balancer.

        @type load_balancer_name: string
        @param load_balancer_name: The name of the Load Balancer

        @type instances: List of strings
        @param instances: The instance ID's of the EC2 instances to remove.

        @rtype: List of strings
        @return: An updated list of instances for this Load Balancer.

        """
        params = {'LoadBalancerName' : load_balancer_name}
        self.build_list_params(params, instances, 'Instances.member.%d.InstanceId')
        return self.get_list('DeregisterInstancesFromLoadBalancer', params, [('member', InstanceInfo)])

    def describe_instance_health(self, load_balancer_name, instances=None):
        """
        Get current state of all Instances registered to an Load Balancer.

        @type load_balancer_name: string
        @param load_balancer_name: The name of the Load Balancer

        @type instances: List of strings
        @param instances: The instance ID's of the EC2 instances
                          to return status for.  If not provided,
                          the state of all instances will be returned.

        @rtype: List of L{InstanceState<boto.ec2.elb.instancestate.InstanceState>}
        @return: list of state info for instances in this Load Balancer.

        """
        params = {'LoadBalancerName' : load_balancer_name}
        if instances:
            self.build_list_params(params, instances, 'instances.member.%d')
        return self.get_list('DescribeInstanceHealth', params, [('member', InstanceState)])

    def configure_health_check(self, name, health_check):
        """
        Define a health check for the EndPoints.

        @type name: string
        @param name: The mnemonic name associated with the new access point

        @type health_check: L{HealthCheck<boto.ec2.elb.healthcheck.HealthCheck>}
        @param health_check: A HealthCheck object populated with the desired
                             values.

        @rtype: L{HealthCheck<boto.ec2.elb.healthcheck.HealthCheck}
        @return: The updated L{HealthCheck<boto.ec2.elb.healthcheck.HealthCheck}
        """
        params = {'LoadBalancerName' : name,
                  'HealthCheck.Timeout' : health_check.timeout,
                  'HealthCheck.Target' : health_check.target,
                  'HealthCheck.Interval' : health_check.interval,
                  'HealthCheck.UnhealthyThreshold' : health_check.unhealthy_threshold,
                  'HealthCheck.HealthyThreshold' : health_check.healthy_threshold}
        return self.get_object('ConfigureHealthCheck', params, HealthCheck)
