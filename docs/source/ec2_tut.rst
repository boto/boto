.. _ec2_tut:

=======================================
An Introduction to boto's EC2 interface
=======================================

This tutorial focuses on the boto interface to the Elastic Compute Cloud
from Amazon Web Services.  This tutorial assumes that you have already
downloaded and installed boto.

Creating a Connection
---------------------
The first step in accessing EC2 is to create a connection to the service.
There are two ways to do this in boto.  The first is::

    >>> from boto.ec2.connection import EC2Connection
    >>> conn = EC2Connection('<AWS_ACCESS_KEY_ID>', '<AWS_SECRET_ACCESS_KEY>')

At this point the variable conn will point to an EC2Connection object.  In
this example, the AWS access key and AWS secret key are passed in to the
method explicitely.  Alternatively, you can set the boto config environment variables
and then call the constructor without any arguments, like this::

    >>> conn = EC2Connection()

There is also a shortcut function in the boto package, called connect_ec2
that may provide a slightly easier means of creating a connection::

    >>> import boto
    >>> conn = boto.connect_ec2()

In either case, conn will point to an EC2Connection object which we will
use throughout the remainder of this tutorial.

Lanching Instances
------------------
Possibly, the most important and common task you'll use EC2 for is to launch, stop and terminate instances.
In its most primitive form, you can launch an instance as follows::

    >>> conn.run_instances('<ami-image-id>')
    
This will launch an instance in the specified region with the default parameters.

Now, let's say that you already have a key pair, want a specific type of instance, and
you have your security group all setup. In this case we can use the keyword arguments to accomplish that::

    >>> conn.run_instances('<ami-image-id>',key_name='myKey', instance_type='c1.xlarge', security_groups=['public-facing'])

The main caveat with the above call is that it is possible to request an instance type that is not compatible with the 
provided AMI (for example, the instance was created for a 64-bit instance and you choose a m1.small instance_type).
For more details on the plethora of possible keyword parameters, be sure to check out boto's EC2 API documentation_
.. _documentation http://boto.cloudhackers.com/en/latest/ref/ec2.html

Stopping Instances
------------------
Once you have your instances up and running, you might wish to shut them down if they're no in use. Please note that this will only de-allocate
virtual hardware resources (as well as instance store drives), but won't destroy your EBS volumes -- this means you'll pay nominal provisioned storage fees 
even if your instance is stopped. To do this, you can do so as follows::

    >>> conn.stop_instances(instance_ids=['<instance-id-1>','<instance-id-2>'], ...)

This will request a 'graceful' stop of each of the specified instances. If you wish to request the equivalent of unplugging your instance(s),
simply add force=True keyword argument to the call above. Please note that stop instance is not allowed on Spot instances.

Terminating Instances
---------------------
Once you are completely done with your instance and with

Security Groups
----------------

Amazon defines a security group as:

"A security group is a named collection of access rules.  These access rules
 specify which ingress, i.e. incoming, network traffic should be delivered
 to your instance."

To get a listing of all currently defined security groups:

>>> rs = conn.get_all_security_groups()
>>> print rs
[SecurityGroup:appserver, SecurityGroup:default, SecurityGroup:vnc, SecurityGroup:webserver]
>>>

Each security group can have an arbitrary number of rules which represent
different network ports which are being enabled.  To find the rules for a
particular security group, use the rules attribute:

>>> sg = rs[1]
>>> sg.name
u'default'
>>> sg.rules
[IPPermissions:tcp(0-65535),
 IPPermissions:udp(0-65535),
 IPPermissions:icmp(-1--1),
 IPPermissions:tcp(22-22),
 IPPermissions:tcp(80-80)]
>>>

In addition to listing the available security groups you can also create
a new security group.  I'll follow through the "Three Tier Web Service"
example included in the EC2 Developer's Guide for an example of how to
create security groups and add rules to them.

First, let's create a group for our Apache web servers that allows HTTP
access to the world:

>>> web = conn.create_security_group('apache', 'Our Apache Group')
>>> web
SecurityGroup:apache
>>> web.authorize('tcp', 80, 80, '0.0.0.0/0')
True
>>>

The first argument is the ip protocol which can be one of; tcp, udp or icmp.
The second argument is the FromPort or the beginning port in the range, the
third argument is the ToPort or the ending port in the range and the last
argument is the CIDR IP range to authorize access to.

Next we create another group for the app servers:

>>> app = conn.create_security_group('appserver', 'The application tier')
>>>

We then want to grant access between the web server group and the app
server group.  So, rather than specifying an IP address as we did in the
last example, this time we will specify another SecurityGroup object.

>>> app.authorize(src_group=web)
True
>>>

Now, to verify that the web group now has access to the app servers, we want to
temporarily allow SSH access to the web servers from our computer.  Let's
say that our IP address is 192.168.1.130 as it is in the EC2 Developer
Guide.  To enable that access:

>>> web.authorize(ip_protocol='tcp', from_port=22, to_port=22, cidr_ip='192.168.1.130/32')
True
>>>

Now that this access is authorized, we could ssh into an instance running in
the web group and then try to telnet to specific ports on servers in the
appserver group, as shown in the EC2 Developer's Guide.  When this testing is
complete, we would want to revoke SSH access to the web server group, like this:

>>> web.rules
[IPPermissions:tcp(80-80),
 IPPermissions:tcp(22-22)]
>>> web.revoke('tcp', 22, 22, cidr_ip='192.168.1.130/32')
True
>>> web.rules
[IPPermissions:tcp(80-80)]
>>>







