.. _cloudfront_tut:

==========
CloudFront
==========

This new boto module provides an interface to Amazon's Content Service,
CloudFront.

.. warning::

    This module is not well tested.  Paging of distributions is not yet
    supported. CNAME support is completely untested.  Use with caution.
    Feedback and bug reports are greatly appreciated.

Creating a CloudFront connection
--------------------------------

    >>> import boto
    >>> c = boto.connect_cloudfront()

Create a new :class:`boto.cloudfront.distribution.Distribution`::

    >>> distro = c.create_distribution(origin='mybucket.s3.amazonaws.com', enabled=False, comment='My new Distribution')
    >>> d.domain_name
    u'd2oxf3980lnb8l.cloudfront.net'
    >>> d.id
    u'ECH69MOIW7613'
    >>> d.status
    u'InProgress'
    >>> d.config.comment
    u'My new distribution'
    >>> d.config.origin
    <S3Origin: mybucket.s3.amazonaws.com>
    >>> d.config.caller_reference
    u'31b8d9cf-a623-4a28-b062-a91856fac6d0'
    >>> d.config.enabled
    False

Note that a new caller reference is created automatically, using
uuid.uuid4(). The :class:`boto.cloudfront.distribution.Distribution`,
:class:`boto.cloudfront.distribution.DistributionConfig` and
:class:`boto.cloudfront.distribution.DistributionSummary` objects are defined
in the :mod:`boto.cloudfront.distribution` module.

To get a listing of all current distributions::

    >>> rs = c.get_all_distributions()
    >>> rs
    [<boto.cloudfront.distribution.DistributionSummary instance at 0xe8d4e0>,
     <boto.cloudfront.distribution.DistributionSummary instance at 0xe8d788>]

This returns a list of :class:`boto.cloudfront.distribution.DistributionSummary`
objects. Note that paging is not yet supported! To get a
:class:`boto.cloudfront.distribution.DistributionObject` from a
:class:`boto.cloudfront.distribution.DistributionSummary` object::

    >>> ds = rs[1]
    >>> distro = ds.get_distribution()
    >>> distro.domain_name
    u'd2oxf3980lnb8l.cloudfront.net'

To change a property of a distribution object::

    >>> distro.comment
    u'My new distribution'
    >>> distro.update(comment='This is a much better comment')
    >>> distro.comment
    'This is a much better comment'

You can also enable/disable a distribution using the following
convenience methods::

    >>> distro.enable()  # just calls distro.update(enabled=True)

or

    >>> distro.disable()  # just calls distro.update(enabled=False)

The only attributes that can be updated for a Distribution are
comment, enabled and cnames.

To delete a :class:`boto.cloudfront.distribution.Distribution`::

    >>> distro.delete()