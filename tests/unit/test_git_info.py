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


def _git(repo, *args):
    import subprocess

    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo, check=True, capture_output=True,
    )


def _git_date(repo, rev):
    import subprocess

    out = subprocess.run(
        ["git", "log", "-1", "--format=%cI", rev],
        cwd=repo, check=True, capture_output=True, text=True,
    )
    return out.stdout.strip()


def _fresh_caches():
    from docsforge import git_info

    git_info._PAGE_INFO_CACHE.clear()
    git_info._REPO_ROOT_CACHE.clear()


class TestRevParseMemo:
    def test_root_resolved_once_per_directory(self, tmp_path, monkeypatch):
        import subprocess

        from docsforge import git_info

        _fresh_caches()
        (tmp_path / "a.md").write_text("# A")
        (tmp_path / "b.md").write_text("# B")
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-qm", "init")

        real_run = subprocess.run
        calls = []

        def counting_run(cmd, **kwargs):
            if cmd[:2] == ["git", "rev-parse"]:
                calls.append(cmd)
            return real_run(cmd, **kwargs)

        monkeypatch.setattr("docsforge.git_info.subprocess.run", counting_run)
        assert git_info.get_git_page_info(str(tmp_path / "a.md")) is not None
        assert git_info.get_git_page_info(str(tmp_path / "b.md")) is not None
        assert len(calls) == 1


class TestPrefetch:
    def _repo_with_rename(self, root):
        (root / "docs").mkdir()
        (root / "docs" / "old.md").write_text("# Old")
        _git(root, "init", "-q")
        _git(root, "add", ".")
        _git(root, "commit", "-qm", "first")
        (root / "docs" / "old.md").rename(root / "docs" / "new.md")
        (root / "docs" / "other.md").write_text("# Other")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "rename and add")

    def test_prefetch_matches_lazy_and_follows_renames(self, tmp_path):
        from docsforge import git_info

        self._repo_with_rename(tmp_path)
        new = str(tmp_path / "docs" / "new.md")
        other = str(tmp_path / "docs" / "other.md")

        _fresh_caches()
        lazy_new = git_info.get_git_page_info(new)
        lazy_other = git_info.get_git_page_info(other)
        assert lazy_new is not None and lazy_other is not None
        # --follow sees through the rename: created is the first commit's
        # date (date strings have 1s precision, so compare against the
        # recorded commit date instead of updated).
        first_date = _git_date(tmp_path, "HEAD~1")
        assert lazy_new["created"] == first_date

        _fresh_caches()
        git_info.prefetch_git_page_info([new, other])
        assert git_info.get_git_page_info(new) == lazy_new
        assert git_info.get_git_page_info(other) == lazy_other

    def test_second_prefetch_spawns_no_git(self, tmp_path, monkeypatch):

        from docsforge import git_info

        self._repo_with_rename(tmp_path)
        _fresh_caches()
        paths = [str(tmp_path / "docs" / "new.md"), str(tmp_path / "docs" / "other.md")]
        git_info.prefetch_git_page_info(paths)

        def no_git(cmd, **kwargs):
            raise AssertionError(f"unexpected git call: {cmd}")

        monkeypatch.setattr("docsforge.git_info.subprocess.run", no_git)
        git_info.prefetch_git_page_info(paths)
        assert git_info.get_git_page_info(paths[0]) is not None
