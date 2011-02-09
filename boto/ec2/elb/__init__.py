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
from boto.regioninfo import RegionInfo
import boto

RegionData = {
    'us-east-1' : 'elasticloadbalancing.us-east-1.amazonaws.com',
    'us-west-1' : 'elasticloadbalancing.us-west-1.amazonaws.com',
    'eu-west-1' : 'elasticloadbalancing.eu-west-1.amazonaws.com',
    'ap-southeast-1' : 'elasticloadbalancing.ap-southeast-1.amazonaws.com'}

def regions():
    """
    Get all available regions for the SDB service.

    :rtype: list
    :return: A list of :class:`boto.RegionInfo` instances
    """
    regions = []
    for region_name in RegionData:
        region = RegionInfo(name=region_name,
                            endpoint=RegionData[region_name],
                            connection_cls=ELBConnection)
        regions.append(region)
    return regions

def connect_to_region(region_name):
    """
    Given a valid region name, return a 
    :class:`boto.ec2.elb.ELBConnection`.
    
    :param str region_name: The name of the region to connect to.
    
    :rtype: :class:`boto.ec2.ELBConnection` or ``None``
    :return: A connection to the given region, or None if an invalid region
        name is given
    """
    for region in regions():
        if region.name == region_name:
            return region.connect()
    return None

class ELBConnection(AWSQueryConnection):

    APIVersion = boto.config.get('Boto', 'elb_version', '2010-07-01')
    DefaultRegionName = boto.config.get('Boto', 'elb_region_name', 'us-east-1')
    DefaultRegionEndpoint = boto.config.get('Boto', 'elb_region_endpoint',
                                            'elasticloadbalancing.amazonaws.com')

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=False, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, debug=0,
                 https_connection_factory=None, region=None, path='/'):
        """
        Init method to create a new connection to EC2 Load Balancing Service.

        B{Note:} The region argument is overridden by the region specified in
        the boto configuration file.
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
        for i in range(1, len(items)+1):
            params[label % i] = items[i-1]

    def get_all_load_balancers(self, load_balancer_names=None):
        """
        Retrieve all load balancers associated with your account.

        :type load_balancer_names: list
        :param load_balancer_names: An optional list of load balancer names

        :rtype: list
        :return: A list of :class:`boto.ec2.elb.loadbalancer.LoadBalancer`
        """
        params = {}
        if load_balancer_names:
            self.build_list_params(params, load_balancer_names, 'LoadBalancerNames.member.%d')
        return self.get_list('DescribeLoadBalancers', params, [('member', LoadBalancer)])


    def create_load_balancer(self, name, zones, listeners):
        """
        Create a new load balancer for your account.

        :type name: string
        :param name: The mnemonic name associated with the new load balancer

        :type zones: List of strings
        :param zones: The names of the availability zone(s) to add.

        :type listeners: List of tuples
        :param listeners: Each tuple contains three or four values,
                          (LoadBalancerPortNumber, InstancePortNumber, Protocol,
                          [SSLCertificateId])
                          where LoadBalancerPortNumber and InstancePortNumber are
                          integer values between 1 and 65535, Protocol is a
                          string containing either 'TCP', 'HTTP' or 'HTTPS';
                          SSLCertificateID is the ARN of a AWS AIM certificate,
                          and must be specified when doing HTTPS.

        :rtype: :class:`boto.ec2.elb.loadbalancer.LoadBalancer`
        :return: The newly created :class:`boto.ec2.elb.loadbalancer.LoadBalancer`
        """
        params = {'LoadBalancerName' : name}
        for i in range(0, len(listeners)):
            params['Listeners.member.%d.LoadBalancerPort' % (i+1)] = listeners[i][0]
            params['Listeners.member.%d.InstancePort' % (i+1)] = listeners[i][1]
            params['Listeners.member.%d.Protocol' % (i+1)] = listeners[i][2]
            if listeners[i][2]=='HTTPS':
                params['Listeners.member.%d.SSLCertificateId' % (i+1)] = listeners[i][3]
        self.build_list_params(params, zones, 'AvailabilityZones.member.%d')
        load_balancer = self.get_object('CreateLoadBalancer', params, LoadBalancer)
        load_balancer.name = name
        load_balancer.listeners = listeners
        load_balancer.availability_zones = zones
        return load_balancer

    def create_load_balancer_listeners(self, name, listeners):
        """
        Creates a Listener (or group of listeners) for an existing Load Balancer

        :type name: string
        :param name: The name of the load balancer to create the listeners for

        :type listeners: List of tuples
        :param listeners: Each tuple contains three values,
                          (LoadBalancerPortNumber, InstancePortNumber, Protocol,
                          [SSLCertificateId])
                          where LoadBalancerPortNumber and InstancePortNumber are
                          integer values between 1 and 65535, Protocol is a
                          string containing either 'TCP', 'HTTP' or 'HTTPS';
                          SSLCertificateID is the ARN of a AWS AIM certificate,
                          and must be specified when doing HTTPS.

        :return: The status of the request
        """
        params = {'LoadBalancerName' : name}
        for i in range(0, len(listeners)):
            params['Listeners.member.%d.LoadBalancerPort' % (i+1)] = listeners[i][0]
            params['Listeners.member.%d.InstancePort' % (i+1)] = listeners[i][1]
            params['Listeners.member.%d.Protocol' % (i+1)] = listeners[i][2]
            if listeners[i][2]=='HTTPS':
                params['Listeners.member.%d.SSLCertificateId' % (i+1)] = listeners[i][3]
        return self.get_status('CreateLoadBalancerListeners', params)


    def delete_load_balancer(self, name):
        """
        Delete a Load Balancer from your account.

        :type name: string
        :param name: The name of the Load Balancer to delete
        """
        params = {'LoadBalancerName': name}
        return self.get_status('DeleteLoadBalancer', params)

    def delete_load_balancer_listeners(self, name, ports):
        """
        Deletes a load balancer listener (or group of listeners)

        :type name: string
        :param name: The name of the load balancer to create the listeners for

        :type ports: List int
        :param ports: Each int represents the port on the ELB to be removed

        :return: The status of the request
        """
        params = {'LoadBalancerName' : name}
        for i in range(0, len(ports)):
            params['LoadBalancerPorts.member.%d' % (i+1)] = ports[i]
        return self.get_status('DeleteLoadBalancerListeners', params)



    def enable_availability_zones(self, load_balancer_name, zones_to_add):
        """
        Add availability zones to an existing Load Balancer
        All zones must be in the same region as the Load Balancer
        Adding zones that are already registered with the Load Balancer
        has no effect.

        :type load_balancer_name: string
        :param load_balancer_name: The name of the Load Balancer

        :type zones: List of strings
        :param zones: The name of the zone(s) to add.

        :rtype: List of strings
        :return: An updated list of zones for this Load Balancer.

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

        :type load_balancer_name: string
        :param load_balancer_name: The name of the Load Balancer

        :type zones: List of strings
        :param zones: The name of the zone(s) to remove.

        :rtype: List of strings
        :return: An updated list of zones for this Load Balancer.

        """
        params = {'LoadBalancerName' : load_balancer_name}
        self.build_list_params(params, zones_to_remove, 'AvailabilityZones.member.%d')
        return self.get_list('DisableAvailabilityZonesForLoadBalancer', params, None)

    def register_instances(self, load_balancer_name, instances):
        """
        Add new Instances to an existing Load Balancer.

        :type load_balancer_name: string
        :param load_balancer_name: The name of the Load Balancer

        :type instances: List of strings
        :param instances: The instance ID's of the EC2 instances to add.

        :rtype: List of strings
        :return: An updated list of instances for this Load Balancer.

        """
        params = {'LoadBalancerName' : load_balancer_name}
        self.build_list_params(params, instances, 'Instances.member.%d.InstanceId')
        return self.get_list('RegisterInstancesWithLoadBalancer', params, [('member', InstanceInfo)])

    def deregister_instances(self, load_balancer_name, instances):
        """
        Remove Instances from an existing Load Balancer.

        :type load_balancer_name: string
        :param load_balancer_name: The name of the Load Balancer

        :type instances: List of strings
        :param instances: The instance ID's of the EC2 instances to remove.

        :rtype: List of strings
        :return: An updated list of instances for this Load Balancer.

        """
        params = {'LoadBalancerName' : load_balancer_name}
        self.build_list_params(params, instances, 'Instances.member.%d.InstanceId')
        return self.get_list('DeregisterInstancesFromLoadBalancer', params, [('member', InstanceInfo)])

    def describe_instance_health(self, load_balancer_name, instances=None):
        """
        Get current state of all Instances registered to an Load Balancer.

        :type load_balancer_name: string
        :param load_balancer_name: The name of the Load Balancer

        :type instances: List of strings
        :param instances: The instance ID's of the EC2 instances
                          to return status for.  If not provided,
                          the state of all instances will be returned.

        :rtype: List of :class:`boto.ec2.elb.instancestate.InstanceState`
        :return: list of state info for instances in this Load Balancer.

        """
        params = {'LoadBalancerName' : load_balancer_name}
        if instances:
            self.build_list_params(params, instances, 'Instances.member.%d')
        return self.get_list('DescribeInstanceHealth', params, [('member', InstanceState)])

    def configure_health_check(self, name, health_check):
        """
        Define a health check for the EndPoints.

        :type name: string
        :param name: The mnemonic name associated with the new access point

        :type health_check: :class:`boto.ec2.elb.healthcheck.HealthCheck`
        :param health_check: A HealthCheck object populated with the desired
                             values.

        :rtype: :class:`boto.ec2.elb.healthcheck.HealthCheck`
        :return: The updated :class:`boto.ec2.elb.healthcheck.HealthCheck`
        """
        params = {'LoadBalancerName' : name,
                  'HealthCheck.Timeout' : health_check.timeout,
                  'HealthCheck.Target' : health_check.target,
                  'HealthCheck.Interval' : health_check.interval,
                  'HealthCheck.UnhealthyThreshold' : health_check.unhealthy_threshold,
                  'HealthCheck.HealthyThreshold' : health_check.healthy_threshold}
        return self.get_object('ConfigureHealthCheck', params, HealthCheck)

    def set_lb_listener_SSL_certificate(self, lb_name, lb_port, ssl_certificate_id):
        """
        Sets the certificate that terminates the specified listener's SSL
        connections. The specified certificate replaces any prior certificate
        that was used on the same LoadBalancer and port.
        """
        params = {
                    'LoadBalancerName'          :   lb_name,
                    'LoadBalancerPort'          :   lb_port,
                    'SSLCertificateId'          :   ssl_certificate_id,
                 }
        return self.get_status('SetLoadBalancerListenerSSLCertificate', params)

    def create_app_cookie_stickiness_policy(self, name, lb_name, policy_name):
        """
        Generates a stickiness policy with sticky session lifetimes that follow
        that of an application-generated cookie. This policy can only be
        associated with HTTP listeners.

        This policy is similar to the policy created by
        CreateLBCookieStickinessPolicy, except that the lifetime of the special
        Elastic Load Balancing cookie follows the lifetime of the
        application-generated cookie specified in the policy configuration. The
        load balancer only inserts a new stickiness cookie when the application
        response includes a new application cookie.

        If the application cookie is explicitly removed or expires, the session
        stops being sticky until a new application cookie is issued.
        """
        params = {
                    'CookieName'        :   name,
                    'LoadBalancerName'  :   lb_name,
                    'PolicyName'        :   policy_name,
                 }
        return self.get_status('CreateAppCookieStickinessPolicy', params)

    def create_lb_cookie_stickiness_policy(self, cookie_expiration_period, lb_name, policy_name):
        """
        Generates a stickiness policy with sticky session lifetimes controlled
        by the lifetime of the browser (user-agent) or a specified expiration
        period. This policy can only be associated only with HTTP listeners.

        When a load balancer implements this policy, the load balancer uses a
        special cookie to track the backend server instance for each request.
        When the load balancer receives a request, it first checks to see if
        this cookie is present in the request. If so, the load balancer sends
        the request to the application server specified in the cookie. If not,
        the load balancer sends the request to a server that is chosen based on
        the existing load balancing algorithm.

        A cookie is inserted into the response for binding subsequent requests
        from the same user to that server. The validity of the cookie is based
        on the cookie expiration time, which is specified in the policy
        configuration.
        """
        params = {
                    'CookieExpirationPeriod'    :   cookie_expiration_period,
                    'LoadBalancerName'          :   lb_name,
                    'PolicyName'                :   policy_name,
                 }
        return self.get_status('CreateLBCookieStickinessPolicy', params)

    def delete_lb_policy(self, lb_name, policy_name):
        """
        Deletes a policy from the LoadBalancer. The specified policy must not
        be enabled for any listeners.
        """
        params = {
                    'LoadBalancerName'          : lb_name,
                    'PolicyName'                : policy_name,
                 }
        return self.get_status('DeleteLoadBalancerPolicy', params)

    def set_lb_policies_of_listener(self, lb_name, lb_port, policies):
        """
        Associates, updates, or disables a policy with a listener on the load
        balancer. Currently only zero (0) or one (1) policy can be associated
        with a listener.
        """
        params = {
                    'LoadBalancerName'          : lb_name,
                    'LoadBalancerPort'          : lb_port,
                 }
        self.build_list_params(params, policies, 'PolicyNames.member.%d')
        return self.get_status('SetLoadBalancerPoliciesOfListener', params)


