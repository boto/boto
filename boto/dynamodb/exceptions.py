"""
Exceptions that are specific to the dynamodb module.
"""
from boto.exception import BotoServerError

class DynamoDBExpiredTokenError(BotoServerError):
    """
    Raised when a DynamoDB security token expires. This is generally boto's
    (or the user's) notice to renew their DynamoDB security tokens.
    """
    pass