import json
import os
from typing import Optional, Callable, List

import flask
import requests
from flask import Blueprint, current_app, Response

from .info import Info

# Endpoints in this list are allowed to make cascading calls to
# dependent services.
CASCADING_CHECKS: List[str] = ['readiness']
# Endpoints in this list are allowed to make calls to closures
# for their input.
CHECKS_WITH_PLUGGABLE_FUNCTIONS: List[str] = ['readiness', 'version_function']
# This is the Flask blueprint object that is used to import the
# blueprint into a Flask application.
management_endpoints_blueprint = Blueprint(name='management_endpoints',
                                           import_name=__name__,
                                           url_prefix='/z')


class HealthError(Exception):
    pass


@management_endpoints_blueprint.route('/version', methods=['GET'])
def version():
    """
    Returns the version of the Flask application.
    """
    if 'version_function' in CHECKS_WITH_PLUGGABLE_FUNCTIONS:
        version_function = _z_endpoints_config()['version_function']
        return version_function()
    else:
        return current_app.render_template("404.html")


@management_endpoints_blueprint.route('/info', methods=['GET'])
def info():
    """
    Returns information about the environment in which this Flask
    application is running.

    """
    info_attributes = Info(app_name=current_app.name)

    return Response(response=json.dumps(info_attributes),
                    content_type='application/json',
                    status=200)


@management_endpoints_blueprint.route("/health/<check_name>")
def nested_health_check(check_name):
    all_successful = True

    if check_name in CASCADING_CHECKS:
        if not _terse_cascading_z_check(check_name):
            all_successful = False
    elif check_name == 'liveness' or check_name == 'ping':
        all_successful = True
    else:
        return current_app.render_template("404.html")

    config = _z_endpoints_config()
    check_config = config['check_functions']

    if check_name in CHECKS_WITH_PLUGGABLE_FUNCTIONS and check_name in check_config:
        for func_name, run_check_func in check_config[check_name].items():
            if not run_check_func():
                all_successful = False

    status = {'status': _up_or_down(all_successful)}
    status_code = _success_status_code(all_successful)
    return Response(json.dumps(status), content_type='application/json', status=status_code)


@management_endpoints_blueprint.route("/health")
def health():
    config = _z_endpoints_config()

    all_successful = True
    status = {'components': {}}
    components = status['components']

    def response_hook(_backend_host: str, backend_name: str, _url: str,
                      response: Optional[flask.Response] = None):
        if response is not None:
            components[backend_name].update(response.json())

    # Check every dependent webservice and get its health status
    for backend_name, backend_host in config['service_dependencies'].items():
        components[backend_name] = {}
        success = _check_backend(backend_name=backend_name,
                                 backend_host=backend_host,
                                 check_name=None,
                                 response_hook=response_hook)

        components[backend_name]['status'] = _up_or_down(success)

        if not success:
            all_successful = False

    # Run each applicable health check function
    check_config = config['check_functions']
    for check_name in CHECKS_WITH_PLUGGABLE_FUNCTIONS:
        if check_name in check_config:
            for func_name, run_check_func in check_config[check_name].items():
                success = run_check_func()
                components[func_name] = {
                    'status': _up_or_down(success)
                }
                if not success:
                    all_successful = False

    status['status'] = _up_or_down(all_successful)
    status_code = _success_status_code(all_successful)

    return Response(json.dumps(status),
                    content_type='application/json',
                    status=status_code)


def _default_version_function():
    return os.environ.get('VERSION') or 'unknown', 200


def _z_endpoints_config() -> dict:
    if 'Z_ENDPOINTS' not in current_app.config:
        config = {}
    else:
        config = current_app.config['Z_ENDPOINTS']

    if 'service_dependencies' not in config:
        config['service_dependencies'] = {}

    if 'check_functions' not in config:
        config['check_functions'] = {}
    if 'version_function' not in config:
        config['version_function'] = _default_version_function

    return config


def _check_backend(backend_name: str, backend_host: str, check_name: Optional[str] = None,
                   response_hook: Optional[Callable] = None) -> bool:
    timeout = current_app.config['BACKEND_TIMEOUT']
    if check_name:
        check_endpoint = f'/{check_name}'
    else:
        check_endpoint = ''
    url = f'http://{backend_host}/z/health{check_endpoint}'
    response = None

    try:
        response = requests.get(url=url, timeout=timeout)
        response_json = response.json()
        status_is_up = 'status' in response_json and response_json['status'] == 'UP'

        # If a response hook has been defined and we haven't error trying to decode JSON
        if response_hook and response_json:
            response_hook(check_name, backend_name, url, response)

        if response.status_code != 200 or not status_is_up:
            msg = f'Check against {url} failed [check={check_name}, ' \
                  f'status_code={response.status_code}:\n{response_json}'
            raise HealthError(msg)
    except HealthError as err:
        current_app.logger.error(err)
        return False
    except (IOError, ValueError) as err:
        msg = f'Check against {url} failed [check={check_name}]: {err}'
        current_app.logger.error(msg)
        return False

    return True


def _terse_cascading_z_check(check_name) -> bool:
    config = _z_endpoints_config()
    all_successful = True

    for backend_name, backend_host in config['service_dependencies'].items():
        success = _check_backend(backend_name=backend_name,
                                 backend_host=backend_host,
                                 check_name=check_name)

        if not success:
            all_successful = False

    return all_successful


def _up_or_down(flag: bool) -> str:
    if flag:
        return 'UP'
    else:
        return 'DOWN'


def _success_status_code(flag: bool) -> int:
    if flag:
        return 200
    else:
        return 503