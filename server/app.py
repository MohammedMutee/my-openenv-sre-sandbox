"""
SRE Sandbox — OpenEnv-compliant HTTP Server.

Uses the ``HTTPEnvServer`` wrapper from openenv-core to automatically expose
``/health``, ``/metadata``, ``/schema``, ``/reset``, ``/step``, ``/state``
endpoints that pass ``openenv validate``.
"""

import logging

from fastapi import FastAPI

from openenv.core.env_server.http_server import HTTPEnvServer

from env import SREEnvironment
from models import SREAction, SREObservation

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SRE Sandbox",
    description="Autonomous SRE evaluation sandbox — OpenEnv compliant.",
    version="2.0.0",
)

# Wrap the environment in the OpenEnv HTTP server
server = HTTPEnvServer(
    env=SREEnvironment,
    action_cls=SREAction,
    observation_cls=SREObservation,
)

# Register all OpenEnv routes (/health, /metadata, /schema, /reset, /step, /state, /ws)
server.register_routes(app)


def main() -> None:
    """Entry point for ``pyproject.toml`` console script and ``__main__``."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-7s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
