.. _autoscale_tut:

=============================================
An Introduction to boto's Autoscale interface
=============================================

This tutorial focuses on the boto interface to the Autoscale service. This
assumes you are familiar with boto's EC2 interface and concepts.

Autoscale Concepts
------------------

The AWS Autoscale service is comprised of three core concepts:

 #. *Autoscale Group (AG):* An AG can be viewed as a collection of criteria for
    maintaining or scaling a set of EC2 instances over one or more availability
    zones. An AG is limited to a single region.
 #. *Launch Configuration (LC):* An LC is the set of information needed by the
    AG to launch new instances - this can encompass image ids, startup data,
    security groups and keys. Only one LC is attached to an AG.
 #. *Triggers*: A trigger is essentially a set of rules for determining when to
    scale an AG up or down. These rules can encompass a set of metrics such as
    average CPU usage across instances, or incoming requests, a threshold for
    when an action will take place, as well as parameters to control how long
    to wait after a threshold is crossed.

Creating a Connection
---------------------
The first step in accessing autoscaling is to create a connection to the service.
There are two ways to do this in boto.  The first is:

>>> from boto.ec2.autoscale import AutoScaleConnection
>>> conn = AutoScaleConnection('<aws access key>', '<aws secret key>')

Alternatively, you can use the shortcut:

>>> conn = boto.connect_autoscale()

A Note About Regions and Endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Like EC2 the Autoscale service has a different endpoint for each region. By
default the US endpoint is used. To choose a specific region, instantiate the
AutoScaleConnection object with that region's endpoint.

>>> ec2 = boto.connect_autoscale(host='autoscaling.eu-west-1.amazonaws.com')

Alternatively, edit your boto.cfg with the default Autoscale endpoint to use::

    [Boto]
    autoscale_endpoint = autoscaling.eu-west-1.amazonaws.com

Getting Existing AutoScale Groups
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To retrieve existing autoscale groups:

>>> conn.get_all_groups()

You will get back a list of AutoScale group objects, one for each AG you have.

Creating Autoscaling Groups
---------------------------
An Autoscaling group has a number of parameters associated with it.

 #. *Name*: The name of the AG.
 #. *Availability Zones*: The list of availability zones it is defined over.
 #. *Minimum Size*: Minimum number of instances running at one time.
 #. *Maximum Size*: Maximum number of instances running at one time.
 #. *Launch Configuration (LC)*: A set of instructions on how to launch an instance.
 #. *Load Balancer*: An optional ELB load balancer to use. See the ELB tutorial
    for information on how to create a load balancer.

For the purposes of this tutorial, let's assume we want to create one autoscale
group over the us-east-1a and us-east-1b availability zones. We want to have
two instances in each availability zone, thus a minimum size of 4. For now we
won't worry about scaling up or down - we'll introduce that later when we talk
about triggers. Thus we'll set a maximum size of 4 as well. We'll also associate
the AG with a load balancer which we assume we've already created, called 'my_lb'.

Our LC tells us how to start an instance. This will at least include the image
id to use, security_group, and key information. We assume the image id, key
name and security groups have already been defined elsewhere - see the EC2
tutorial for information on how to create these.

>>> from boto.ec2.autoscale import LaunchConfiguration
>>> from boto.ec2.autoscale import AutoScalingGroup
>>> lc = LaunchConfiguration(name='my-launch_config', image_id='my-ami',
                             key_name='my_key_name',
                             security_groups=['my_security_groups'])
>>> conn.create_launch_configuration(lc)

We now have created a launch configuration called 'my-launch-config'. We are now
ready to associate it with our new autoscale group.

>>> ag = AutoScalingGroup(group_name='my_group', load_balancers=['my-lb'],
                          availability_zones=['us-east-1a', 'us-east-1b'],
                          launch_config=lc, min_size=4, max_size=4)
>>> conn.create_auto_scaling_group(ag)

We now have a new autoscaling group defined! At this point instances should be
starting to launch. To view activity on an autoscale group:

>>> ag.get_activities()
 [Activity:Launching a new EC2 instance status:Successful progress:100,
  ...]

or alternatively:

>>> conn.get_all_activities(ag)

This autoscale group is fairly useful in that it will maintain the minimum size without
breaching the maximum size defined. That means if one instance crashes, the autoscale
group will use the launch configuration to start a new one in an attempt to maintain
its minimum defined size. It knows instance health using the health check defined on
its associated load balancer.

Scaling a Group Up or Down
^^^^^^^^^^^^^^^^^^^^^^^^^^
It might be more useful to also define means to scale a group up or down
depending on certain criteria. For example, if the average CPU utilization of
all your instances goes above 60%, you may want to scale up a number of
instances to deal with demand - likewise you might want to scale down if usage
drops. These criteria are defined in *triggers*.

For example, let's modify our above group to have a maxsize of 8 and define means
of scaling up based on CPU utilization. We'll say we should scale up if the average
CPU usage goes above 80% and scale down if it goes below 40%.

>>> from boto.ec2.autoscale import Trigger
>>> tr = Trigger(name='my_trigger', autoscale_group=ag,
             measure_name='CPUUtilization', statistic='Average',
             unit='Percent',
             dimensions=[('AutoScalingGroupName', ag.name)],
             period=60, lower_threshold=40,
             lower_breach_scale_increment='-5',
             upper_threshold=80,
             upper_breach_scale_increment='10',
             breach_duration=360)
>> conn.create_trigger(tr)

