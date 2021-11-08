# This code is inspired from:
# https://github.com/fedora-infra/flask-healthz/blob/7cda21963e379c10e5376c2cfbadf5de12ee1b6b/flask_healthz/log.py
# Which is licensed under the same BSD 3-clause as this project and is copyrighted by Redhat.
class PrefixFilter:
    def __init__(self, prefix):
        self.prefix = prefix

    def filter(self, record):
        url = None

        # Gunicorn logs
        url = record.args.get("U") if isinstance(record.args, dict) else None

        do_not_log = (
            url is not None
            and url.startswith(f"{self.prefix}/")
            and record.args.get("s") == 200
        )
        return 0 if do_not_log else 1
