"""Run the kit's practice test, surviving platform outages. The kit files are not modified.

    python3 builder/run_tests.py <agent_id> <run_cases.py arguments...>

- Runs tools/run_cases.py in this process with every Freya API call and bank call retried on
  5xx errors and timeouts (3 tries, 10 s apart). The kit's freya.py does not retry.
- Never stops a running test. If run_cases still fails, waits until the workspace has no running
  simulation, then runs once more.
- A simulation of ours that stays "running" with no update for 15 minutes (twice the 7-minute call
  limit) is stuck: it is cancelled (POST /api/v2/simulations/{id}/cancel), since the kit's client
  would wait for it forever and every later simulation would queue behind it. A watchdog thread
  checks this every minute while run_cases.py runs, not only after a failure.
"""
import datetime
import os
import runpy
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TRIES, PAUSE_S = 3, 10
POLL_S, MAX_WAIT_S, STUCK_S, WATCH_S = 30, 900, 15 * 60, 60
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))


def transient(e: Exception) -> bool:
    text = str(e)
    return any(code in text for code in ("-> 500", "-> 502", "-> 503", "-> 504", "timed out", "Connection", "URLError"))


def with_retry(fn):
    def wrapped(*args, **kwargs):
        for attempt in range(1, TRIES + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:  # retried only when the platform looks unavailable
                if attempt == TRIES or not transient(e):
                    raise
                print(f"platform error ({str(e)[:80]}); retry {attempt} in {PAUSE_S} s", flush=True)
                time.sleep(PAUSE_S)
    return wrapped


def patch_clients() -> None:
    import freya
    import score
    if not getattr(freya.api, "_retrying", False):
        freya.api = with_retry(freya.api)
        freya.api._retrying = True
    if not getattr(score.http, "_retrying", False):
        score.http = with_retry(score.http)
        score.http._retrying = True


def simulations() -> list:
    import freya
    r = freya.api("GET", "/api/v2/simulations", workspaceId=freya.workspace_id(), limit=10)
    items = r.get("simulations") or r.get("items") or r
    return items if isinstance(items, list) else []


def age_s(stamp: str) -> float:
    try:
        t = datetime.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds()
    except ValueError:
        return 0.0


def stuck(sims: list) -> list:
    return [s for s in sims if s.get("status") == "running" and age_s(s.get("updatedAt")) > STUCK_S]


def cancel(s: dict) -> None:
    import freya
    print(f"simulation {s.get('id')} has not moved for {age_s(s.get('updatedAt')) / 60:.0f} min: cancelling it", flush=True)
    try:
        freya.api("POST", f"/api/v2/simulations/{s.get('id')}/cancel", {})
    except Exception as e:
        print(f"cancel failed: {str(e)[:80]}", flush=True)


def watchdog(stop: threading.Event) -> None:
    while not stop.wait(WATCH_S):
        try:
            for s in stuck(simulations()):
                cancel(s)
        except Exception as e:  # a listing error during an outage: try again next minute
            print(f"watchdog: cannot list simulations ({str(e)[:60]})", flush=True)


def wait_until_idle() -> None:
    import freya
    waited = 0
    while waited < MAX_WAIT_S:
        try:
            running = [s for s in simulations() if s.get("status") not in ("completed", "failed", "paused", "cancelled")]
        except Exception as e:
            print(f"cannot list simulations ({str(e)[:60]}); waiting", flush=True)
            running = [None]
        if not running:
            return
        for s in stuck([s for s in running if s]):
            cancel(s)
        print(f"waiting for the running simulation to finish ({waited} s)", flush=True)
        time.sleep(POLL_S)
        waited += POLL_S


def run_once(args: list) -> int:
    sys.argv = [os.path.join(ROOT, "tools", "run_cases.py")] + args
    try:
        runpy.run_path(sys.argv[0], run_name="__main__")
        return 0
    except SystemExit as e:
        return int(e.code or 0) if isinstance(e.code, int) else 1
    except Exception as e:
        print(f"run_cases.py failed: {str(e)[:200]}", flush=True)
        return 1


def main(argv: list) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    os.chdir(ROOT)
    patch_clients()
    stop = threading.Event()
    threading.Thread(target=watchdog, args=(stop,), daemon=True).start()
    rc = 1
    try:
        for attempt in (1, 2):
            rc = run_once(argv[1:])
            if rc == 0:
                return 0
            print(f"attempt {attempt} failed; the platform may be unstable", flush=True)
            wait_until_idle()
        return rc
    finally:
        stop.set()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
