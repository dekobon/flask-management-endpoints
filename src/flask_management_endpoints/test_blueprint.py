import unittest

from . import blueprint


class TestManagementEndpointsBlueprint(unittest.TestCase):
    def test_http_url_as_backend_url(self):
        backend_name = 'http_unit_test_service'
        backend_host = 'http://localhost:9090/admin/health'
        check_name = 'foo'
        expected = f'{backend_host}/{check_name}'
        actual = blueprint._backend_host_as_url(backend_name=backend_name,
                                                backend_host=backend_host,
                                                check_name=check_name)
        self.assertEqual(expected, str(actual))

    def test_https_url_as_backend_url(self):
        backend_name = 'https_unit_test_service'
        backend_host = 'https://localhost:9090/admin/health'
        check_name = 'foo'
        expected = f'{backend_host}/{check_name}'
        actual = blueprint._backend_host_as_url(backend_name=backend_name,
                                                backend_host=backend_host,
                                                check_name=check_name)
        self.assertEqual(expected, str(actual))

    def test_host_and_port_as_backend_url(self):
        backend_name = 'http_unit_test_service'
        backend_host = 'localhost:8000'
        check_name = 'foo'
        expected = f'http://{backend_host}/z/health/{check_name}'
        actual = blueprint._backend_host_as_url(backend_name=backend_name,
                                                backend_host=backend_host,
                                                check_name=check_name)
        self.assertEqual(expected, str(actual))

    def test_host_and_port_with_path_as_backend_url(self):
        backend_name = 'http_unit_test_service'
        backend_host = 'localhost:8000/admin'
        check_name = 'foo'
        expected = f'http://{backend_host}/{check_name}'
        actual = blueprint._backend_host_as_url(backend_name=backend_name,
                                                backend_host=backend_host,
                                                check_name=check_name)
        self.assertEqual(expected, str(actual))

    def test_host_as_backend_url(self):
        backend_name = 'http_unit_test_service'
        backend_host = 'localhost'
        check_name = 'foo'
        expected = f'http://{backend_host}/z/health/{check_name}'
        actual = blueprint._backend_host_as_url(backend_name=backend_name,
                                                backend_host=backend_host,
                                                check_name=check_name)
        self.assertEqual(expected, str(actual))

    def test_host_as_backend_url_with_no_check_name(self):
        backend_name = 'http_unit_test_service'
        backend_host = 'localhost'
        check_name = ''
        expected = f'http://{backend_host}/z/health'
        actual = blueprint._backend_host_as_url(backend_name=backend_name,
                                                backend_host=backend_host,
                                                check_name=check_name)
        self.assertEqual(expected, str(actual))

    def test_bad_value_as_backend_url(self):
        backend_name = 'http_unit_test_service'
        backend_host = 'local:://host'
        check_name = 'foo'

        with self.assertRaises(blueprint.HealthError):
            blueprint._backend_host_as_url(backend_name=backend_name,
                                           backend_host=backend_host,
                                           check_name=check_name)
