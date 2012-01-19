"""
Exceptions that are specific to the dynamodb module.
"""
from boto.exception import BotoServerError, BotoClientError

class DynamoDBExpiredTokenError(BotoServerError):
    """
    Raised when a DynamoDB security token expires. This is generally boto's
    (or the user's) notice to renew their DynamoDB security tokens.
    """
    pass


class DynamoDBKeyNotFoundError(BotoClientError):
    """
    Raised when attempting to retrieve or interact with an item whose key
    can't be found.
    """
    pass