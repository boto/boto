.. cloudsearch_tut:

============================================
An Introduction to boto's Cloudsearch interface
============================================

This tutorial focuses on the boto interface to AWS' Cloudsearch_. This tutorial
assumes that you have boto already downloaded and installed.

.. _Cloudsearch: http://aws.amazon.com/cloudsearch/

Creating a Domain
-----------------

    import boto

    our_ip = '192.168.1.0'

    conn = boto.connect_cloudsearch()
    domain = conn.create_domain('demo')

    # Allow our IP address to access the document and search services
    policy = domain.get_access_policies()
    policy.allow_search_ip(our_ip)
    policy.allow_doc_ip(our_ip)

    # Create an 'text' index field called 'username'
    uname_field = domain.create_index_field('username', 'text')
    
    # But it would be neat to drill down into different countries    
    loc_field = domain.create_index_field('location', 'text', facet=True)
    
    # Epoch time of when the user last did something
    time_field = domain.create_index_field('last_activity', 'uint', default=0)
    
    follower_field = domain.create_index_field('follower_count', 'uint', default=0)

    domain.create_rank_expression('recently_active', 'last_activity')  # We'll want to be able to just show the most recently active users
    
    domain.create_rank_expression('activish', 'text_relevance + ((follower_count/(time() - last_activity))*1000)')  # Let's get trickier and combine text relevance with a really dynamic expression



Adding Documents to the Index
-----------------------------

Now, we can add some documents to our new search domain.

    doc_service = domain.get_document_service()

    # Presumably get some users from your db of choice.
    users = [
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

    for user in users:
        doc_service.add(user['id'], user['last_activity'], user)

    result = doc_service.commit()  # Actually post the SDF to the document service

The result is an instance of `cloudsearch.CommitResponse` which will
makes the plain dictionary response a nice object (ie result.adds,
result.deletes) and raise an exception for us if all of our documents
weren't actually committed.


Searching Documents
-------------------

Now, let's try performing a search.

    # Get an instance of cloudsearch.SearchServiceConnection
    search_service = domain.get_search_service()

    # Horray wildcard search
    query = "username:'dan*'"


    results = search_service.search(bq=query, rank=['-recently_active'], start=0, size=10)
    
    # Results will give us back a nice cloudsearch.SearchResults object that looks as
    # close as possible to pysolr.Results

    print "Got %s results back." % results.hits
    print "User ids are:"
    for result in results:
        print result['id']


Deleting Documents
------------------

    import time
    from datetime import datetime

    doc_service = domain.get_document_service()

     # Again we'll cheat and use the current epoch time as our version number
     
    doc_service.delete(4, int(time.mktime(datetime.utcnow().timetuple())))
    service.commit()
