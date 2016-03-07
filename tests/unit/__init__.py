from boto.compat import http_client
from tests.compat import mock, unittest


class AWSMockServiceTestCase(unittest.TestCase):
    """Base class for mocking aws services."""
    # This param is used by the unittest module to display a full
    # diff when assert*Equal methods produce an error message.
    maxDiff = None
    connection_class = None

    def setUp(self):
        self.https_connection = mock.Mock(spec=http_client.HTTPSConnection)
        self.https_connection.debuglevel = 0
        self.https_connection_factory = (
            mock.Mock(return_value=self.https_connection), ())
        self.service_connection = self.create_service_connection(
            https_connection_factory=self.https_connection_factory,
            aws_access_key_id='aws_access_key_id',
            aws_secret_access_key='aws_secret_access_key')
        self.initialize_service_connection()

    def initialize_service_connection(self):
        self.actual_request = None
        self.original_mexe = self.service_connection._mexe
        self.service_connection._mexe = self._mexe_spy
        self.proxy = None
        self.use_proxy = False

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
        response = mock.Mock(spec=http_client.HTTPResponse)
        response.status = status_code
        response.read.return_value = body
        response.reason = reason

        response.getheaders.return_value = header
        response.msg = dict(header)

        def overwrite_header(arg, default=None):
            header_dict = dict(header)
            if arg in header_dict:
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
                try:
                    del request_params[param]
                except KeyError:
                    pass
        self.assertDictEqual(request_params, params)

    def set_http_response(self, status_code, reason='', header=[], body=None):
        http_response = self.create_response(status_code, reason, header, body)
        self.https_connection.getresponse.return_value = http_response

    def default_body(self):
        return ''


class MockServiceWithConfigTestCase(AWSMockServiceTestCase):
    def setUp(self):
        super(MockServiceWithConfigTestCase, self).setUp()
        self.environ = {}
        self.config = {}
        self.config_patch = mock.patch('boto.provider.config.get',
                                       self.get_config)
        self.has_config_patch = mock.patch('boto.provider.config.has_option',
                                           self.has_config)
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.config_patch.start()
        self.has_config_patch.start()
        self.environ_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        self.has_config_patch.stop()
        self.environ_patch.stop()

    def has_config(self, section_name, key):
        try:
            self.config[section_name][key]
            return True
        except KeyError:
            return False

    def get_config(self, section_name, key, default=None):
        try:
            return self.config[section_name][key]
        except KeyError:
            return None

class AWSQueryConnectionParamOverrideTestBase(unittest.TestCase):
    def get_conn_class(self):
        raise Exception("Abstract method")

    def test_host_override(self):
        host_name = 'some.dummy.host'
        conn = self.get_conn_class()(host=host_name)
        self.assertEqual(host_name, conn.host)

    def test_port_override(self):
        port_num = 12345
        conn = self.get_conn_class()(port=port_num)
        self.assertEqual(port_num, conn.port)

    def _test_ssl_override(self, is_secure):
        conn = self.get_conn_class()(is_secure=is_secure)
        self.assertEqual(is_secure, conn.is_secure)

    def test_ssl_override_true(self):
        self._test_ssl_override(True)

    def test_ssl_override_false(self):
        self._test_ssl_override(False)
