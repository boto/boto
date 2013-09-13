.. _index:

===============================================
boto: A Python interface to Amazon Web Services
===============================================

An integrated interface to current and future infrastructural services
offered by `Amazon Web Services`_.

.. _Amazon Web Services: http://aws.amazon.com/

Getting Started
---------------

If you've never used ``boto`` before, you should read the
:doc:`Getting Started with Boto <getting_started>` guide to get familiar
with ``boto`` & its usage.

Currently Supported Services
----------------------------

* **Compute**

  * :doc:`Elastic Compute Cloud (EC2) <ec2_tut>` -- (:doc:`API Reference <ref/ec2>`)
  * :doc:`Elastic MapReduce (EMR) <emr_tut>` -- (:doc:`API Reference <ref/emr>`)
  * :doc:`Auto Scaling <autoscale_tut>` -- (:doc:`API Reference <ref/autoscale>`)

* **Content Delivery**

  * :doc:`CloudFront <cloudfront_tut>` -- (:doc:`API Reference <ref/cloudfront>`)

* **Database**

  * :doc:`DynamoDB2 <dynamodb2_tut>` -- (:doc:`API Reference <ref/dynamodb2>`) -- (:doc:`Migration Guide from v1 <migrations/dynamodb_v1_to_v2>`)
  * :doc:`DynamoDB <dynamodb_tut>` -- (:doc:`API Reference <ref/dynamodb>`)
  * :doc:`Relational Data Services (RDS) <rds_tut>` -- (:doc:`API Reference <ref/rds>`)
  * ElastiCache -- (:doc:`API Reference <ref/elasticache>`)
  * Redshift -- (:doc:`API Reference <ref/redshift>`)
  * :doc:`SimpleDB <simpledb_tut>` -- (:doc:`API Reference <ref/sdb>`)

* **Deployment and Management**

  * CloudFormation -- (:doc:`API Reference <ref/cloudformation>`)
  * Elastic Beanstalk -- (:doc:`API Reference <ref/beanstalk>`)
  * Data Pipeline -- (:doc:`API Reference <ref/datapipeline>`)
  * Opsworks -- (:doc:`API Reference <ref/opsworks>`)

* **Identity & Access**

  * Identity and Access Management (IAM) -- (:doc:`API Reference <ref/iam>`)
  * Security Token Service (STS) -- (:doc:`API Reference <ref/sts>`)

* **Application Services**

  * :doc:`Cloudsearch <cloudsearch_tut>` -- (:doc:`API Reference <ref/cloudsearch>`)
  * Elastic Transcoder -- (:doc:`API Reference <ref/elastictranscoder>`)
  * Simple Workflow Service (SWF) -- (:doc:`API Reference <ref/swf>`)
  * :doc:`Simple Queue Service (SQS) <sqs_tut>` -- (:doc:`API Reference <ref/sqs>`)
  * Simple Notification Service (SNS) -- (:doc:`API Reference <ref/sns>`)
  * :doc:`Simple Email Service (SES) <ses_tut>` -- (:doc:`API Reference <ref/ses>`)

* **Monitoring**

  * :doc:`CloudWatch <cloudwatch_tut>` -- (:doc:`API Reference <ref/cloudwatch>`)

* **Networking**

  * Route 53 -- (:doc:`API Reference <ref/route53>`)
  * :doc:`Virtual Private Cloud (VPC) <vpc_tut>` -- (:doc:`API Reference <ref/vpc>`)
  * :doc:`Elastic Load Balancing (ELB) <elb_tut>` -- (:doc:`API Reference <ref/elb>`)

* **Payments & Billing**

  * Flexible Payments Service (FPS) -- (:doc:`API Reference <ref/fps>`)

* **Storage**

  * :doc:`Simple Storage Service (S3) <s3_tut>` -- (:doc:`API Reference <ref/s3>`)
  * Amazon Glacier -- (:doc:`API Reference <ref/glacier>`)
  * Google Cloud Storage -- (:doc:`API Reference <ref/gs>`)

* **Workforce**

  * Mechanical Turk -- (:doc:`API Reference <ref/mturk>`)

* **Other**

  * Marketplace Web Services -- (:doc:`API Reference <ref/mws>`)
  * :doc:`Support <support_tut>` -- (:doc:`API Reference <ref/support>`)

Additional Resources
--------------------

* :doc:`Applications Built On Boto <apps_built_on_boto>`
* :doc:`Command Line Utilities <commandline>`
* :doc:`Boto Config Tutorial <boto_config_tut>`
* :doc:`Contributing to Boto <contributing>`
* `Boto Source Repository`_
* `Boto Issue Tracker`_
* `Boto Twitter`_
* `Follow Mitch on Twitter`_
* Join our `IRC channel`_ (#boto on FreeNode).

.. _Boto Issue Tracker: https://github.com/boto/boto/issues
.. _Boto Source Repository: https://github.com/boto/boto
.. _Boto Twitter: http://twitter.com/pythonboto
.. _IRC channel: http://webchat.freenode.net/?channels=boto
.. _Follow Mitch on Twitter: http://twitter.com/garnaat


Release Notes
-------------

.. toctree::
   :titlesonly:

   releasenotes/v2.12.0
   releasenotes/v2.11.0
   releasenotes/v2.10.0
   releasenotes/v2.9.9
   releasenotes/v2.9.8
   releasenotes/v2.9.7
   releasenotes/v2.9.6
   releasenotes/v2.9.5
   releasenotes/v2.9.4
   releasenotes/v2.9.3
   releasenotes/v2.9.2
   releasenotes/v2.9.1
   releasenotes/v2.9.0
   releasenotes/v2.8.0
   releasenotes/v2.7.0
   releasenotes/v2.6.0
   releasenotes/v2.5.2
   releasenotes/v2.5.1
   releasenotes/v2.5.0
   releasenotes/v2.4.0
   releasenotes/v2.3.0
   releasenotes/v2.2.2
   releasenotes/v2.2.1
   releasenotes/v2.2.0
   releasenotes/v2.1.1
   releasenotes/v2.1.0
   releasenotes/v2.0.0
   releasenotes/v2.0b1


.. toctree::
   :hidden:
   :glob:

   getting_started
   ec2_tut
   security_groups
   emr_tut
   autoscale_tut
   cloudfront_tut
   simpledb_tut
   dynamodb_tut
   rds_tut
   sqs_tut
   ses_tut
   cloudsearch_tut
   cloudwatch_tut
   vpc_tut
   elb_tut
   s3_tut
   boto_config_tut
   documentation
   contributing
   commandline
   support_tut
   dynamodb2_tut
   migrations/dynamodb_v1_to_v2
   ref/*
   releasenotes/*


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
