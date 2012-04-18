.. cloudsearch_tut:

============================================
An Introduction to boto's Cloudsearch interface
============================================

This tutorial focuses on the boto interface to AWS' Cloudsearch_. This tutorial
assumes that you have boto already downloaded and installed.

.. _Cloudsearch: http://aws.amazon.com/cloudsearch/

Creating a Domain
-----------------

    from boto import connect_cloudsearch

    instance_ip = 'whatever'
    domain_name = 'appusers'

    conn = connect_cloudsearch(config['AWS_ACCESS_KEY_ID'], config['AWS_SECRET_ACCESS_KEY'])
    domain = conn.create_domain(domain_name)  # Config call to provision our new domain
    domain.allow_ip(instance_ip)  # Allow our instance to access the document and search services
    domain.create_index_field('username', 'text')  # We'll search for now on just username
    domain.create_index_field('location', 'text', facet=True)  # But it would be neat to drill down into different countries
    domain.create_index_field('last_activity', 'uint', default=0)  # Epoch time of when the user last did something
    domain.create_index_field('follower_count', 'uint', default=0) # How many

    domain.create_rank_expression('recently_active', 'last_activity')  # We'll want to be able to just show the most recently active users
    domain.create_rank_expression('activish', 'text_relevance + ((follower_count/(time() - last_activity))*1000)')  # Let's get trickier and combine text relevance with a really dynamic expression



Adding Documents to the Index
-----------------------------

    from boto import connect_cloudsearch
    from boto.cloudsearch import get_document_service

    endpoint = 'paste your doc service endpoint here'

    service = get_document_service(endpoint=endpoint)  # Get a new instance of cloudsearch.DocumentServiceConnection

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
            'id': 3
            'username': 'danielle',
            'last_activity': 1334252969,
            'follower_count': 100,
            'location': 'DE'
        },
        {
            'id': 4
            'username': 'daniella',
            'last_activity': 1334253279,
            'follower_count': 7,
            'location': 'USA'
        }
    ]

    # We don't want to keep track of versions on our user documents because it's weird
    # But we do have the last_activity integer which is just as good as a version number
    # since its the last time the user was modified.

    for user in users:
        service.add(user['id'], user['last_activity'], user) # Add the user document in SDF style

    result = service.commit()  # Actually post the SDF to the document service

    # result is an instance of `cloudsearch.CommitResponse` which will makes the plain dictionary response
    # a nice object (ie result.adds, result.deletes) and raise an exception for us if all of our documents
    # weren't actually committed.


Searching Documents
-------------------

    from boto import connect_cloudsearch
    from boto.cloudsearch import get_search_service

    endpoint = 'your search endpoint'

    # Get an instance of cloudsearch.SearchServiceConnection
    service = get_search_service(endpoint=endpoint)

    # Horray wildcard search
    query = "username:'dan*'"


    results = conn.search(bq=query, rank=['-recently_active'], start=0, size=10)
    # Results will give us back a nice cloudsearch.SearchResults object that looks as
    # close as possible to pysolr.Results

    print "Got %s results back." % results.hits
    print "User ids are:"
    for result in results:
        print result['id']


Deleting Documents
------------------

    from boto import connect_cloudsearch
    from boto.cloudsearch import get_document_service
    import time
    from datetime import datetime

    endpoint = 'paste your doc service endpoint here'

    service = get_document_service(endpoint=endpoint)  # Get a new instance of cloudsearch.DocumentServiceConnection

     # Again we'll cheat and use the current epoch time as our version number
    service.delete(4, int(time.mktime(datetime.utcnow().timetuple())))
    service.commit()
