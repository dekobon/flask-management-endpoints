# Flask Management Endpoints

Flask Management Endpoints allows for the definition of endpoints in your Flask 
application such that Kubernetes can use them for [liveness and readiness probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/).
Additionally, it provides verbose health and informational endpoints. The API
is designed in the style of [Spring Actuator management endpoints](https://docs.spring.io/spring-boot/docs/current/reference/html/actuator.html). 

| Endpoint              | Method / Return Type | Description                                                                                                                     |
| --------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `/info`               | `GET / json`         | Provides information about the application and host system.                                                                     |
| `/health`             | `GET / json`         | Runs all health checks and outputs the status of each health check.                                                             |
| `/health/liveness`    | `GET / json`         | Returns successfully if endpoint is running with terse output.                                                                  |
| `/health/ping`        | `GET / json`         | Returns successfully if endpoint is running with terse output (same as liveness).                                               |
| `/health/readiness`   | `GET / json`         | Readiness probe endpoint that runs all health checks and has terse output.                                                      |
| `/version`            | `GET / plaintext`    | By default returns the contents of the environment variable `VERSION`, but can be configured to return any value via a closure. |

## Configuration

To register the [Flask Blueprint](https://exploreflask.com/en/latest/blueprints.html) in your application:
```python
from flask import Flask
from flask_management_endpoints import z_blueprint

app = Flask(__name__)
app.register_blueprint(z_blueprint)
```

If you would like to mount the endpoint at a different URL prefix than the default (`/z`), then it can be
specified when registering the blueprint:
```python
app.register_blueprint(z_blueprint, url_prefix="/admin")
```

Next, define the URL service health checks that you would like to register. The service dependencies can be defined
as a fixed URL in which checks will be appended to the end. Alternatively, dependencies can be defined with simply
a hostname and an optional port, then the URL scheme and paths will be filled in by defaults.
```python
app.config.update(
    Z_ENDPOINTS={        
        "service_dependencies": {
            # key is an identifier for the service name
            # value is a base URL pointing to a Spring Actuator style health endpoint or just a hostname with
            # an optional port.
            'users_api': 'https://user-service:9922/admin', # readiness check: https://user-service:9922/admin/readiness
            'widget_api': 'widget-service', # readiness check: {PREFERRED_URL_SCHEME}://widget-service/{url_prefix}/health/readiness
        }
    }
)
```

If you would like to have custom functions that will execute on the readiness check, you can define them as follows:
```python
def db_check():
    try:
        engine = users_db.engine
        result = engine.execute('SELECT 1')
        return result.first()[0] == 1
    except Exception as err:
        app.logger.error(f'DB health check failed: {err}')
        return False

app.config.update(
    Z_ENDPOINTS={
        'check_functions': {
            'readiness': {
                'db': db_check
            }
        }
    }
```

### Extension

This project can also be used via the provided Flask extension. With the extension the blueprint is registered using
the `ManagementEndpoints` class.

```python
from flask import Flask
from flask_management_endpoints import ManagementEndpoints

app = Flask(__name__)
ManagementEndpoints(app)
```

The rest of the configuration is identical.

The extension has an additional option, `no_log`, that can disable logging of the HTTP requests
handled by your healthz endpoints, to avoid cluttering your web log files with automated requests.
At the moment, only the [gunicorn](https://gunicorn.org/) web server is supported.

```python
ManagementEndpoints(app, no_log=True)
```

## Other Resources

If you need a less opinionated Flask health check blueprint, check out [flask-healthz](https://github.com/fedora-infra/flask-healthz). 

## License

Copyright 2021 Elijah Zupancic

The Flask Management Endpoints project is licensed under the same license as Flask itself: [BSD 3-clause](LICENSE).
