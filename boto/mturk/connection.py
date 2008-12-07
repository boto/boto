# Copyright (c) 2006,2007 Mitch Garnaat http://garnaat.org/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import xml.sax
import datetime

from boto import handler
from boto.mturk.price import Price
import boto.mturk.notification
from boto.connection import AWSQueryConnection
from boto.exception import EC2ResponseError
from boto.resultset import ResultSet

class MTurkConnection(AWSQueryConnection):
    
    APIVersion = '2006-10-31'
    SignatureVersion = '1'
    
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 is_secure=False, port=None, proxy=None, proxy_port=None,
                 proxy_user=None, proxy_pass=None, host='mechanicalturk.amazonaws.com', debug=0,
                 https_connection_factory=None):
        AWSQueryConnection.__init__(self, aws_access_key_id, aws_secret_access_key,
                                    is_secure, port, proxy, proxy_port, proxy_user, proxy_pass,
                                    host, debug, https_connection_factory)
    
    def get_account_balance(self):
        """
        """
        params = {}
        return self._process_request('GetAccountBalance', params, [('AvailableBalance', Price),
                                                                   ('OnHoldBalance', Price)])
    
    def register_hit_type(self, title, description, reward, duration,
                          keywords=None, approval_delay=None, qual_req=None):
        """
        Register a new HIT Type
        \ttitle, description are strings
        \treward is a Price object
        \tduration can be an integer or string
        """
        params = {'Title' : title,
                  'Description' : description,
                  'AssignmentDurationInSeconds' : duration}
        params.update(MTurkConnection.get_price_as_price(reward).get_as_params('Reward'))

        if keywords:
            params['Keywords'] = keywords

        if approval_delay is not None:
            params['AutoApprovalDelayInSeconds']= approval_delay

        return self._process_request('RegisterHITType', params)

    def set_email_notification(self, hit_type, email, event_types=None):
        """
        Performs a SetHITTypeNotification operation to set email notification for a specified HIT type
        """
        return self._set_notification(hit_type, 'Email', email, event_types)
    
    def set_rest_notification(self, hit_type, url, event_types=None):
        """
        Performs a SetHITTypeNotification operation to set REST notification for a specified HIT type
        """
        return self._set_notification(hit_type, 'REST', url, event_types)
        
    def _set_notification(self, hit_type, transport, destination, event_types=None):
        """
        Common SetHITTypeNotification operation to set notification for a specified HIT type
        """
        assert type(hit_type) is str, "hit_type argument should be a string."
        
        params = {'HITTypeId': hit_type}
        
        # from the Developer Guide:
        # The 'Active' parameter is optional. If omitted, the active status of the HIT type's
        # notification specification is unchanged. All HIT types begin with their
        # notification specifications in the "inactive" status.
        notification_params = {'Destination': destination,
                               'Transport': transport,
                               'Version': boto.mturk.notification.NotificationMessage.NOTIFICATION_VERSION,
                               'Active': True,
                               }

        # add specific event types if required
        if event_types:
            self.build_list_params(notification_params, event_types, 'EventType')
        
        # Set up dict of 'Notification.1.Transport' etc. values
        notification_rest_params = {}
        num = 1
        for key in notification_params:
            notification_rest_params['Notification.%d.%s' % (num, key)] = notification_params[key]
        
        # Update main params dict
        params.update(notification_rest_params)
        
        # Execute operation
        return self._process_request('SetHITTypeNotification', params)
    
    def create_hit(self, hit_type=None, question=None, lifetime=60*60*24*7, max_assignments=1, 
                   title=None, description=None, keywords=None, reward=None,
                   duration=60*60*24*7, approval_delay=None, annotation=None, qual_req=None, 
                   questions=None, qualifications=None, response_groups=None):
        """
        Creates a new HIT.
        Returns a ResultSet
        See: http://docs.amazonwebservices.com/AWSMechanicalTurkRequester/2006-10-31/ApiReference_CreateHITOperation.html
        """
        
        # handle single or multiple questions
        if question is not None and questions is not None:
            raise ValueError("Must specify either question (single Question instance) or questions (list), but not both")
        if question is not None and questions is None:
            questions = [question]
        
        
        # Handle basic required arguments and set up params dict
        params = {'Question': question.get_as_xml(),
                  'LifetimeInSeconds' : lifetime,
                  'MaxAssignments' : max_assignments,
                  }

        # if hit type specified then add it
        # else add the additional required parameters
        if hit_type:
            params['HITTypeId'] = hit_type
        else:
            # Handle keywords
            final_keywords = MTurkConnection.get_keywords_as_string(keywords)
            
            # Handle price argument
            final_price = MTurkConnection.get_price_as_price(reward)

            additional_params = {'Title': title,
                                 'Description' : description,
                                 'Keywords': final_keywords,
                                 'AssignmentDurationInSeconds' : duration,
                                 }
            additional_params.update(final_price.get_as_params('Reward'))

            if approval_delay is not None:
                additional_params['AutoApprovalDelayInSeconds'] = approval_delay

            # add these params to the others
            params.update(additional_params)

        # add the annotation if specified
        if annotation is not None:
            params['RequesterAnnotation'] = annotation
               
        # Add the Qualifications if specified
        if qualifications is not None:
            params.update(qualifications.get_as_params())

        # Handle optional response groups argument
        if response_groups:
            self.build_list_params(params, response_groups, 'ResponseGroup')
                
        # Submit
        return self._process_request('CreateHIT', params, [('Reward', Price),])

    def get_reviewable_hits(self, hit_type=None, status='Reviewable',
                            sort_by='Expiration', sort_direction='Ascending', 
                            page_size=10, page_number=1):
        """
        Retrieve the HITs that have a status of Reviewable, or HITs that
        have a status of Reviewing, and that belong to the Requester calling the operation.
        """
        params = {'Status' : status,
                  'SortProperty' : sort_by,
                  'SortDirection' : sort_direction,
                  'PageSize' : page_size,
                  'PageNumber' : page_number}

        # Handle optional hit_type argument
        if hit_type is not None:
            params.update({'HITTypeId': hit_type})

        return self._process_request('GetReviewableHITs', params, [('HIT', HIT),])

    def search_hits(self, sort_by='CreationTime', sort_direction='Ascending', 
                    page_size=10, page_number=1):
        """
        Return all of a Requester's HITs, on behalf of the Requester.
        The operation returns HITs of any status, except for HITs that have been disposed 
        with the DisposeHIT operation.
        Note:
        The SearchHITs operation does not accept any search parameters that filter the results.
        """
        params = {'SortProperty' : sort_by,
                  'SortDirection' : sort_direction,
                  'PageSize' : page_size,
                  'PageNumber' : page_number}

        return self._process_request('SearchHITs', params, [('HIT', HIT),])

    def get_assignments(self, hit_id, status=None,
                            sort_by='SubmitTime', sort_direction='Ascending', 
                            page_size=10, page_number=1):
        """
        Retrieves completed assignments for a HIT. 
        Use this operation to retrieve the results for a HIT.

        The returned ResultSet will have the following attributes:

        NumResults
                The number of assignments on the page in the filtered results list, 
                equivalent to the number of assignments being returned by this call.
                A non-negative integer
        PageNumber
                The number of the page in the filtered results list being returned.
                A positive integer
        TotalNumResults
                The total number of HITs in the filtered results list based on this call.
                A non-negative integer

        The ResultSet will contain zero or more Assignment objects 

        """
        params = {'HITId' : hit_id,
                  'SortProperty' : sort_by,
                  'SortDirection' : sort_direction,
                  'PageSize' : page_size,
                  'PageNumber' : page_number}

        if status is not None:
            params['AssignmentStatus'] = status

        return self._process_request('GetAssignmentsForHIT', params, [('Assignment', Assignment),])

    def approve_assignment(self, assignment_id, feedback=None):
        """
        """
        params = {'AssignmentId' : assignment_id,}
        if feedback:
            params['RequesterFeedback'] = feedback
        return self._process_request('ApproveAssignment', params)

    def reject_assignment(self, assignment_id, feedback=None):
        """
        """
        params = {'AssignmentId' : assignment_id,}
        if feedback:
            params['RequesterFeedback'] = feedback
        return self._process_request('RejectAssignment', params)

    def get_hit(self, hit_id):
        """
        """
        params = {'HITId' : hit_id,}
        return self._process_request('GetHIT', params, [('HIT', HIT),])

    def set_reviewing(self, hit_id, revert=None):
        """
        Update a HIT with a status of Reviewable to have a status of Reviewing, 
        or reverts a Reviewing HIT back to the Reviewable status.

        Only HITs with a status of Reviewable can be updated with a status of Reviewing. 
        Similarly, only Reviewing HITs can be reverted back to a status of Reviewable.
        """
        params = {'HITId' : hit_id,}
        if revert:
            params['Revert'] = revert
        return self._process_request('SetHITAsReviewing', params)

    def disable_hit(self, hit_id):
        """
        Remove a HIT from the Mechanical Turk marketplace, approves all submitted assignments 
        that have not already been approved or rejected, and disposes of the HIT and all
        assignment data.

        Assignments for the HIT that have already been submitted, but not yet approved or rejected, will be
        automatically approved. Assignments in progress at the time of the call to DisableHIT will be
        approved once the assignments are submitted. You will be charged for approval of these assignments.
        DisableHIT completely disposes of the HIT and all submitted assignment data. Assignment results
        data cannot be retrieved for a HIT that has been disposed.

        It is not possible to re-enable a HIT once it has been disabled. To make the work from a disabled HIT
        available again, create a new HIT.
        """
        params = {'HITId' : hit_id,}
        return self._process_request('DisableHIT', params)

    def dispose_hit(self, hit_id):
        """
        Dispose of a HIT that is no longer needed.

        Only HITs in the "reviewable" state, with all submitted assignments approved or rejected, 
        can be disposed. A Requester can call GetReviewableHITs to determine which HITs are 
        reviewable, then call GetAssignmentsForHIT to retrieve the assignments. 
        Disposing of a HIT removes the HIT from the results of a call to GetReviewableHITs.
        """
        params = {'HITId' : hit_id,}
        return self._process_request('DisposeHIT', params)

    def extend_hit(self, hit_id, assignments_increment=None, expiration_increment=None):
        """
        Increase the maximum number of assignments, or extend the expiration date, of an existing HIT.
        
        NOTE: If a HIT has a status of Reviewable and the HIT is extended to make it Available, the
        HIT will not be returned by GetReviewableHITs, and its submitted assignments will not
        be returned by GetAssignmentsForHIT, until the HIT is Reviewable again.
        Assignment auto-approval will still happen on its original schedule, even if the HIT has
        been extended. Be sure to retrieve and approve (or reject) submitted assignments before
        extending the HIT, if so desired.
        """
        # must provide assignment *or* expiration increment
        if (assignments_increment is None and expiration_increment is None) or \
           (assignments_increment is not None and expiration_increment is not None):
            raise ValueError("Must specify either assignments_increment or expiration_increment, but not both")

        params = {'HITId' : hit_id,}
        if assignments_increment:
            params['MaxAssignmentsIncrement'] = assignments_increment
        if expiration_increment:
            params['ExpirationIncrementInSeconds'] = expiration_increment

        return self._process_request('ExtendHIT', params)

    def get_help(self, about, help_type='Operation'):
        """
        Return information about the Mechanical Turk Service operations and response group
        NOTE - this is basically useless as it just returns the URL of the documentation

        help_type: either 'Operation' or 'ResponseGroup'
        """
        params = {'About': about, 'HelpType': help_type,}
        return self._process_request('Help', params)

    def grant_bonus(self, worker_id, assignment_id, bonus_price, reason):
        """
        Issues a payment of money from your account to a Worker.
        To be eligible for a bonus, the Worker must have submitted results for one of your
        HITs, and have had those results approved or rejected. This payment happens separately
        from the reward you pay to the Worker when you approve the Worker's assignment.
        The Bonus must be passed in as an instance of the Price object.
        """
        params = bonus_price.get_as_params('BonusAmount', 1)
        params['WorkerId'] = worker_id
        params['AssignmentId'] = assignment_id
        params['Reason'] = reason

        return self._process_request('GrantBonus', params)

    def _process_request(self, request_type, params, marker_elems=None):
        """
        Helper to process the xml response from AWS
        """
        response = self.make_request(request_type, params)
        return self._process_response(response, marker_elems)

    def _process_response(self, response, marker_elems=None):
        """
        Helper to process the xml response from AWS
        """
        body = response.read()
        #print body
        if response.status == 200:
            rs = ResultSet(marker_elems)
            h = handler.XmlHandler(rs, self)
            xml.sax.parseString(body, h)
            return rs
        else:
            raise EC2ResponseError(response.status, response.reason, body)

    @staticmethod
    def get_keywords_as_string(keywords):
        """
        Returns a comma+space-separated string of keywords from either a list or a string
        """
        if type(keywords) is list:
            final_keywords = ', '.join(keywords)
        elif type(keywords) is str:
            final_keywords = keywords
        elif keywords is None:
            final_keywords = ""
        else:
            raise TypeError("keywords argument must be a string or a list of strings; got a %s" % type(keywords))
        return final_keywords
    
    @staticmethod
    def get_price_as_price(reward):
        """
        Returns a Price data structure from either a float or a Price
        """
        if isinstance(reward, Price):
            final_price = reward
        else:
            final_price = Price(reward)
        return final_price

class BaseAutoResultElement:
    """
    Base class to automatically add attributes when parsing XML
    """
    def __init__(self, connection):
        self.connection = connection

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        setattr(self, name, value)

class HIT(BaseAutoResultElement):
    """
    Class to extract a HIT structure from a response (used in ResultSet)
    
    Will have attributes named as per the Developer Guide, 
    e.g. HITId, HITTypeId, CreationTime
    """

    # property helper to determine if HIT has expired
    def _has_expired(self):
        """ Has this HIT expired yet? """
        expired = False
        if hasattr(self, 'Expiration'):
            now = datetime.datetime.utcnow()
            expiration = datetime.datetime.strptime(self.Expiration, '%Y-%m-%dT%H:%M:%SZ')
            expired = (now >= expiration)
        else:
            raise ValueError("ERROR: Request for expired property, but no Expiration in HIT!")
        return expired

    # are we there yet?
    expired = property(_has_expired)

class Assignment(BaseAutoResultElement):
    """
    Class to extract an Assignment structure from a response (used in ResultSet)
    
    Will have attributes named as per the Developer Guide, 
    e.g. AssignmentId, WorkerId, HITId, Answer, etc
    """

    def __init__(self, connection):
        BaseAutoResultElement.__init__(self, connection)
        self.answers = []

    def endElement(self, name, value, connection):
        # the answer consists of embedded XML, so it needs to be parsed independantly
        if name == 'Answer':
            answer_rs = ResultSet([('Answer', QuestionFormAnswer),])
            h = handler.XmlHandler(answer_rs, connection)
            # need to convert from unicode to string for sax
            value = str(value)
            xml.sax.parseString(value, h)
            self.answers.append(answer_rs)
        else:
            BaseAutoResultElement.endElement(self, name, value, connection)

class QuestionFormAnswer(BaseAutoResultElement):
    """
    Class to extract Answers from inside the embedded XML QuestionFormAnswers element inside the
    Answer element which is part of the Assignment structure

    A QuestionFormAnswers element contains an Answer element for each question in the HIT or
    Qualification test for which the Worker provided an answer. Each Answer contains a
    QuestionIdentifier element whose value corresponds to the QuestionIdentifier of a
    Question in the QuestionForm. See the QuestionForm data structure for more information about
    questions and answer specifications.

    If the question expects a free-text answer, the Answer element contains a FreeText element. This
    element contains the Worker's answer

    *NOTE* - currently really only supports free-text answers
    """

    pass
