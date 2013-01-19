import time

from boto.provider import Provider


_HAS_GOOGLE_CREDENTIALS = None


def has_google_credentials():
    global _HAS_GOOGLE_CREDENTIALS
    if _HAS_GOOGLE_CREDENTIALS is None:
        provider = Provider('google')
        if provider.access_key is None or provider.secret_key is None:
            _HAS_GOOGLE_CREDENTIALS = False
        else:
            _HAS_GOOGLE_CREDENTIALS = True
    return _HAS_GOOGLE_CREDENTIALS


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    Taken from:
      https://github.com/saltycrane/retry-decorator
    Licensed under BSD:
      https://github.com/saltycrane/retry-decorator/blob/master/LICENSE

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            try_one_last_time = True
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                    try_one_last_time = False
                    break
                except ExceptionToCheck, e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            if try_one_last_time:
                return f(*args, **kwargs)
            return
        return f_retry  # true decorator
    return deco_retry
