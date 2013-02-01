####
boto
####
boto 2.8.0
31-Jan-2013

.. image:: https://secure.travis-ci.org/boto/boto.png?branch=develop
        :target: https://secure.travis-ci.org/boto/boto

************
Introduction
************

Boto is a Python package that provides interfaces to Amazon Web Services.
At the moment, boto supports:

* Compute

  * Amazon Elastic Compute Cloud (EC2)
  * Amazon Elastic Map Reduce (EMR)
  * AutoScaling

* Content Delivery

  * Amazon CloudFront

* Database

  * Amazon Relational Data Service (RDS)
  * Amazon DynamoDB
  * Amazon SimpleDB
  * Amazon ElastiCache

* Deployment and Management

  * AWS Elastic Beanstalk
  * AWS CloudFormation
  * AWS Data Pipeline

* Identity & Access

  * AWS Identity and Access Management (IAM)

* Application Services

  * Amazon CloudSearch
  * Amazon Simple Workflow Service (SWF)
  * Amazon Simple Queue Service (SQS)
  * Amazon Simple Notification Server (SNS)
  * Amazon Simple Email Service (SES)

* Montoring

  * Amazon CloudWatch

* Networking

  * Amazon Route53
  * Amazon Virtual Private Cloud (VPC)
  * Elastic Load Balancing (ELB)

* Payments and Billing

  * Amazon Flexible Payment Service (FPS)

* Storage

  * Amazon Simple Storage Service (S3)
  * Amazon Glacier
  * Amazon Elastic Block Store (EBS)
  * Google Cloud Storage

* Workforce

  * Amazon Mechanical Turk

* Other

  * Marketplace Web Services

The goal of boto is to support the full breadth and depth of Amazon
Web Services.  In addition, boto provides support for other public
services such as Google Storage in addition to private cloud systems
like Eucalyptus, OpenStack and Open Nebula.

Boto is developed mainly using Python 2.6.6 and Python 2.7.1 on Mac OSX
and Ubuntu Maverick.  It is known to work on other Linux distributions
and on Windows.  Boto requires no additional libraries or packages
other than those that are distributed with Python.  Efforts are made
to keep boto compatible with Python 2.5.x but no guarantees are made.

************
Installation
************

Install via `pip`_:

::

	$ pip install boto

Install from source:

::

	$ git clone git://github.com/boto/boto.git
	$ cd boto
	$ python setup.py install

**********
ChangeLogs
**********

To see what has changed over time in boto, you can check out the
`release notes`_ in the wiki.

***************************
Finding Out More About Boto
***************************

The main source code repository for boto can be found on `github.com`_.
The boto project uses the `gitflow`_ model for branching.

`Online documentation`_ is also available. The online documentation includes
full API documentation as well as Getting Started Guides for many of the boto
modules.

Boto releases can be found on the `Python Cheese Shop`_.

Join our IRC channel `#boto` on FreeNode.
Webchat IRC channel: http://webchat.freenode.net/?channels=boto

Join the `boto-users Google Group`_.

*************************
Getting Started with Boto
*************************

Your credentials can be passed into the methods that create
connections.  Alternatively, boto will check for the existance of the
following environment variables to ascertain your credentials:

**AWS_ACCESS_KEY_ID** - Your AWS Access Key ID

**AWS_SECRET_ACCESS_KEY** - Your AWS Secret Access Key

Credentials and other boto-related settings can also be stored in a
boto config file.  See `this`_ for details.

Copyright (c) 2006-2012 Mitch Garnaat <mitch@garnaat.com>
Copyright (c) 2010-2011, Eucalyptus Systems, Inc.
Copyright (c) 2012 Amazon.com, Inc. or its affiliates.
All rights reserved.

.. _pip: http://www.pip-installer.org/
.. _release notes: https://github.com/boto/boto/wiki
.. _github.com: http://github.com/boto/boto
.. _Online documentation: http://docs.pythonboto.org
.. _Python Cheese Shop: http://pypi.python.org/pypi/boto
.. _this: http://code.google.com/p/boto/wiki/BotoConfig
.. _gitflow: http://nvie.com/posts/a-successful-git-branching-model/
.. _neo: https://github.com/boto/boto/tree/neo
.. _boto-users Google Group: https://groups.google.com/forum/?fromgroups#!forum/boto-users
