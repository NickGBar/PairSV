"""Regression test for the shard-9 test-extraction crash (2026-07-26):
RemoteCramSession.close() must swallow a cleanup-time OSError from a remote
HTTP-streamed CRAM handle rather than let it crash the whole extraction job,
and must always clear self._alignment even when close() raises."""
from __future__ import annotations

import warnings

from deepsv.multisample.extraction import RemoteCramSession


class _FakeAlignmentRaisesOnClose:
    def __init__(self):
        self.close_called = False

    def close(self):
        self.close_called = True
        raise OSError(29, "Closing failed: Illegal seek: 'https://example/fake.cram'")


class _FakeAlignmentClosesCleanly:
    def __init__(self):
        self.close_called = False

    def close(self):
        self.close_called = True


def _session():
    return RemoteCramSession("https://example/fake.cram", "/tmp/fake.crai", "/tmp/fake.fa")


def test_close_swallows_cleanup_time_oserror_and_clears_handle():
    session = _session()
    fake = _FakeAlignmentRaisesOnClose()
    session._alignment = fake
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        session.close()  # must not raise
    assert fake.close_called
    assert session._alignment is None
    assert any(issubclass(w.category, RuntimeWarning) for w in caught)


def test_close_still_closes_cleanly_when_no_error_occurs():
    session = _session()
    fake = _FakeAlignmentClosesCleanly()
    session._alignment = fake
    session.close()
    assert fake.close_called
    assert session._alignment is None


def test_close_on_already_closed_session_is_a_noop():
    session = _session()
    session._alignment = None
    session.close()  # must not raise
    assert session._alignment is None


def test_exit_does_not_raise_despite_a_close_time_error():
    """__exit__ (called directly, not via `with`, so no real open() runs
    first) must not itself raise even if close() would have -- the exact
    bug this test file was written for."""
    session = _session()
    session._alignment = _FakeAlignmentRaisesOnClose()
    session.__exit__(None, None, None)  # must not raise
    assert session._alignment is None


def test_exit_does_not_suppress_a_real_exception_from_the_with_block(monkeypatch):
    """A genuine exception raised inside the `with` block must still
    propagate -- __exit__ swallowing its OWN close-time error must not be
    confused with suppressing unrelated errors."""
    session = _session()
    monkeypatch.setattr(session, "open", lambda: setattr(session, "_alignment", _FakeAlignmentRaisesOnClose()))
    raised = False
    try:
        with session:
            raise ValueError("real error from inside the with-block")
    except ValueError:
        raised = True
    assert raised, "a genuine exception from inside the with-block must still propagate"
