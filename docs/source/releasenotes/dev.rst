boto v2.xx.x
============

:date: 2013/xx/xx

This release adds support for VPC within AWS Opsworks, ....


Features
--------

* Added support for VPC within Opsworks. (:sha:`56e1df3`)


Bugfixes
--------

* Fixed EC2's ``associate_public_ip`` to work correctly. (:sha:`9db6101`)
* Fixed a bug with ``dynamodb_load`` when working with sets. (:issue:`1664`,
  :sha:`ef2d28b`)
* Several documentation improvements/fixes:

    * Added Opsworks docs to the index. (:sha:`5d48763`)
    * Added docs on the correct string values for ``get_all_images``.
      (:issue:`1674`, :sha:`1e4ed2e`)
