"""Push the remaining v2 insert-size-variant kernels once a GPU slot is
confirmed free. Same corrected discipline established for Train40: never
push a slug more than once -- check status first, push exactly once, and if
that single push still fails, move to a fresh never-attempted suffix rather
than retry the one that just failed.
"""
import json, subprocess, time
from pathlib import Path

IN_FLIGHT = [
    "nicbaranov/deepsv-ms-v2-insertsize-removed",
    "nicbaranov/deepsv-ms-v2-insertsize-log1p",
]
QUEUE = [
    ("kaggle/deepsv-ms-v2-insertsize-clip99/source", "nicbaranov/deepsv-ms-v2-insertsize-clip99", ""),
    ("kaggle/deepsv-ms-v2-insertsize-robust/source", "nicbaranov/deepsv-ms-v2-insertsize-robust", ""),
]
MAX_SLOTS = 2


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def status(kernel_id):
    r = subprocess.run(["kaggle", "kernels", "status", kernel_id], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if "RUNNING" in out or "QUEUED" in out:
        return "RUNNING"
    if "COMPLETE" in out:
        return "COMPLETE"
    if "ERROR" in out or "CANCEL" in out:
        return "FAILED"
    return f"UNKNOWN({out[:80]})"


def set_slug(source_dir, base_id, suffix):
    meta_path = Path(source_dir) / "kernel-metadata.json"
    meta = json.loads(meta_path.read_text())
    new_id = f"{base_id}{suffix}"
    meta["id"] = new_id
    meta["title"] = new_id.split("/")[-1]
    meta_path.write_text(json.dumps(meta))
    return new_id


def push_once(source_dir):
    r = subprocess.run(["kaggle", "kernels", "push", "-p", source_dir], capture_output=True, text=True)
    out = r.stdout + r.stderr
    return "successfully pushed" in out, out


def next_suffix(s):
    return "b" if s == "" else chr(ord(s) + 1)


def main():
    launched = list(IN_FLIGHT)
    remaining = list(QUEUE)
    terminal = {}

    while remaining or any(status(k) == "RUNNING" for k in launched):
        for k in list(launched):
            if k in terminal:
                continue
            s = status(k)
            if s in ("COMPLETE", "FAILED"):
                terminal[k] = s
                log(f"{k} reached terminal state: {s}")

        active_slots = sum(1 for k in launched if terminal.get(k, status(k)) == "RUNNING")
        if remaining and active_slots < MAX_SLOTS:
            source_dir, base_id, suffix = remaining[0]
            kid = set_slug(source_dir, base_id, suffix)
            ok, out = push_once(source_dir)
            if ok:
                log(f"pushed {kid} (confirmed free slot: {active_slots}/{MAX_SLOTS} were active)")
                launched.append(kid)
                remaining.pop(0)
            else:
                log(f"push of fresh slug {kid} still failed (race?): {out.strip()[:200]} -- trying next suffix")
                remaining[0] = (source_dir, base_id, next_suffix(suffix))
        elif remaining:
            log(f"slots full ({active_slots}/{MAX_SLOTS}); {len(remaining)} still queued, not pushing yet")

        if not remaining and all(status(k) in ("COMPLETE", "FAILED") for k in launched):
            break
        time.sleep(120)

    log("ORCHESTRATION LOOP DONE")
    for k in launched:
        log(f"  {k}: {terminal.get(k, status(k))}")


if __name__ == "__main__":
    main()
