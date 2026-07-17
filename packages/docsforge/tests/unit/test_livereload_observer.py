"""Unit tests for the file-system observer selection in the live-reload server.

The server must prefer watchdog's native Observer (inotify/FSEvents/...) and
only fall back to the CPU-heavy PollingObserver when the native one cannot
be constructed.
"""
from __future__ import annotations

import watchdog.observers
import watchdog.observers.polling

from docsforge.livereload import LiveReloadServer


def _make_server(tmp_path, **kwargs):
    # bind_and_activate=False -> no real socket/port needed.
    return LiveReloadServer(
        builder=lambda: None,
        host="127.0.0.1",
        port=0,
        root=str(tmp_path),
        mount_path="/",
        **kwargs,
    )


class TestObserverSelection:
    def test_prefers_native_observer_by_default(self, tmp_path):
        """The default watcher must be the native Observer, not PollingObserver."""
        s = _make_server(tmp_path)
        assert isinstance(s.observer, watchdog.observers.Observer)
        assert not isinstance(s.observer, watchdog.observers.polling.PollingObserver)

    def test_falls_back_to_polling_observer_when_native_fails(self, tmp_path, mocker):
        """If the native Observer cannot be constructed, fall back to
        PollingObserver and honor the configured polling_interval."""
        mocker.patch.object(
            watchdog.observers, "Observer", side_effect=Exception("no inotify")
        )
        s = _make_server(tmp_path, polling_interval=2.0)
        assert isinstance(s.observer, watchdog.observers.polling.PollingObserver)
        assert s.observer.timeout == 2.0

    def test_observer_is_daemon_thread(self, tmp_path):
        """Regression: whichever observer is chosen, it must stay a daemon."""
        s = _make_server(tmp_path)
        assert s.observer.daemon is True
