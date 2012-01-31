# boto
boto 2.2.0
31-Jan-2012

## Introduction

Boto is a Python package that provides interfaces to Amazon Web Services.
At the moment, boto supports:

 * Simple Storage Service (S3)
 * SimpleQueue Service (SQS)
 * Elastic Compute Cloud (EC2)
 * Mechanical Turk
 * SimpleDB
 * CloudFront
 * CloudWatch
 * AutoScale
 * Elastic Load Balancer (ELB)
 * Virtual Private Cloud (VPC)
 * Elastic Map Reduce (EMR)
 * Relational Data Service (RDS) 
 * Simple Notification Server (SNS)
 * Google Storage
 * Identity and Access Management (IAM)
 * Route53 DNS Service (route53)
 * Simple Email Service (SES)
 * Flexible Payment Service (FPS)
 * CloudFormation
 * Amazon DynamoDB

The goal of boto is to support the full breadth and depth of Amazon
Web Services.  In addition, boto provides support for other public
services such as Google Storage in addition to private cloud systems
like Eucalyptus, OpenStack and Open Nebula.

Boto is developed mainly using Python 2.6.6 and Python 2.7.1 on Mac OSX
and Ubuntu Maverick.  It is known to work on other Linux distributions
and on Windows.  Boto requires no additional libraries or packages
other than those that are distributed with Python.  Efforts are made
to keep boto compatible with Python 2.5.x but no guarantees are made.

## Finding Out More About Boto

The main source code repository for boto can be found on
[github.com](http://github.com/boto/boto)

[Online documentation](http://readthedocs.org/docs/boto/) is also
available.  The online documentation includes full API documentation
as well as Getting Started Guides for many of the boto modules.

Boto releases can be found on the [Google Project
page](http://code.google.com/p/boto/downloads/list) or on the [Python
Cheese Shop](http://pypi.python.org/).

Join our `IRC channel`_ (#boto on FreeNode).
    IRC channel: http://webchat.freenode.net/?channels=boto

## Getting Started with Boto

Your credentials can be passed into the methods that create 
connections.  Alternatively, boto will check for the existance of the
following environment variables to ascertain your credentials:

AWS_ACCESS_KEY_ID - Your AWS Access Key ID
AWS_SECRET_ACCESS_KEY - Your AWS Secret Access Key

Credentials and other boto-related settings can also be stored in a
boto config file.  See
[this](http://code.google.com/p/boto/wiki/BotoConfig) for details.

Copyright (c) 2006-2011 Mitch Garnaat <mitch@garnaat.com>
Copyright (c) 2010-2011, Eucalyptus Systems, Inc.
All rights reserved.
