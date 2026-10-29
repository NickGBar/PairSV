"""Resumable download for large Kaggle kernel-output files.

kaggle.kernels_output() reads the whole HTTP response into memory via
`requests.get(url, stream=True).content` with no retry/resume, so any dropped
connection on a large file loses the whole transfer. This re-issues
list_kernel_session_output for a fresh signed URL each attempt, streams to
disk incrementally, and resumes with an HTTP Range header from the last
written byte on failure.
"""
import argparse, json, os, sys, time
import requests
from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest


def fetch_output_urls(api: KaggleApi, owner: str, kernel: str):
    with api.build_kaggle_client() as kaggle:
        request = ApiListKernelSessionOutputRequest()
        request.user_name = owner
        request.kernel_slug = kernel
        request.page_size = 50
        response = kaggle.kernels.kernels_api_client.list_kernel_session_output(request)
    return {item.file_name: item.url for item in (response.files or [])}


def _object_identity(r, have):
    """(total_size, last_modified) fingerprint for the object being served.

    Kaggle's signed URLs expose no ETag, so Last-Modified + the total size
    parsed from Content-Range (206) or Content-Length (200) is what we have.
    Both must stay constant across resumed attempts, or we are at risk of
    stitching bytes from two different underlying object versions together.
    """
    last_modified = r.headers.get("Last-Modified")
    content_range = r.headers.get("Content-Range")  # "bytes X-Y/TOTAL"
    if content_range and "/" in content_range:
        total = int(content_range.rsplit("/", 1)[1])
    else:
        cl = r.headers.get("Content-Length")
        total = have + int(cl) if cl is not None else None
    return total, last_modified


def _confirmed_remote_total(url):
    """Independently ask the server for the object's current total size.

    Uses a tiny Range request so we get Content-Range's '.../TOTAL' rather than
    relying on a header that may be absent on whichever response we happen to
    have in hand. Returns (total, last_modified), either of which may be None
    if the server declines to say.
    """
    r = requests.get(url, stream=True, headers={"Range": "bytes=0-0"}, timeout=(15, 30))
    try:
        cr = r.headers.get("Content-Range", "")
        total = int(cr.rsplit("/", 1)[1]) if "/" in cr else None
        if total is None:
            cl = r.headers.get("Content-Length")
            total = int(cl) if cl is not None else None
        return total, r.headers.get("Last-Modified")
    finally:
        r.close()


def download_resumable(api, owner, kernel, file_name, dest, max_attempts=10):
    """Never deletes `dest` on ambiguous evidence -- only on a *positively
    confirmed* mismatch between two known totals. When identity can't be
    confirmed either way, it keeps the bytes on disk and retries; it never
    silently declares success on unconfirmed data either (see NOTE below)."""
    identity_path = dest + ".identity.json"
    expected_identity = None
    if os.path.exists(identity_path):
        expected_identity = tuple(json.load(open(identity_path)))

    for attempt in range(1, max_attempts + 1):
        urls = fetch_output_urls(api, owner, kernel)
        if file_name not in urls:
            raise SystemExit(f"file {file_name!r} not in kernel output; available: {list(urls)}")
        url = urls[file_name]
        have = os.path.getsize(dest) if os.path.exists(dest) else 0

        if have and expected_identity is not None and expected_identity[0] is not None:
            # We already know, from our own prior confirmed write, exactly how large
            # this object is -- check that directly instead of guessing from headers.
            if have >= expected_identity[0]:
                if have > expected_identity[0]:
                    raise SystemExit(
                        f"local file is LARGER ({have} bytes) than the confirmed remote total "
                        f"({expected_identity[0]} bytes) -- refusing to guess; inspect {dest} by hand"
                    )
                print(f"[attempt {attempt}] {have} bytes == previously confirmed total: already complete", flush=True)
                os.remove(identity_path)
                return have

        headers = {"Range": f"bytes={have}-"} if have else {}
        mode = "ab" if have else "wb"
        try:
            with requests.get(url, stream=True, headers=headers, timeout=(15, 60)) as r:
                if have and r.status_code == 200:
                    # server ignored Range (fresh signed URL may not preserve partial semantics) -> restart clean
                    have = 0
                    mode = "wb"
                elif have and r.status_code == 416:
                    # Ambiguous by itself -- ask independently rather than assume either way.
                    true_total, true_lm = _confirmed_remote_total(url)
                    if true_total is not None and true_total == have:
                        print(f"[attempt {attempt}] 416; independently confirmed total {true_total} == have: complete", flush=True)
                        if os.path.exists(identity_path):
                            os.remove(identity_path)
                        return have
                    if true_total is not None and true_total != have:
                        print(f"[attempt {attempt}] 416; CONFIRMED remote total {true_total} != local {have} "
                              f"(different object version) -- discarding local bytes and restarting", flush=True)
                        os.remove(dest)
                        expected_identity = None
                        continue
                    # true_total still unknown: do NOT delete, do NOT declare success. Just retry --
                    # a later attempt may get a server response that resolves the ambiguity.
                    print(f"[attempt {attempt}] 416 and remote total still unconfirmable; "
                          f"leaving {have} bytes on disk untouched and retrying", flush=True)
                    time.sleep(min(2 ** attempt, 30))
                    continue
                elif r.status_code not in (200, 206):
                    r.raise_for_status()

                total, last_modified = _object_identity(r, have)
                identity = (total, last_modified)
                if (expected_identity is not None and have > 0
                        and expected_identity[0] is not None and total is not None
                        and expected_identity[0] != total):
                    print(f"[attempt {attempt}] CONFIRMED total changed {expected_identity[0]} -> {total}; "
                          f"discarding {have} partial bytes and restarting rather than risk splicing "
                          f"two object versions together", flush=True)
                    os.remove(dest)
                    expected_identity = None
                    continue
                expected_identity = identity
                json.dump(list(identity), open(identity_path, "w"))

                with open(dest, mode) as f:
                    written = have
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        if not chunk:
                            continue
                        f.write(chunk)
                        written += len(chunk)
                print(f"[attempt {attempt}] wrote to {written} bytes (target {total}, "
                      f"last-modified {last_modified})", flush=True)
                if total is not None and written >= total:
                    os.remove(identity_path)
                    return written
                if total is None:
                    # NOTE: unknown length means we cannot positively confirm completeness;
                    # only accept this as done if the stream closed with no exception AND a
                    # subsequent request would 416 at this exact offset. Keep it simple and
                    # explicit rather than silently trusting an untriaged stream close.
                    confirmed_total, _ = _confirmed_remote_total(url)
                    if confirmed_total is not None and confirmed_total != written:
                        print(f"[attempt {attempt}] stream closed at {written} bytes but confirmed remote "
                              f"total is {confirmed_total}; treating as incomplete, will retry", flush=True)
                        continue
                    os.remove(identity_path)
                    return written
        except (requests.exceptions.RequestException, ConnectionError) as e:
            print(f"[attempt {attempt}] failed at {os.path.getsize(dest) if os.path.exists(dest) else 0} bytes: {e!r}", flush=True)
            time.sleep(min(2 ** attempt, 30))
            continue
    raise SystemExit(f"gave up after {max_attempts} attempts; partial file at {dest}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kernel", help="owner/kernel-slug")
    ap.add_argument("file_name")
    ap.add_argument("dest")
    ap.add_argument("--max-attempts", type=int, default=10)
    args = ap.parse_args()
    owner, kernel = args.kernel.split("/", 1)
    api = KaggleApi()
    api.authenticate()
    os.makedirs(os.path.dirname(os.path.abspath(args.dest)), exist_ok=True)
    size = download_resumable(api, owner, kernel, args.file_name, args.dest, args.max_attempts)
    print(f"DONE: {args.dest} ({size} bytes)")
