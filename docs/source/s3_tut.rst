.. _s3_tut:

======================================
An Introduction to boto's S3 interface
======================================

This tutorial focuses on the boto interface to the Simple Storage Service
from Amazon Web Services.  This tutorial assumes that you have already
downloaded and installed boto.

Creating a Connection
---------------------
The first step in accessing S3 is to create a connection to the service.
There are two ways to do this in boto.  The first is:

>>> from boto.s3.connection import S3Connection
>>> conn = S3Connection('<aws access key>', '<aws secret key>')

At this point the variable conn will point to an S3Connection object.  In
this example, the AWS access key and AWS secret key are passed in to the
method explicitely.  Alternatively, you can set the environment variables:

AWS_ACCESS_KEY_ID - Your AWS Access Key ID
AWS_SECRET_ACCESS_KEY - Your AWS Secret Access Key

and then call the constructor without any arguments, like this:

>>> conn = S3Connection()

There is also a shortcut function in the boto package, called connect_s3
that may provide a slightly easier means of creating a connection:

>>> import boto
>>> conn = boto.connect_s3()

In either case, conn will point to an S3Connection object which we will
use throughout the remainder of this tutorial.

Creating a Bucket
-----------------

Once you have a connection established with S3, you will probably want to
create a bucket.  A bucket is a container used to store key/value pairs
in S3.  A bucket can hold an unlimited amount of data so you could potentially
have just one bucket in S3 for all of your information.  Or, you could create
separate buckets for different types of data.  You can figure all of that out
later, first let's just create a bucket.  That can be accomplished like this:

>>> bucket = conn.create_bucket('mybucket')
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
  File "boto/connection.py", line 285, in create_bucket
    raise S3CreateError(response.status, response.reason)
boto.exception.S3CreateError: S3Error[409]: Conflict

Whoa.  What happended there?  Well, the thing you have to know about
buckets is that they are kind of like domain names.  It's one flat name
space that everyone who uses S3 shares.  So, someone has already create
a bucket called "mybucket" in S3 and that means no one else can grab that
bucket name.  So, you have to come up with a name that hasn't been taken yet.
For example, something that uses a unique string as a prefix.  Your
AWS_ACCESS_KEY (NOT YOUR SECRET KEY!) could work but I'll leave it to
your imagination to come up with something.  I'll just assume that you
found an acceptable name.

The create_bucket method will create the requested bucket if it does not
exist or will return the existing bucket if it does exist.

Creating a Bucket In Another Location
-------------------------------------

The example above assumes that you want to create a bucket in the
standard US region.  However, it is possible to create buckets in
other locations.  To do so, first import the Location object from the
boto.s3.connection module, like this:

>>> from boto.s3.connection import Location
>>> dir(Location)
['DEFAULT', 'EU', 'USWest', 'APSoutheast', '__doc__', '__module__']
>>>

As you can see, the Location object defines three possible locations;
DEFAULT, EU, USWest, and APSoutheast.  By default, the location is the
empty string which is interpreted as the US Classic Region, the
original S3 region.  However, by specifying another location at the
time the bucket is created, you can instruct S3 to create the bucket
in that location.  For example:

>>> conn.create_bucket('mybucket', location=Location.EU)

will create the bucket in the EU region (assuming the name is available).

Storing Data
----------------

Once you have a bucket, presumably you will want to store some data
in it.  S3 doesn't care what kind of information you store in your objects
or what format you use to store it.  All you need is a key that is unique
within your bucket.

The Key object is used in boto to keep track of data stored in S3.  To store
new data in S3, start by creating a new Key object:

>>> from boto.s3.key import Key
>>> k = Key(bucket)
>>> k.key = 'foobar'
>>> k.set_contents_from_string('This is a test of S3')

The net effect of these statements is to create a new object in S3 with a
key of "foobar" and a value of "This is a test of S3".  To validate that
this worked, quit out of the interpreter and start it up again.  Then:

>>> import boto
>>> c = boto.connect_s3()
>>> b = c.create_bucket('mybucket') # substitute your bucket name here
>>> from boto.s3.key import Key
>>> k = Key(b)
>>> k.key = 'foobar'
>>> k.get_contents_as_string()
'This is a test of S3'

So, we can definitely store and retrieve strings.  A more interesting
example may be to store the contents of a local file in S3 and then retrieve
the contents to another local file.

>>> k = Key(b)
>>> k.key = 'myfile'
>>> k.set_contents_from_filename('foo.jpg')
>>> k.get_contents_to_filename('bar.jpg')

There are a couple of things to note about this.  When you send data to
S3 from a file or filename, boto will attempt to determine the correct
mime type for that file and send it as a Content-Type header.  The boto
package uses the standard mimetypes package in Python to do the mime type
guessing.  The other thing to note is that boto does stream the content
to and from S3 so you should be able to send and receive large files without
any problem.

Listing All Available Buckets
-----------------------------
In addition to accessing specific buckets via the create_bucket method
you can also get a list of all available buckets that you have created.

>>> rs = conn.get_all_buckets()

This returns a ResultSet object (see the SQS Tutorial for more info on
ResultSet objects).  The ResultSet can be used as a sequence or list type
object to retrieve Bucket objects.

>>> len(rs)
11
>>> for b in rs:
... print b.name
...
<listing of available buckets>
>>> b = rs[0]

Setting / Getting the Access Control List for Buckets and Keys
--------------------------------------------------------------
The S3 service provides the ability to control access to buckets and keys
within s3 via the Access Control List (ACL) associated with each object in
S3.  There are two ways to set the ACL for an object:

1. Create a custom ACL that grants specific rights to specific users.  At the
   moment, the users that are specified within grants have to be registered
   users of Amazon Web Services so this isn't as useful or as general as it
   could be.

2. Use a "canned" access control policy.  There are four canned policies
   defined:
   a. private: Owner gets FULL_CONTROL.  No one else has any access rights.
   b. public-read: Owners gets FULL_CONTROL and the anonymous principal is granted READ access.
   c. public-read-write: Owner gets FULL_CONTROL and the anonymous principal is granted READ and WRITE access.
   d. authenticated-read: Owner gets FULL_CONTROL and any principal authenticated as a registered Amazon S3 user is granted READ access.

To set a canned ACL for a bucket, use the set_acl method of the Bucket object.
The argument passed to this method must be one of the four permissable
canned policies named in the list CannedACLStrings contained in acl.py.
For example, to make a bucket readable by anyone:

>>> b.set_acl('public-read')

You can also set the ACL for Key objects, either by passing an additional
argument to the above method:

>>> b.set_acl('public-read', 'foobar')

where 'foobar' is the key of some object within the bucket b or you can
call the set_acl method of the Key object:

>>> k.set_acl('public-read')

You can also retrieve the current ACL for a Bucket or Key object using the
get_acl object.  This method parses the AccessControlPolicy response sent
by S3 and creates a set of Python objects that represent the ACL.

>>> acp = b.get_acl()
>>> acp
<boto.acl.Policy instance at 0x2e6940>
>>> acp.acl
<boto.acl.ACL instance at 0x2e69e0>
>>> acp.acl.grants
[<boto.acl.Grant instance at 0x2e6a08>]
>>> for grant in acp.acl.grants:
...   print grant.permission, grant.display_name, grant.email_address, grant.id
... 
FULL_CONTROL <boto.user.User instance at 0x2e6a30>

The Python objects representing the ACL can be found in the acl.py module
of boto.

Both the Bucket object and the Key object also provide shortcut
methods to simplify the process of granting individuals specific
access.  For example, if you want to grant an individual user READ
access to a particular object in S3 you could do the following:

>>> key = b.lookup('mykeytoshare')
>>> key.add_email_grant('READ', 'foo@bar.com')

The email address provided should be the one associated with the users
AWS account.  There is a similar method called add_user_grant that accepts the
canonical id of the user rather than the email address.

Setting/Getting Metadata Values on Key Objects
----------------------------------------------
S3 allows arbitrary user metadata to be assigned to objects within a bucket.
To take advantage of this S3 feature, you should use the set_metadata and
get_metadata methods of the Key object to set and retrieve metadata associated
with an S3 object.  For example:

>>> k = Key(b)
>>> k.key = 'has_metadata'
>>> k.set_metadata('meta1', 'This is the first metadata value')
>>> k.set_metadata('meta2', 'This is the second metadata value')
>>> k.set_contents_from_filename('foo.txt')

This code associates two metadata key/value pairs with the Key k.  To retrieve
those values later:

>>> k = b.get_key('has_metadata)
>>> k.get_metadata('meta1')
'This is the first metadata value'
>>> k.get_metadata('meta2')
'This is the second metadata value'
>>>
