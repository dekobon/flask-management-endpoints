# This code is inspired from:
# https://github.com/fedora-infra/flask-healthz/blob/7cda21963e379c10e5376c2cfbadf5de12ee1b6b/flask_healthz/ext.py
# Which is licensed under the same BSD 3-clause as this project and is copyrighted by Redhat.
import logging

from .blueprint import z_blueprint
from .log import PrefixFilter


class ManagementEndpoints:
    def __init__(self, app=None, prefix=z_blueprint.url_prefix, no_log=False):
        self.prefix = prefix
        self.no_log = no_log
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.register_blueprint(z_blueprint, url_prefix=self.prefix)
        if self.no_log:
            prefix_filter = PrefixFilter(self.prefix)
            loggers = logging.getLogger().manager.loggerDict  # Undocumented API
            # Gunicorn support
            if "gunicorn.access" in loggers:
                logger = logging.getLogger("gunicorn.access")
                logger.addFilter(prefix_filter)
