#!/bin/sh
# Fail fast on bad configuration, then hand off to the server.
#
# Why this exists: `uvicorn --workers N` runs a supervisor that respawns dead
# children. A configuration error raises at import time inside each worker, so
# the supervisor spawned, lost, and respawned workers forever while the
# container stayed "Up (unhealthy)" and never exited. An orchestrator saw a
# running container, not a crash, so it neither restarted nor alerted.
#
# Importing the settings module here surfaces the same error in PID 1, before
# any worker starts, and exits non-zero so the platform treats it as a failure.

set -eu

python - <<'PY'
import sys

try:
    from config.settings import settings
except Exception as exc:  # noqa: BLE001 - we re-raise as a readable message
    sys.stderr.write("\nConfiguration is invalid; refusing to start.\n\n")
    sys.stderr.write(f"{exc}\n\n")
    sys.stderr.write("Fix the environment variables above and redeploy. "
                     "See docs/deployment.md.\n")
    raise SystemExit(78)  # EX_CONFIG

sys.stderr.write(
    f"config ok: environment={settings.environment} "
    f"mock_integrations={settings.use_mock_integrations}\n"
)
PY

exec "$@"
