import os
import platform
import re
import socket
import sys
import tempfile
import uuid
from typing import Optional

pod_name_re = re.compile(r'(\w+)-([a-z0-9]{9})-([a-z0-9]{5})')


class Info(dict):
    def __init__(self, app_name: str):
        super().__init__()
        self['app'] = Info.app_attributes(name=app_name)
        self['trace.attributes'] = Info.trace_attributes(app_name)

    @staticmethod
    def app_attributes(name: Optional[str] = None,
                       version: Optional[str] = os.getenv('VERSION')):
        attributes = {}
        if name:
            attributes['name'] = name
        if version:
            attributes['version'] = version

        return attributes

    @staticmethod
    def trace_attributes(app_name: str,
                         version: Optional[str] = os.getenv('VERSION')) -> dict:
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
        service_instance_id = Info.service_instance_id(app_name=app_name)
        if service_instance_id:
            attributes.update(service_instance_id)
        k8s_attributes = Info.k8s()
        if k8s_attributes:
            attributes.update(k8s_attributes)

        return attributes

    @staticmethod
    def host_info(hostname: Optional[str] = os.getenv('HOSTNAME') or socket.gethostname()) -> dict:
        attributes = {
            'host.arch': platform.machine().replace('x86_64', 'amd64'),
            'host.name': platform.node(),
        }

        if hostname:
            attributes['host.hostname'] = hostname

        return attributes

    @staticmethod
    def os_info() -> dict:
        return {
            'os.description': f'{platform.system()} {platform.release()}',
            'os.type': platform.system().lower()
        }

    @staticmethod
    def process_info() -> dict:
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
        attributes = {}

        file_content = Info.read_first_line(machine_id_file)
        if file_content:
            attributes['machine.id'] = file_content

        return attributes

    @staticmethod
    def container_id(cpuset_file: Optional[str] = '/proc/1/cpuset') -> dict:
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
        if os.path.isfile(file):
            # noinspection PyBroadException
            try:
                with open(file, 'rt') as file:
                    content = file.readline(1024).strip()
                    if content == '':
                        return None
                    else:
                        return content
            except:
                pass

        return None
