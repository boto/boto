.. _route53_tut.rst:

===========================================
An Introduction to boto's Route53 interface
===========================================

This tutorial focuses on the boto interface to Route53 from Amazon Web
Services.  This tutorial assumes that you have already downloaded and installed
boto.

Route53 is a Domain Name System (DNS) web service. It can be used to route
requests to services running on AWS such as EC2 instances or load balancers, as
well as to external services. Route53 also allows you to have automated checks
to send requests where you require them.

In this tutorial, we will be setting up our services for *example.com*.

Creating a connection
---------------------

To start using Route53 you will need to create a connection to the service as
normal:

>>> import boto.route53
>>> conn = boto.route53.connect_to_region('us-west-2')

You will be using this conn object for the remainder of the tutorial to send
commands to Route53.

Working with domain names
-------------------------

You can manipulate domains through a zone object. For example, you can create a
domain name:

>>> zone = conn.create_zone("example.com.")

Note that trailing dot on that domain name is significant. This is known as a
fully qualified domain name (`FQDN <http://en.wikipedia.org/wiki/Fully_qualified_domain_name>`_).

>>> zone
<Zone:example.com.>

You can also retrieve all your domain names:

>>> conn.get_zones()
[<Zone:example.com.>]

Or you can retrieve a single domain:

>>> conn.get_zone("example.com.")
<Zone:example.com.>

Finally, you can retrieve the list of nameservers that AWS has setup for this
domain name as follows:

>>> zone.get_nameservers()
[u'ns-1000.awsdns-42.org.', u'ns-1001.awsdns-30.com.', u'ns-1002.awsdns-59.net.', u'ns-1003.awsdns-09.co.uk.']

Once you have finished configuring your domain name, you will need to change
your nameservers at your registrar to point to those nameservers for Route53 to
work.

Setting up dumb records
-----------------------

You can also add, update and delete records on a zone:

>>> status = a.add_record("MX", "example.com.", "10 mail.isp.com")

When you send a change request through, the status of the update will be
*PENDING*:

>>> status
<Status:PENDING>

You can call the API again and ask for the current status as follows:

>>> status.update()
'INSYNC'

>>> status
<Status:INSYNC>

When the status has changed to *INSYNC*, the change has been propagated to
remote servers

