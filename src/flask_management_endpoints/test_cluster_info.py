import unittest

from .info import Info


class TestClusterInfo(unittest.TestCase):
    def test_k8s_can_parse_valid_pod_name(self):
        hostname = 'fooservice-b55497fc6-x9f56'
        namespace = 'something'
        infoz = Info.k8s(hostname=hostname, namespace=namespace)
        self.assertEqual(infoz['k8s.pod.name'], hostname)
        self.assertEqual(infoz['k8s.container.name'], 'fooservice')
        self.assertEqual(infoz['k8s.namespace.name'], namespace)

    def test_k8s_wont_parse_invalid_pod_name(self):
        hostname = 'generic-hostname'
        infoz = Info.k8s(hostname=hostname, namespace=None)
        self.assertNotIn('k8s.pod.name', infoz)
        self.assertNotIn('k8s.container.name', infoz)
        self.assertNotIn('k8s.namespace.name', infoz)
