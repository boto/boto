####
boto
####
boto 2.27.0

Released: 6-March-2014

.. image:: https://travis-ci.org/boto/boto.png?branch=develop
        :target: https://travis-ci.org/boto/boto

.. image:: https://pypip.in/d/boto/badge.png
        :target: https://crate.io/packages/boto/

************
Introduction
************

Boto is a Python package that provides interfaces to Amazon Web Services.
At the moment, boto supports:

* Compute

  * Amazon Elastic Compute Cloud (EC2)
  * Amazon Elastic Map Reduce (EMR)
  * AutoScaling
  * Amazon Kinesis

* Content Delivery

  * Amazon CloudFront

* Database

  * Amazon Relational Data Service (RDS)
  * Amazon DynamoDB
  * Amazon SimpleDB
  * Amazon ElastiCache
  * Amazon Redshift

* Deployment and Management

  * AWS Elastic Beanstalk
  * AWS CloudFormation
  * AWS Data Pipeline
  * AWS Opsworks
  * AWS CloudTrail

* Identity & Access

  * AWS Identity and Access Management (IAM)

* Application Services

  * Amazon CloudSearch
  * Amazon Elastic Transcoder
  * Amazon Simple Workflow Service (SWF)
  * Amazon Simple Queue Service (SQS)
  * Amazon Simple Notification Server (SNS)
  * Amazon Simple Email Service (SES)

* Monitoring

  * Amazon CloudWatch

* Networking

  * Amazon Route53
  * Amazon Virtual Private Cloud (VPC)
  * Elastic Load Balancing (ELB)
  * AWS Direct Connect

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
  * AWS Support

The goal of boto is to support the full breadth and depth of Amazon
Web Services.  In addition, boto provides support for other public
services such as Google Storage in addition to private cloud systems
like Eucalyptus, OpenStack and Open Nebula.

Boto is developed mainly using Python 2.6.6 and Python 2.7.3 on Mac OSX
and Ubuntu Maverick.  It is known to work on other Linux distributions
and on Windows.  Most of Boto requires no additional libraries or packages
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
release notes at `http://docs.pythonboto.org/en/latest/#release-notes`

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
connections.  Alternatively, boto will check for the existence of the
following environment variables to ascertain your credentials:

**AWS_ACCESS_KEY_ID** - Your AWS Access Key ID

**AWS_SECRET_ACCESS_KEY** - Your AWS Secret Access Key

Credentials and other boto-related settings can also be stored in a
boto config file.  See `this`_ for details.

.. _pip: http://www.pip-installer.org/
.. _release notes: https://github.com/boto/boto/wiki
.. _github.com: http://github.com/boto/boto
.. _Online documentation: http://docs.pythonboto.org
.. _Python Cheese Shop: http://pypi.python.org/pypi/boto
.. _this: http://code.google.com/p/boto/wiki/BotoConfig
.. _gitflow: http://nvie.com/posts/a-successful-git-branching-model/
.. _neo: https://github.com/boto/boto/tree/neo
.. _boto-users Google Group: https://groups.google.com/forum/?fromgroups#!forum/boto-users
