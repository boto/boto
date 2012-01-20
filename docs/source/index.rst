.. _index:

===============================================
boto: A Python interface to Amazon Web Services
===============================================

An integrated interface to current and future infrastructural services
offered by `Amazon Web Services`_.

.. _Amazon Web Services: http://aws.amazon.com/

Currently Supported Services
----------------------------

* **Compute**

  * :doc:`Elastic Compute Cloud (EC2) <ec2_tut>` -- (:doc:`API Reference <ref/ec2>`)
  * :doc:`Elastic MapReduce (EMR) <emr_tut>` -- (:doc:`API Reference <ref/emr>`)
  * :doc:`Auto Scaling <autoscale_tut>`

* **Content Delivery**

  * :doc:`CloudFront <cloudfront_tut>` -- (:doc:`API Reference <ref/cloudfront>`)

* **Database**

  * SimpleDB -- (:doc:`API Reference <ref/sdb>`)
  * DynamoDB -- (:doc:`API Reference <ref/dynamodb>`)
  * Relational Data Services (RDS) -- (:doc:`API Reference <ref/rds>`)

* **Deployment and Management**

  * CloudFormation -- (:doc:`API Reference <ref/cloudformation>`)

* **Identity & Access**

  * Identity and Access Management (IAM) -- (:doc:`API Reference <ref/iam>`)

* **Messaging**

  * :doc:`Simple Queue Service (SQS) <sqs_tut>` -- (:doc:`API Reference <ref/sqs>`)
  * Simple Notification Service (SNS) -- (:doc:`API Reference <ref/sns>`)
  * Simple Email Service (SES) -- (:doc:`API Reference <ref/ses>`)

* **Monitoring**

  * CloudWatch -- (API Reference coming soon)

* **Networking**

  * Route 53 -- (:doc:`API Reference <ref/route53>`)
  * :doc:`Virtual Private Cloud (VPC) <vpc_tut>` -- (:doc:`API Reference <ref/vpc>`)
  * :doc:`Elastic Load Balancing (ELB) <elb_tut>` -- (:ref:`API Reference <ref-ec2-elb>`)

* **Payments & Billing**

  * Flexible Payments Service (FPS) -- (:doc:`API Reference <ref/fps>`)

* **Storage**

  * :doc:`Simple Storage Service (S3) <s3_tut>` -- (:doc:`API Reference <ref/s3>`)

* **Workforce**

  * Mechanical Turk -- (:doc:`API Reference <ref/mturk>`)

Additional Resources
--------------------

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

.. toctree::
   :hidden:

   ec2_tut
   ref/ec2
   emr_tut
   ref/emr
   autoscale_tut
   cloudfront_tut
   ref/cloudfront
   ref/sdb
   ref/rds
   ref/cloudformation
   ref/iam
   sqs_tut
   ref/sqs
   ref/sns
   ref/ses
   ref/route53
   vpc_tut
   ref/vpc
   elb_tut
   ref/fps
   s3_tut
   ref/s3
   ref/mturk

   ref/index
   documentation


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

