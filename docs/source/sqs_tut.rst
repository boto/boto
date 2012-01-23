.. _sqs_tut:

=======================================
An Introduction to boto's SQS interface
=======================================

This tutorial focuses on the boto interface to the Simple Queue Service
from Amazon Web Services.  This tutorial assumes that you have boto already
downloaded and installed.

Creating a Connection
---------------------
The first step in accessing SQS is to create a connection to the service.
There are two ways to do this in boto.  The first is::

    >>> from boto.sqs.connection import SQSConnection
    >>> conn = SQSConnection('<aws access key>', '<aws secret key>')

At this point the variable conn will point to an SQSConnection object. Bear in mind that
just as any other AWS service SQS is region-specfic. Also important to note is that by default,
if no region is provided, it'll connect to the US-EAST-1 region. In
this example, the AWS access key and AWS secret key are passed in to the
method explicitely.  Alternatively, you can set the environment variables:

AWS_ACCESS_KEY_ID - Your AWS Access Key ID
AWS_SECRET_ACCESS_KEY - Your AWS Secret Access Key

and then call the constructor without any arguments, like this::

    >>> conn = SQSConnection()

There is also a shortcut function in the boto package, called connect_sqs
that may provide a slightly easier means of creating a connection::

    >>> import boto
    >>> conn = boto.connect_sqs()

In either case, conn will point to an SQSConnection object which we will
use throughout the remainder of this tutorial.

Creating a Queue
----------------
Once you have a connection established with SQS, you will probably want to
create a queue.  In its simplest form, that can be accomplished as follows::

    >>> q = conn.create_queue('myqueue')

The create_queue method will create (and return) the requested queue if it does not
exist or will return the existing queue if it does.  There is an
optional parameter to create_queue called visibility_timeout.  This basically
controls how long a message will remain invisible to other queue readers
once it has been read (see SQS documentation for more detailed explanation).
If this is not explicitly specified the queue will be created with whatever
default value SQS provides (currently 30 seconds).  If you would like to
specify another value, you could do so like this::

    >>> q = conn.create_queue('myqueue', 120)

This would establish a default visibility timeout for this queue of 120
seconds.  As you will see later on, this default value for the queue can
also be overridden each time a message is read from the queue.  If you want
to check what the default visibility timeout is for a queue::

    >>> q.get_timeout()
    30

Listing all Queues
------------------

To retrieve a list of the queues for your account in the current region::

    >>> conn.get_all_queues()
    [
        Queue(https://queue.amazonaws.com/411358162645/myqueue),
        Queue(https://queue.amazonaws.com/411358162645/another_queue),
        Queue(https://queue.amazonaws.com/411358162645/another_queue2)
    ]

This will leave you with a list of all of your :py:class:`boto.sqs.queue.Queue`
instances. Alternatively, if you wanted to only list the queues that started
with ``'another'``::

    >>> conn.get_all_queues(prefix='another')
    [
        Queue(https://queue.amazonaws.com/411358162645/another_queue),
        Queue(https://queue.amazonaws.com/411358162645/another_queue2)
    ]

Getting a Queue (by name)
-----------------------
If you wish to explicitly retrieve an existing queue and the name of the queue is known, 
you can retrieve the queue as follows::

    >>> my_queue = conn.get_queue('myqueue')
    Queue(https://queue.amazonaws.com/411358162645/myqueue)

This leaves you with a single :py:class:`boto.sqs.queue.Queue`, which abstracts
the SQS Queue named 'myqueue'.

Writing Messages
----------------
Once you have a queue setup, presumably you will want to write some messages
to it.  SQS doesn't care what kind of information you store in your messages
or what format you use to store it.  As long as the amount of data per
message is less than or equal to 256Kb, SQS won't complain.

So, first we need to create a Message object::

>>> from boto.sqs.message import Message
>>> m = Message()
>>> m.set_body('This is my first message.')
>>> status = q.write(m)

The write method returns a True if everything went well.  If the write
didn't succeed it will either return a False (meaning SQS simply chose
not to write the message for some reason) or an exception if there was
some sort of problem with the request.

Writing Messages (Custom Format)
--------------------------------
The technique above will work only if you use boto's default Message payload format;
however, you may have a lot of specific requirements around the format of
the message data.  For example, you may want to store one big string or you might
want to store something that looks more like RFC822 messages or you might want
to store a binary payload such as pickled Python objects.

The way boto deals with this issue is to define a simple Message object that
treats the message data as one big string which you can set and get.  If that
Message object meets your needs, you're good to go.  However, if you need to
incorporate different behavior in your message or handle different types of
data you can create your own Message class.  You just need to register that
class with the boto queue object so that it knows that, when you read a message from the
queue, it should create one of your message objects rather than the
default boto Message object.  To register your message class, you would::

>>> import MyMessage
>>> q.set_message_class(MyMessage)
>>> m = MyMessage()
>>> m.set_body('This is my first message.')
>>> status = q.write(m)

where MyMessage is the class definition for your message class.  Your
message class should subclass the boto Message because there is a small
bit of Python magic happening in the __setattr__ method of the boto Message
class.

Reading Messages
----------------

So, now we have a message in our queue.  How would we go about reading it?
Here's one way:

>>> rs = q.get_messages()
>>> len(rs)
1
>>> m = rs[0]
>>> m.get_body()
u'This is my first message'

The get_messages method also returns a ResultSet object as described
above.  In addition to the special attributes that we already talked
about the ResultSet object also contains any results returned by the
request.  To get at the results you can treat the ResultSet as a
sequence object (e.g. a list).  We can check the length (how many results)
and access particular items within the list using the slice notation
familiar to Python programmers.

At this point, we have read the message from the queue and SQS will make
sure that this message remains invisible to other readers of the queue
until the visibility timeout period for the queue expires.  If you delete
the message before the timeout period expires then no one else will ever see
the message again.  However, if you don't delete it (maybe because your reader crashed
or failed in some way, for example) it will magically reappear in my queue
for someone else to read.  If you aren't happy with the default visibility
timeout defined for the queue, you can override it when you read a message:

>>> q.get_messages(visibility_timeout=60)

This means that regardless of what the default visibility timeout is for
the queue, this message will remain invisible to other readers for 60
seconds.

The get_messages method can also return more than a single message.  By
passing a num_messages parameter (defaults to 1) you can control the maximum
number of messages that will be returned by the method.  To show this
feature off, first let's load up a few more messages.

>>> for i in range(1, 11):
...   m = Message()
...   m.set_body('This is message %d' % i)
...   q.write(m)
...
>>> rs = q.get_messages(10)
>>> len(rs)
10

Don't be alarmed if the length of the result set returned by the get_messages
call is less than 10.  Sometimes it takes some time for new messages to become
visible in the queue.  Give it a minute or two and they will all show up.

If you want a slightly simpler way to read messages from a queue, you
can use the read method.  It will either return the message read or
it will return None if no messages were available.  You can also pass
a visibility_timeout parameter to read, if you desire:

>>> m = q.read(60)
>>> m.get_body()
u'This is my first message'

Deleting Messages and Queues
----------------------------
As stated above, messages are never deleted by the queue unless explicitly told to do so. 
To remove a message from a queue:

>>> q.delete_message(m)
[]

If I want to delete the entire queue, I would use:

>>> conn.delete_queue(q)

However, and this is a good safe guard, this won't succeed unless the queue is empty.

Additional Information
----------------------
The above tutorial covers the basic operations of creating queues, writing messages,
reading messages, deleting messages, and deleting queues.  There are a
few utility methods in boto that might be useful as well.  For example,
to count the number of messages in a queue:

>>> q.count()
10

This can be handy but is command as well as the other two utility methods
I'll describe in a minute are inefficient and should be used with caution
on queues with lots of messages (e.g. many hundreds or more).  Similarly,
you can clear (delete) all messages in a queue with:

>>> q.clear()

Be REAL careful with that one!  Finally, if you want to dump all of the
messages in a queue to a local file:

>>> q.dump('messages.txt', sep='\n------------------\n')

This will read all of the messages in the queue and write the bodies of
each of the messages to the file messages.txt.  The option sep argument
is a separator that will be printed between each message body in the file.
