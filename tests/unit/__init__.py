try:
    import unittest2 as unittest
except ImportError:
    import unittest
import httplib

from mock import Mock


class AWSMockServiceTestCase(unittest.TestCase):
    """Base class for mocking aws services."""
    # This param is used by the unittest module to display a full
    # diff when assert*Equal methods produce an error message.
    maxDiff = None
    connection_class = None

    def setUp(self):
        self.https_connection = Mock(spec=httplib.HTTPSConnection)
        self.https_connection_factory = (
            Mock(return_value=self.https_connection), ())
        self.service_connection = self.create_service_connection(
            https_connection_factory=self.https_connection_factory,
            aws_access_key_id='aws_access_key_id',
            aws_secret_access_key='aws_secret_access_key')
        self.actual_request = None
        self.original_mexe = self.service_connection._mexe
        self.service_connection._mexe = self._mexe_spy

    def create_service_connection(self, **kwargs):
        if self.connection_class is None:
            raise ValueError("The connection_class class attribute must be "
                             "set to a non-None value.")
        return self.connection_class(**kwargs)

    def _mexe_spy(self, request, *args, **kwargs):
        self.actual_request = request
        return self.original_mexe(request, *args, **kwargs)

    def create_response(self, status_code, reason='', header=[], body=None):
        if body is None:
            body = self.default_body()
        response = Mock(spec=httplib.HTTPResponse)
        response.status = status_code
        response.read.return_value = body
        response.reason = reason

        response.getheaders.return_value = header
        def overwrite_header(arg, default=None):
            header_dict = dict(header)
            if header_dict.has_key(arg):
                return header_dict[arg]
            else:
                return default
        response.getheader.side_effect = overwrite_header
        
        return response

    def assert_request_parameters(self, params, ignore_params_values=None):
        """Verify the actual parameters sent to the service API."""
        request_params = self.actual_request.params.copy()
        if ignore_params_values is not None:
            for param in ignore_params_values:
                # We still want to check that the ignore_params_values params
                # are in the request parameters, we just don't need to check
                # their value.
                self.assertIn(param, request_params)
                del request_params[param]
        self.assertDictEqual(request_params, params)

    def set_http_response(self, status_code, reason='', header=[], body=None):
        http_response = self.create_response(status_code, reason, header, body)
        self.https_connection.getresponse.return_value = http_response

    def default_body(self):
        return ''
