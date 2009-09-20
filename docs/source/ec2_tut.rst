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
There are two ways to do this in boto.  The first is:

>>> from boto.ec2.connection import EC2Connection
>>> conn = EC2Connection('<aws access key>', '<aws secret key>')

At this point the variable conn will point to an EC2Connection object.  In
this example, the AWS access key and AWS secret key are passed in to the
method explicitely.  Alternatively, you can set the environment variables:

AWS_ACCESS_KEY_ID - Your AWS Access Key ID
AWS_SECRET_ACCESS_KEY - Your AWS Secret Access Key

and then call the constructor without any arguments, like this:

>>> conn = EC2Connection()

There is also a shortcut function in the boto package, called connect_ec2
that may provide a slightly easier means of creating a connection:

>>> import boto
>>> conn = boto.connect_ec2()

In either case, conn will point to an EC2Connection object which we will
use throughout the remainder of this tutorial.

A Note About Regions
--------------------
The 2008-12-01 version of the EC2 API introduced the idea of Regions.
A Region is geographically distinct and is completely isolated from
other EC2 Regions.  At the time of the launch of the 2008-12-01 API
there were two available regions, us-east-1 and eu-west-1.  Each
Region has it's own service endpoint and therefore would require
it's own EC2Connection object in boto.

The default behavior in boto, as shown above, is to connect you with
the us-east-1 region which is exactly the same as the behavior prior
to the introduction of Regions.

However, if you would like to connect to a region other than us-east-1,
there are a couple of ways to accomplish that.  The first way, is to
as EC2 to provide a list of currently supported regions.  You can do
that using the regions function in the boto.ec2 module:

>>> import boto.ec2
>>> regions = boto.ec2.regions()
>>> regions
[RegionInfo:eu-west-1, RegionInfo:us-east-1]
>>> 

As you can see, a list of available regions is returned.  Each region
is represented by a RegionInfo object.  A RegionInfo object has two
attributes; a name and an endpoint.

>>> eu = regions[0]
>>> eu.name
u'eu-west-1'
>>> eu.endpoint
u'eu-west-1.ec2.amazonaws.com'
>>>

You can easily create a connection to a region by using the connect
method of the RegionInfo object:

>>> conn_eu = eu.connect()
>>> conn_eu
<boto.ec2.connection.EC2Connection instance at 0xccaaa8>
>>> 

The variable conn_eu is now bound to an EC2Connection object connected
to the endpoint of the eu-west-1 region and all operations performed via
that connection and all objects created by that connection will be scoped
to the eu-west-1 region.  You can always tell which region a connection
is associated with by accessing it's region attribute:

>>> conn_eu.region
RegionInfo:eu-west-1
>>>

Supporting EC2 objects such as SecurityGroups, KeyPairs, Addresses,
Volumes, Images and SnapShots are local to a particular region.  So
don't expect to find the security groups you created in the us-east-1
region to be available in the eu-west-1 region.

Some objects in boto, such as SecurityGroup, have a new method called
copy_to_region which will attempt to create a copy of the object in
another region.  For example:

>>> regions
[RegionInfo:eu-west-1, RegionInfo:us-east-1]
>>> conn_us = regions[1].connect()
>>> groups = conn_us.get_all_security_groups()
>>> groups
[SecurityGroup:alfresco, SecurityGroup:apache, SecurityGroup:vnc,
SecurityGroup:appserver2, SecurityGroup:FTP, SecurityGroup:webserver,
SecurityGroup:default, SecurityGroup:test-1228851996]
>>> us_group = groups[0]
>>> us_group
SecurityGroup:alfresco
>>> us_group.rules
[IPPermissions:tcp(22-22), IPPermissions:tcp(80-80), IPPermissions:tcp(1445-1445)]
>>> eu_group = us_group.copy_to_region(eu)
>>> eu_group.rules
[IPPermissions:tcp(22-22), IPPermissions:tcp(80-80), IPPermissions:tcp(1445-1445)]

In the above example, we chose one of the security groups available
in the us-east-1 region (the group alfresco) and copied that security
group to the eu-west-1 region.  All of the rules associated with the
original security group will be copied as well.

If you would like your default region to be something other than
us-east-1, you can override that default in your boto config file
(either ~/.boto for personal settings or /etc/boto.cfg for system-wide
settings).  For example:

[Boto]
ec2_region_name = eu-west-1
ec2_region_endpoint = eu-west-1.ec2.amazonaws.com

The above lines added to either boto config file would set the default
region to be eu-west-1.

Images & Instances
------------------

An Image object represents an Amazon Machine Image (AMI) which is an
encrypted machine image stored in Amazon S3.  It contains all of the
information necessary to boot instances of your software in EC2.

To get a listing of all available Images:

>>> images = conn.get_all_images()
>>> images
[Image:ami-20b65349, Image:ami-22b6534b, Image:ami-23b6534a, Image:ami-25b6534c, Image:ami-26b6534f, Image:ami-2bb65342, Image:ami-78b15411, Image:ami-a4aa4fcd, Image:ami-c3b550aa, Image:ami-e4b6538d, Image:ami-f1b05598]
>>> for image in images:
...    print image.location
ec2-public-images/fedora-core4-base.manifest.xml
ec2-public-images/fedora-core4-mysql.manifest.xml
ec2-public-images/fedora-core4-apache.manifest.xml
ec2-public-images/fedora-core4-apache-mysql.manifest.xml
ec2-public-images/developer-image.manifest.xml
ec2-public-images/getting-started.manifest.xml
marcins_cool_public_images/fedora-core-6.manifest.xml
khaz_fc6_win2003/image.manifest
aes-images/django.manifest
marcins_cool_public_images/ubuntu-6.10.manifest.xml
ckk_public_ec2_images/centos-base-4.4.manifest.xml

The most useful thing you can do with an Image is to actually run it, so let's
run a new instance of the base Fedora image:

>>> image = images[0]
>>> image.location
ec2-public-images/fedora-core4-base.manifest.xml
>>> reservation = image.run()

This will begin the boot process for a new EC2 instance.  The run method
returns a Reservation object which represents a collection of instances
that are all started at the same time.  In this case, we only started one
but you can check the instances attribute of the Reservation object to see
all of the instances associated with this reservation:

>>> reservation.instances
[Instance:i-6761850e]
>>> instance = reservation.instances[0]
>>> instance.state
u'pending'
>>>

So, we have an instance booting up that is still in the pending state.  We
can call the update method on the instance to get a refreshed view of it's
state:

>>> instance.update()
>>> instance.state
u'pending'
>>> # wait a few minutes
>>> instance.update()
>>> instance.state
u'running'

So, now our instance is running.  The time it takes to boot a new instance
varies based on a number of different factors but usually it takes less than
five minutes.

Now the instance is up and running you can find out its DNS name like this:

>>> instance.dns_name
u'ec2-72-44-40-153.z-2.compute-1.amazonaws.com'

This provides the public DNS name for your instance.  Since the 2007--3-22
release of the EC2 service, the default addressing scheme for instances
uses NAT-addresses which means your instance has both a public IP address and a
non-routable private IP address.  You can access each of these addresses
like this:

>>> instance.public_dns_name
u'ec2-72-44-40-153.z-2.compute-1.amazonaws.com'
>>> instance.private_dns_name
u'domU-12-31-35-00-42-33.z-2.compute-1.internal'

Even though your instance has a public DNS name, you won't be able to
access it yet because you need to set up some security rules which are
described later in this tutorial.

Since you are now being charged for that instance we just created, you will
probably want to know how to terminate the instance, as well.  The simplest
way is to use the stop method of the Instance object:

>>> instance.stop()
>>> instance.update()
>>> instance.state
u'shutting-down'
>>> # wait a minute
>>> instance.update()
>>> instance.state
u'terminated'
>>>

When we created our new instance, we didn't pass any args to the run method
so we got all of the default values.  The full set of possible parameters
to the run method are:

min_count - The minimum number of instances to launch.
max_count - The maximum number of instances to launch.
keypair - Keypair to launch instances with (either a KeyPair object or a string with the name of the desired keypair.
security_groups - A list of security groups to associate with the instance.  This can either be a list of SecurityGroup objects or a list of strings with the names of the desired security groups.
user_data - Data to be made available to the launched instances.  This should be base64 encoded according to the EC2 documentation.

So, if I wanted to create two instances of the base image and launch them
with my keypair, called gsg-keypair, I would to this:

>>> reservation.image.run(2,2,'gsg-keypair')
>>> reservation.instances
[Instance:i-5f618536, Instance:i-5e618537]
>>> for i in reservation.instances:
...    print i.status
u'pending'
u'pending'
>>>

Later, when you are finished with the instances you can either stop each
individually or you can call the stop_all method on the Reservation object:

>>> reservation.stop_all()
>>>

If you just want to get a list of all of your running instances, use
the get_all_instances method of the connection object.  Note that the
list returned is actually a list of Reservation objects (which contain
the Instances) and that the list may include recently terminated instances
for a small period of time subsequent to their termination.

>>> instances = conn.get_all_instances()
>>> instances
[Reservation:r-a76085ce, Reservation:r-a66085cf, Reservation:r-8c6085e5]
>>> r = instances[0]
>>> for inst in r.instances:
...    print inst.state
u'terminated'
>>>

A recent addition to the EC2 api's is to allow other EC2 users to launch
your images.  There are a couple of ways of accessing this capability in
boto but I'll show you the simplest way here.  First of all, you need to
know the Amazon ID for the user in question.  The Amazon Id is a twelve
digit number that appears on your Account Activity page at AWS.  It looks
like this:

1234-5678-9012

To use this number in API calls, you need to remove the dashes so in our
example the user ID would be 12345678912.  To allow the user associated
with this ID to launch one of your images, let's assume that the variable
image represents the Image you want to share.  So:

>>> image.get_launch_permissions()
{}
>>>

The get_launch_permissions method returns a dictionary object two possible
entries; user_ids or groups.  In our case we haven't yet given anyone
permission to launch our image so the dictionary is empty.  To add our
EC2 user:

>>> image.set_launch_permissions(['123456789012'])
True
>>> image.get_launch_permissions()
{'user_ids': [u'123456789012']}
>>>

We have now added the desired user to the launch permissions for the Image
so that user will now be able to access and launch our Image.  You can add
multiple users at one time by adding them all to the list you pass in as
a parameter to the method.  To revoke the user's launch permissions:

>>> image.remove_launch_permissions(['123456789012'])
True
>>> image.get_launch_permissions()
{}
>>>

It is possible to pass a list of group names to the set_launch_permissions
method, as well.  The only group available at the moment is the group "all"
which would allow any valid EC2 user to launch your image.

Finally, you can completely reset the launch permissions for an Image with:

>>> image.reset_launch_permissions()
True
>>>

This will remove all users and groups from the launch permission list and
makes the Image private, again.

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







