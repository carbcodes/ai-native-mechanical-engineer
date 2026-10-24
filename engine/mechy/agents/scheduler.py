"""`mechy run`: run every ready task card, in parallel up to --jobs, respecting depends_on."""

from __future__ import annotations

import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait

from ..events import Events
from ..project import Project, git_commit
from . import cards as C
from .runner import run_task

_git_lock = threading.Lock()


def run_all(project: Project, jobs: int = 3, events: Events | None = None, max_rounds: int = 50,
            intake: bool = True) -> dict:
    """Digest pending inspiration first (so research cards see the notes), then run every ready card."""
    from .runner import digest_pending
    ev = events or Events(project.root, quiet=True)
    intake_res = digest_pending(project, ev) if intake else None
    jobs = max(1, jobs)
    ran: dict[str, str] = {}
    running: dict[Future, str] = {}
    invalid: dict[str, str] = {}
    launched = 0

    def state(cid: str) -> str:
        return C.read_status(project, cid)["state"]

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        while True:
            cards, invalid = C.load_cards(project)   # reload: tasks may add cards
            in_flight = set(running.values())
            for cid, card in cards.items():
                if cid in in_flight or len(running) >= jobs:
                    continue
                st = state(cid)
                if st in ("done", "failed", "running"):
                    continue
                deps = card["depends_on"]
                unknown = [d for d in deps if d not in cards]
                dstates = {d: state(d) for d in deps if d in cards}
                bad = [d for d, s in dstates.items() if s in ("failed", "blocked")] + unknown
                if bad:
                    if st != "blocked":
                        C.write_status(project, cid, "blocked", error=f"dependency not done: {', '.join(bad)}")
                        ev.emit("task.failed", task=cid, error=f"blocked by {', '.join(bad)}")
                        ran[cid] = "blocked"
                    continue
                if all(s == "done" for s in dstates.values()):
                    if launched >= max_rounds * jobs:
                        continue
                    C.write_status(project, cid, "queued")
                    fut = pool.submit(run_task, project, cid, ev, None, False)
                    running[fut] = cid
                    in_flight.add(cid)
                    launched += 1
            if not running:
                break
            done, _ = wait(list(running), return_when=FIRST_COMPLETED)
            for f in done:
                cid = running.pop(f)
                try:
                    r = f.result()
                    ran[cid] = "done" if r.get("ok") else "failed"
                except Exception as e:  # noqa: BLE001
                    C.write_status(project, cid, "failed", error=str(e))
                    ev.emit("task.failed", task=cid, error=str(e))
                    ran[cid] = "failed"
                if ran[cid] == "done":
                    with _git_lock:
                        git_commit(project.root, f"{cid} done")
    cards, invalid = C.load_cards(project)
    waiting = [cid for cid in cards if state(cid) == "queued"]
    failed = [k for k, v in ran.items() if v != "done"]
    return {"ok": not failed, "ran": ran, "failed": failed, "waiting": waiting, "invalid_cards": invalid,
            **({"intake": intake_res} if intake_res else {})}
