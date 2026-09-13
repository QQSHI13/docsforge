"""Unit tests for docsforge.git_info symlink handling."""
from __future__ import annotations

import os

from docsforge.git_info import _get_git_page_info


class TestRelpathSymlinks:
    """Regression: relpath through a symlink must resolve to the real path."""

    def test_symlinked_docs_dir_still_matches_git_log(self, tmp_path, monkeypatch):
        import subprocess

        real_docs = tmp_path / "real_docs"
        real_docs.mkdir()
        (real_docs / "page.md").write_text("# P")
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
            cwd=tmp_path,
            check=True,
        )

        link = tmp_path / "link_docs"
        link.symlink_to(real_docs, target_is_directory=True)

        file_path = str(link / "page.md")
        captured: dict[str, str] = {}

        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "rev-parse"]:
                return subprocess.CompletedProcess(cmd, 0, stdout=f"{tmp_path}\n", stderr="")
            if cmd[:2] == ["git", "log"]:
                captured["rel_path"] = cmd[-1]
                return subprocess.CompletedProcess(cmd, 0, stdout="2024-01-02T03:04:05+00:00\n", stderr="")
            raise AssertionError(f"unexpected git call: {cmd}")

        monkeypatch.setattr("docsforge.git_info.subprocess.run", fake_run)
        info = _get_git_page_info(file_path)
        assert info is not None
        # Must be relative to the REAL path, not "link_docs/page.md".
        assert captured["rel_path"] == os.path.join("real_docs", "page.md")
