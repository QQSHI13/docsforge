"""Unit tests for the file-system observer selection in the live-reload server.

The server must prefer watchdog's native Observer (inotify/FSEvents/...) and
only fall back to the CPU-heavy PollingObserver when the native one cannot
be constructed.
"""
from __future__ import annotations

import threading
import time

import watchdog.events
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


class TestEventFiltering:
    """Regression: read-only file events must not queue rebuilds."""

    def _event(self, event_type, src_path, is_directory=False):
        cls = {
            'opened': watchdog.events.FileOpenedEvent,
            'closed_no_write': watchdog.events.FileClosedNoWriteEvent,
            'closed': watchdog.events.FileClosedEvent,
            'created': watchdog.events.FileCreatedEvent,
            'modified': watchdog.events.FileModifiedEvent,
            'deleted': watchdog.events.FileDeletedEvent,
            'moved': watchdog.events.FileMovedEvent,
        }[event_type]
        if event_type == 'moved':
            return cls(src_path, dest_path=src_path)
        return cls(src_path)

    def test_ignores_open_and_close_no_write_events(self, tmp_path):
        s = _make_server(tmp_path)
        s._want_rebuild = False

        s._on_file_event(self._event('opened', str(tmp_path / 'file.md')))
        assert s._want_rebuild is False

        s._on_file_event(self._event('closed_no_write', str(tmp_path / 'file.md')))
        assert s._want_rebuild is False

        s._on_file_event(self._event('closed', str(tmp_path / 'file.md')))
        assert s._want_rebuild is False

    def test_modifying_events_trigger_rebuild(self, tmp_path):
        s = _make_server(tmp_path)

        for event_type in ('created', 'modified', 'deleted', 'moved'):
            s._want_rebuild = False
            s._on_file_event(self._event(event_type, str(tmp_path / 'file.md')))
            assert s._want_rebuild is True, f"{event_type} should trigger rebuild"

    def test_queued_rebuild_only_fires_for_modifying_events(self, tmp_path):
        s = _make_server(tmp_path)
        s._rebuilding = True

        s._on_file_event(self._event('opened', str(tmp_path / 'file.md')))
        s._on_file_event(self._event('closed_no_write', str(tmp_path / 'file.md')))
        assert s._pending_rebuild is False

        s._on_file_event(self._event('modified', str(tmp_path / 'file.md')))
        assert s._pending_rebuild is True
