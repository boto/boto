==============
Change history
==============

.. contents::
    :local:

.. _version-2.0:

2.0
===
:release-date: 2011-07-14

.. _v20-important:

Important Notes
---------------

* Backwards-incompatible filter changes in the latest 2011 EC2 APIs

    In the latest 2011 EC2 APIs all security groups are assigned a unique
    identifier (sg-\*).  As a consequence, some existing filters which used to take
    the group name now require the group *id* instead:

    1. *group-id* filter in DescribeInstances (ie get_all_instances())

        To filter by group name you must instead use the *group-name* filter

    2. *launch.group-id* filter in DescribeSpotInstanceRequests (ie get_all_spot_instance_requests())

        Unfortunately for now, it is *not* possible to filter spot instance
        requests by group name; the security group id *must* be used instead.

    This new security group id can be found in the *id* attribute of a boto
    SecurityGroup instance.
