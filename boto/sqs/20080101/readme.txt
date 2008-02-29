This extension provides initial support for the new SQS API (20080101).  It was contributed
by boto user cgwalters.

To use this version rather than the older version of SQS, you need to add the following
line to the [Boto] section of your /etc/boto.cfg or ~/.boto:

boto.sqs_extend = 20080101

This will allow the code in the boto.sqs.20080101 module to override the code in boto.sqs.
