.. cloudsearch_tut:

===============================================
An Introduction to boto's Cloudsearch interface
===============================================

This tutorial focuses on the boto interface to AWS' Cloudsearch_. This tutorial
assumes that you have boto already downloaded and installed.

.. _Cloudsearch: http://aws.amazon.com/cloudsearch/

Creating a Domain
-----------------

    >>> import boto

    >>> our_ip = '192.168.1.0'

    >>> conn = boto.connect_cloudsearch()
    >>> domain = conn.create_domain('demo')

    >>> # Allow our IP address to access the document and search services
    >>> policy = domain.get_access_policies()
    >>> policy.allow_search_ip(our_ip)
    >>> policy.allow_doc_ip(our_ip)

    >>> # Create an 'text' index field called 'username'
    >>> uname_field = domain.create_index_field('username', 'text')
    
    >>> # But it would be neat to drill down into different countries    
    >>> loc_field = domain.create_index_field('location', 'text', facet=True)
    
    >>> # Epoch time of when the user last did something
    >>> time_field = domain.create_index_field('last_activity', 'uint', default=0)
    
    >>> follower_field = domain.create_index_field('follower_count', 'uint', default=0)

    >>> domain.create_rank_expression('recently_active', 'last_activity')  # We'll want to be able to just show the most recently active users
    
    >>> domain.create_rank_expression('activish', 'text_relevance + ((follower_count/(time() - last_activity))*1000)')  # Let's get trickier and combine text relevance with a really dynamic expression

Viewing and Adjusting Stemming for a Domain
--------------------------------------------

A stemming dictionary maps related words to a common stem. A stem is
typically the root or base word from which variants are derived. For
example, run is the stem of running and ran. During indexing, Amazon
CloudSearch uses the stemming dictionary when it performs
text-processing on text fields. At search time, the stemming
dictionary is used to perform text-processing on the search
request. This enables matching on variants of a word. For example, if
you map the term running to the stem run and then search for running,
the request matches documents that contain run as well as running.

To get the current stemming dictionary defined for a domain, use the
``get_stemming`` method of the Domain object.

    >>> stems = domain.get_stemming()
    >>> stems
    {u'stems': {}}
    >>>

This returns a dictionary object that can be manipulated directly to
add additional stems for your search domain by adding pairs of term:stem
to the stems dictionary.

    >>> stems['stems']['running'] = 'run'
    >>> stems['stems']['ran'] = 'run'
    >>> stems
    {u'stems': {u'ran': u'run', u'running': u'run'}}
    >>>

This has changed the value locally.  To update the information in
Amazon CloudSearch, you need to save the data.

    >>> stems.save()

You can also access certain CloudSearch-specific attributes related to
the stemming dictionary defined for your domain.

    >>> stems.status
    u'RequiresIndexDocuments'
    >>> stems.creation_date
    u'2012-05-01T12:12:32Z'
    >>> stems.update_date
    u'2012-05-01T12:12:32Z'
    >>> stems.update_version
    19
    >>>

The status indicates that, because you have changed the stems associated
with the domain, you will need to re-index the documents in the domain
before the new stems are used.

Viewing and Adjusting Stopwords for a Domain
--------------------------------------------

Stopwords are words that should typically be ignored both during
indexing and at search time because they are either insignificant or
so common that including them would result in a massive number of
matches.

To view the stopwords currently defined for your domain, use the
``get_stopwords`` method of the Domain object.

    >>> stopwords = domain.get_stopwords()
    >>> stopwords
    {u'stopwords': [u'a',
     u'an',
     u'and',
     u'are',
     u'as',
     u'at',
     u'be',
     u'but',
     u'by',
     u'for',
     u'in',
     u'is',
     u'it',
     u'of',
     u'on',
     u'or',
     u'the',
     u'to',
     u'was']}
     >>>

You can add additional stopwords by simply appending the values to the
list.

    >>> stopwords['stopwords'].append('foo')
    >>> stopwords['stopwords'].append('bar')
    >>> stopwords

Similarly, you could remove currently defined stopwords from the list.
To save the changes, use the ``save`` method.

    >>> stopwords.save()

The stopwords object has similar attributes defined above for stemming
that provide additional information about the stopwords in your domain.


Viewing and Adjusting Stopwords for a Domain
--------------------------------------------

You can configure synonyms for terms that appear in the data you are
searching. That way, if a user searches for the synonym rather than
the indexed term, the results will include documents that contain the
indexed term.

If you want two terms to match the same documents, you must define
them as synonyms of each other. For example:

    cat, feline
    feline, cat

To view the synonyms currently defined for your domain, use the
``get_synonyms`` method of the Domain object.

    >>> synonyms = domain.get_synsonyms()
    >>> synonyms
    {u'synonyms': {}}
    >>>

You can define new synonyms by adding new term:synonyms entries to the
synonyms dictionary object.

    >>> synonyms['synonyms']['cat'] = ['feline', 'kitten']
    >>> synonyms['synonyms']['dog'] = ['canine', 'puppy']

To save the changes, use the ``save`` method.

    >>> synonyms.save()

The synonyms object has similar attributes defined above for stemming
that provide additional information about the stopwords in your domain.

Adding Documents to the Index
-----------------------------

Now, we can add some documents to our new search domain.

    >>> doc_service = domain.get_document_service()

    >>> # Presumably get some users from your db of choice.
    >>> users = [
        {
            'id': 1,
            'username': 'dan',
            'last_activity': 1334252740,
            'follower_count': 20,
            'location': 'USA'
        },
        {
            'id': 2,
            'username': 'dankosaur',
            'last_activity': 1334252904,
            'follower_count': 1,
            'location': 'UK'
        },
        {
            'id': 3,
            'username': 'danielle',
            'last_activity': 1334252969,
            'follower_count': 100,
            'location': 'DE'
        },
        {
            'id': 4,
            'username': 'daniella',
            'last_activity': 1334253279,
            'follower_count': 7,
            'location': 'USA'
        }
    ]

    >>> for user in users:
    >>>     doc_service.add(user['id'], user['last_activity'], user)

    >>> result = doc_service.commit()  # Actually post the SDF to the document service

The result is an instance of `cloudsearch.CommitResponse` which will
makes the plain dictionary response a nice object (ie result.adds,
result.deletes) and raise an exception for us if all of our documents
weren't actually committed.


Searching Documents
-------------------

Now, let's try performing a search.

    >>> # Get an instance of cloudsearch.SearchServiceConnection
    >>> search_service = domain.get_search_service()

    >>> # Horray wildcard search
    >>> query = "username:'dan*'"


    >>> results = search_service.search(bq=query, rank=['-recently_active'], start=0, size=10)
    
    >>> # Results will give us back a nice cloudsearch.SearchResults object that looks as
    >>> # close as possible to pysolr.Results

    >>> print "Got %s results back." % results.hits
    >>> print "User ids are:"
    >>> for result in results:
    >>>     print result['id']


Deleting Documents
------------------

    >>> import time
    >>> from datetime import datetime

    >>> doc_service = domain.get_document_service()

    >>> # Again we'll cheat and use the current epoch time as our version number
     
    >>> doc_service.delete(4, int(time.mktime(datetime.utcnow().timetuple())))
    >>> service.commit()
