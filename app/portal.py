"""Add /fraude without changing the existing application's routes or data.

Fraud initialization is lazy and contained: a missing fraud asset never takes
/recommander down. Healthcheck still reports a failed fraud deployment.
"""
import logging
from threading import Lock
from .config import Config
from .http import create_app as recommander_app


class Portal:
    def __init__(self, config, *, preview=False, **kwargs):
        self.recommander = recommander_app(config, **kwargs)
        self.config, self.kwargs = config, kwargs
        self.preview = preview
        self.fraud = None
        self.lock = Lock()

    def __call__(self, env, start_response):
        path = env.get("PATH_INFO", "")
        if path != "/fraude" and not path.startswith("/fraude/"):
            return self.recommander(env, start_response)
        try:
            if self.fraud is None:
                with self.lock:
                    if self.fraud is None:
                        from .fraud_http import FraudApplication
                        self.fraud = FraudApplication(self.config, preview=self.preview, **self.kwargs)
        except Exception:
            logging.exception("Fraud application initialization failed")
            start_response("503 Service Unavailable", [("Content-Type", "application/json"),
                           ("Cache-Control", "no-store"), ("Content-Length", "23")])
            return [b'{"error":"unavailable"}']
        return self.fraud(env, start_response)


def create_app(config=None, **kwargs):
    return Portal(config or Config.from_env(), **kwargs)
