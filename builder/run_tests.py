"""Run the kit's practice test, surviving short platform outages.

    python3 builder/run_tests.py <agent_id> <run_cases.py arguments...>

Runs tools/run_cases.py. If it crashes (the platform answered 502/503/504 mid-run), waits until
the workspace's latest simulation is no longer running (polling every 30 s, at most 10 min),
then runs it once more. Never starts a second simulation while one is running.
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
POLL_S, MAX_WAIT_S = 30, 600


def latest_running() -> bool:
    """True while the newest simulation in the workspace is still running (or the API is unreachable)."""
    sys.path.insert(0, ROOT)
    import freya
    try:
        r = freya.api("GET", "/api/v2/simulations", workspaceId=freya.workspace_id())
        items = r.get("simulations") or r.get("items") or r
        return bool(items) and items[0].get("status") not in ("completed", "failed", "paused")
    except Exception:
        return True


def wait_until_idle() -> None:
    waited = 0
    while latest_running() and waited < MAX_WAIT_S:
        print(f"waiting for the platform's running simulation to finish ({waited} s)", flush=True)
        time.sleep(POLL_S)
        waited += POLL_S


def main(argv: list) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = [sys.executable, os.path.join(ROOT, "tools", "run_cases.py")] + argv[1:]
    for attempt in (1, 2):
        rc = subprocess.run(cmd, cwd=ROOT).returncode
        if rc == 0:
            return 0
        print(f"run_cases.py failed (exit {rc}) on attempt {attempt}; the platform may be unstable", flush=True)
        wait_until_idle()
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
