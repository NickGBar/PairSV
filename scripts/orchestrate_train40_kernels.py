"""Serialize Train40 kernel pushes against Kaggle's 2-concurrent-GPU-session cap.

CONFIRMED PLATFORM BEHAVIOR (learned the hard way, three times): a kernel
push can be attempted AT MOST ONCE per slug, ever. If that single attempt
fails for ANY reason -- including a correctly-quota-rejected
"Maximum batch GPU session count" response -- the slug is permanently
unusable afterwards (`Kernel push error: Notebook not found` on every future
attempt, even once slots are free, even though `kaggle kernels list` shows
no such kernel exists). There is no "wait and retry the same slug" strategy
that works. The only correct approach is: never call push for a slug unless
a slot is already confirmed free by checking status first, and if a push
ever fails anyway (race with something else consuming the slot), mint a
brand-new, never-before-attempted suffix rather than retry.

This orchestrator therefore does not loop-retry pushes. It polls status of
the in-flight kernels, and the moment a slot is confirmed free, pushes the
next queued kernel exactly once under a fresh slug suffix. If that single
push still fails (e.g. a race), it appends the next unused suffix letter and
tries that new slug next cycle -- never the one that just failed.
"""
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (source_dir, base_id_without_suffix, current_suffix_already_tried_or_none)
IN_FLIGHT = [
    "nicbaranov/deepsv-ms-train40-ckpt-seed1",
    "nicbaranov/deepsv-ms-train40-ckpt-seed2",
]
QUEUE = [
    ("kaggle/deepsv-ms-train40-ckpt-seed3/source", "nicbaranov/deepsv-ms-train40-ckpt-seed3", ""),
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
    # "" is a valid starting state (a never-yet-attempted base slug); the first
    # fallback after it is "b", matching the convention used for the earlier
    # burned slugs. ord("") would raise, so handle it explicitly.
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
