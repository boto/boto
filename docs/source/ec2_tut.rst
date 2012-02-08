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

Launching Instances
-------------------

Possibly, the most important and common task you'll use EC2 for is to launch,
stop and terminate instances. In its most primitive form, you can launch an
instance as follows::

    >>> conn.run_instances('<ami-image-id>')
    
This will launch an instance in the specified region with the default parameters.
You will not be able to SSH into this machine, as it doesn't have a security
group set. See :doc:`security_groups` for details on creating one.

Now, let's say that you already have a key pair, want a specific type of
instance, and you have your :doc:`security group <security_groups>` all setup.
In this case we can use the keyword arguments to accomplish that::

    >>> conn.run_instances(
            '<ami-image-id>',
            key_name='myKey',
            instance_type='c1.xlarge',
            security_groups=['your-security-group-here'])

The main caveat with the above call is that it is possible to request an
instance type that is not compatible with the provided AMI (for example, the
instance was created for a 64-bit instance and you choose a m1.small instance_type).
For more details on the plethora of possible keyword parameters, be sure to
check out boto's :doc:`EC2 API reference <ref/ec2>`.

Stopping Instances
------------------
Once you have your instances up and running, you might wish to shut them down
if they're not in use. Please note that this will only de-allocate virtual
hardware resources (as well as instance store drives), but won't destroy your
EBS volumes -- this means you'll pay nominal provisioned EBS storage fees
even if your instance is stopped. To do this, you can do so as follows::

    >>> conn.stop_instances(instance_ids=['instance-id-1','instance-id-2', ...])

This will request a 'graceful' stop of each of the specified instances. If you
wish to request the equivalent of unplugging your instance(s), simply add
``force=True`` keyword argument to the call above. Please note that stop
instance is not allowed with Spot instances.

Terminating Instances
---------------------
Once you are completely done with your instance and wish to surrender both
virtual hardware, root EBS volume and all other underlying components
you can request instance termination. To do so you can use the call bellow::

    >>> conn.terminate_instances(instance_ids=['instance-id-1','instance-id-2', ...])

Please use with care since once you request termination for an instance there
is no turning back.

