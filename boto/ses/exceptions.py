"""
Various exceptions that are specific to the SES module.
"""
from boto.exception import BotoServerError

class SESAddressNotVerifiedError(BotoServerError):
    """
    Raised when a "Reply-To" address has not been validated in SES yet.
    """
    pass


class SESAddressBlacklistedError(BotoServerError):
    """
    After you attempt to send mail to an address, and delivery repeatedly
    fails, said address is blacklisted for at least 24 hours. The blacklisting
    eventually expires, and you are able to attempt delivery again. If you
    attempt to send mail to a blacklisted email, this is raised.
    """
    pass


class SESDailyQuotaExceededError(BotoServerError):
    """
    Your account's daily (rolling 24 hour total) allotment of outbound emails
    has been exceeded.
    """
    pass


class SESMaxSendingRateExceededError(BotoServerError):
    """
    Your account's requests/second limit has been exceeded.
    """
    pass


class SESDomainEndsWithDotError(BotoServerError):
    """
    Recipient's email address' domain ends with a period/dot.
    """
    pass