import os
import platform
import re
import socket
import sys
import tempfile
import uuid
from typing import Optional

# Regex that validates and parses a k8s pod name from a network hostname
pod_name_re = re.compile(r'(\w+)-([a-z0-9]{9})-([a-z0-9]{5})')


class Info(dict):
    """
    Class providing information about the running application and host system. The data
    returned from this class is roughly in the same form as returned by Spring Actuator's
    /info endpoint with supplemental trace attributes that are in the Open Telemetry
    Resource format.
    """
    def __init__(self, app_name: str, enable_service_instance_id: Optional[bool] = False):
        super().__init__()
        self['app'] = Info.app_attributes(name=app_name)
        self['trace.attributes'] = Info.trace_attributes(app_name=app_name,
                                                         enable_service_instance_id=enable_service_instance_id)

    @staticmethod
    def app_attributes(name: Optional[str] = None,
                       version: Optional[str] = os.getenv('VERSION')):
        """
        Method providing information about the running application.
        :param name: name of application
        :param version: version of application
        :return: dictionary containing application information
        """
        attributes = {}
        if name:
            attributes['name'] = name
        if version:
            attributes['version'] = version

        return attributes

    @staticmethod
    def trace_attributes(app_name: str,
                         version: Optional[str] = os.getenv('VERSION'),
                         enable_service_instance_id: Optional[bool] = False) -> dict:
        """
        Method providing trace information in the Open Telemetry Resource format.
        :param app_name: name of application
        :param version: version of application
        :param enable_service_instance_id: when true a unique service instance is generated and stored on disk
        :return: dictionary containing Open Telemetry resource attributes
        """
        attributes = {'service.name': app_name}
        if version:
            attributes['service.version'] = version
        attributes.update(Info.host_info())
        attributes.update(Info.os_info())
        attributes.update(Info.process_info())
        machine_id_attributes = Info.machine_id()
        if machine_id_attributes:
            attributes.update(machine_id_attributes)
        container_id_attributes = Info.container_id()
        if container_id_attributes:
            attributes.update(container_id_attributes)
        if enable_service_instance_id:
            service_instance_id = Info.service_instance_id(app_name=app_name)
            if service_instance_id:
                attributes.update(service_instance_id)
        k8s_attributes = Info.k8s()
        if k8s_attributes:
            attributes.update(k8s_attributes)

        return attributes

    @staticmethod
    def host_info(hostname: Optional[str] = os.getenv('HOSTNAME') or socket.gethostname()) -> dict:
        """
        Method providing information about the underlying host.
        :param hostname: network hostname
        """
        attributes = {
            'host.arch': platform.machine().replace('x86_64', 'amd64'),
            'host.name': platform.node(),
        }

        if hostname:
            attributes['host.hostname'] = hostname

        return attributes

    @staticmethod
    def os_info() -> dict:
        """
        Method providing information about the underlying OS.
        """
        return {
            'os.description': f'{platform.system()} {platform.release()}',
            'os.type': platform.system().lower()
        }

    @staticmethod
    def process_info() -> dict:
        """
        Method providing information about the application's running process.
        """
        return {
            'process.pid': os.getpid(),
            'process.command_line': ' '.join(sys.argv),
            'process.executable.path': sys.executable,
            'process.runtime.description': ' '.join(platform.python_build()),
            'process.runtime.name': platform.python_implementation(),
            'process.runtime.version': platform.python_version()
        }

    @staticmethod
    def machine_id(machine_id_file: Optional[str] = '/etc/machine-id') -> dict:
        """
        Method that returns a unique machine id as read from a file on the local filesystem.
        :param machine_id_file: path to file containing machine id file
        """
        attributes = {}

        file_content = Info.read_first_line(machine_id_file)
        if file_content:
            attributes['machine.id'] = file_content

        return attributes

    @staticmethod
    def container_id(cpuset_file: Optional[str] = '/proc/1/cpuset') -> dict:
        """
        Method that returns the running container id if available.
        :param cpuset_file: path to file containing cpuset details
        """
        attributes = {}

        file_content = Info.read_first_line(cpuset_file)
        if file_content:
            tokens = file_content.split('/')
            if len(tokens) > 0:
                container_id = tokens[len(tokens) - 1]
                if container_id != '':
                    attributes['container.id'] = container_id

        return attributes

    @staticmethod
    def service_instance_id(app_name: str,
                            service_instance_id_file: Optional[str] = None):
        """
        Method that generates a unique service id and stores it on a file in the file system. This
        service id would remain constant for the life of an application on a given host.
        :param app_name: name of application
        :param service_instance_id_file: name of file to store service instance id in
        """
        if not service_instance_id_file:
            tempdir = tempfile.gettempdir()
            filename = f'{app_name}-service-instance-id'
            service_instance_id_file = os.path.join(tempdir, filename)

        attributes = {}

        service_instance_id = Info.read_first_line(service_instance_id_file)
        if not service_instance_id:
            with open(service_instance_id_file, 'wt') as file:
                service_instance_id = str(uuid.uuid1()).replace('-', '')
                file.write(service_instance_id)
                file.write('\n')

        attributes['service.instance.id'] = service_instance_id

        return attributes

    @staticmethod
    def k8s(hostname: Optional[str] = os.getenv('HOSTNAME') or socket.gethostname(),
            namespace: Optional[str] = os.getenv('NAMESPACE')) -> Optional[dict]:
        """
        Method that returns details about the running Kubernetes environment.
        :param hostname: network hostname from which the pod name will be parsed
        :param namespace: kubernetes namespace
        :return:
        """
        if not hostname and not namespace:
            return None

        attributes = {}
        if hostname:
            pod_name_pattern = pod_name_re.match(hostname)
            if pod_name_pattern:
                attributes['k8s.pod.name'] = hostname
                attributes['k8s.container.name'] = pod_name_pattern.group(1)

        if namespace:
            attributes['k8s.namespace.name'] = namespace

        return attributes

    @staticmethod
    def read_first_line(file: str) -> Optional[str]:
        """
        Utility method that reads the first 1024 characters from a file into a string.
        :param file: file to read
        :return: string containing contents of file
        """
        if os.path.isfile(file):
            # noinspection PyBroadException
            try:
                with open(file, 'rt') as file:
                    content = file.readline(1024).strip()
                    if content == '':
                        return None
                    else:
                        return content
            except Exception:
                pass

        return None
