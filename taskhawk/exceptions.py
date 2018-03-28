class RetryException(Exception):
    """
    Special exception that does not log an exception when it is received.
    This is a retryable error.
    """
    def __init__(self, *args, **kwargs):
        super(RetryException, self).__init__(*args, **kwargs)
        if 'exc' in kwargs:
            self.exc = kwargs['exc']


class ValidationError(Exception):
    pass


class TaskNotFound(Exception):
    pass


class ConfigurationError(Exception):
    pass
