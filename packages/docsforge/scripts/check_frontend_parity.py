#!/usr/bin/env python3
"""Frontend parity check: does a fresh build from src match the committed output?

Usage:
  check_frontend_parity.py [--baseline DIR] [--whitelist FILE] [--area AREA]
                           [--include-icons] [--report-only]
                           [--vs-ref REF] [--full]

- Builds the frontend from ``src/`` into a temporary directory (never touches
  the committed ``docsforge/templates/``).
- Diffs the build against the baseline (committed templates by default) and
  reports added / removed / changed files.
- Differences matching the whitelist (fnmatch patterns, one per line) are
  expected deltas and do not fail the check.
- Without ``--report-only``, exits non-zero when any non-whitelisted
  difference exists — this is the gate used per area during the Phase 3 swap.
- ``--area`` limits comparison to one area (templates, css, js, sw, icons,
  lunr, katex) so each swap step is verified in isolation.
- ``--baseline-snapshot FILE`` compares the fresh build against a pre-migration
  sha256 snapshot instead of the committed templates, reporting EVERY delta
  (no whitelist) so a swap cannot silently drop behavior that only existed in
  the old compiled output.
- ``--vs-ref REF`` compares the committed ``docsforge/templates/`` against the
  same directory at git ref REF (e.g. ``main``) — no build step. added = files
  we ship that REF does not, removed = files REF ships that we dropped,
  changed = files with different content. This is the output-level view of the
  migration.

The baseline checksum snapshot (``scripts/parity/baseline-*.sha256``) is kept
for reference; the primary comparison is the live committed templates dir.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMITTED = ROOT / "docsforge" / "templates"
sys.path.insert(0, str(ROOT / "scripts"))

import build_frontend  # noqa: E402  (monkeypatches OUT to build to a temp dir)

GIT_ROOT = subprocess.run(
    ["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"],
    capture_output=True, text=True, check=True,
).stdout.strip()
TEMPLATES_IN_REPO = "packages/docsforge/docsforge/templates"

AREA_PREFIXES = {
    "templates": ("*.html",),
    "css": ("assets/stylesheets/*.css",),
    "js": ("assets/javascripts/bundle.min.js", "assets/javascripts/workers/*.js"),
    "sw": ("assets/javascripts/sw.js",),
    "icons": (".icons/",),
    "lunr": ("assets/javascripts/lunr/",),
    "katex": ("assets/katex/",),
}

# DocsForge-specific markers that must survive every frontend rebuild. Hash
# parity only proves the build is reproducible; it cannot see a customization
# that was never ported into src/ (e.g. the X-DocsForge-Instant-Nav sender,
# which only existed in the old compiled bundle until it was lost in the JS
# swap). Each marker must appear in the fresh build's listed output file.
SENTINEL_MARKERS = {
    "assets/javascripts/bundle.min.js": [
        "X-DocsForge-Instant-Nav",   # SW tells instant-nav fetches from asset fetches
    ],
    "assets/javascripts/sw.js": [
        "docsforge-i18n",            # IndexedDB name for the locale preference
        "preferred_locale",          # locale key shared with the page
        "DOCSFORGE_SET_LOCALE",      # postMessage protocol page -> SW
        "docsforge-manifest-files",  # manifest file-set key
    ],
    "base.html": [
        "docsforge-i18n",
        "preferred_locale",
        "DOCSFORGE_SET_LOCALE",
        "DOCSFORGE_RELOAD_DETECTED",  # page tells SW a reload happened
    ],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def area_match(rel: str, area: str | None) -> bool:
    if area is None:
        return True
    for pattern in AREA_PREFIXES[area]:
        if fnmatch.fnmatch(rel, pattern) or rel.startswith(pattern):
            return True
    return False


def load_whitelist(path: Path | None) -> list[str]:
    if path is None:
        path = ROOT / "scripts" / "parity" / "whitelist.txt"
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def load_snapshot(path: Path) -> dict[str, str]:
    """Load a sha256sum snapshot ({path: hash}) from a baseline checksum file."""
    snap: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            snap[parts[1].strip()] = parts[0]
    return snap


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=COMMITTED)
    parser.add_argument(
        "--baseline-snapshot",
        type=Path,
        help="Compare the fresh build against a pre-migration sha256 snapshot "
             "(e.g. scripts/parity/baseline-2026-08-05.sha256) instead of the "
             "committed templates. Reports EVERY difference — no whitelist — so "
             "a swap cannot silently drop old behavior.",
    )
    parser.add_argument("--whitelist", type=Path)
    parser.add_argument("--area", choices=sorted(AREA_PREFIXES))
    parser.add_argument("--include-icons", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--full", action="store_true", help="Print every difference (default: first 10 per category)")
    parser.add_argument("--vs-ref", type=str, help="Compare committed templates against git ref REF (no build)")
    args = parser.parse_args()

    whitelist = load_whitelist(args.whitelist)

    tmp = Path(tempfile.mkdtemp(prefix="docsforge-parity-"))
    try:
        # Compare file sets.
        def files(base: Path) -> dict[str, str]:
            out: dict[str, str] = {}
            for p in base.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(base).as_posix()
                    if area_match(rel, args.area):
                        out[rel] = sha256(p)
            return out

        if args.vs_ref is not None:
            # Output-level view: committed templates vs the same dir at a git
            # ref (e.g. main). No build step — pure file diff of what ships.
            ref_dir = tmp / "ref"
            listing = subprocess.run(
                ["git", "-C", str(GIT_ROOT), "ls-tree", "-r", "--name-only", args.vs_ref, TEMPLATES_IN_REPO],
                capture_output=True, text=True, check=True,
            ).stdout.splitlines()
            prefix = TEMPLATES_IN_REPO + "/"
            for line in listing:
                rel = line[len(prefix):]
                if not args.include_icons and rel.startswith(".icons/"):
                    continue
                content = subprocess.run(
                    ["git", "-C", str(GIT_ROOT), "show", f"{args.vs_ref}:{line}"],
                    capture_output=True, check=True,
                ).stdout
                dst = ref_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(content)
            built = {
                rel: h for rel, h in files(COMMITTED).items()
                if args.include_icons or not rel.startswith(".icons/")
            }
            reference = files(ref_dir)
            missing_markers = []
        else:
            # Build into the temp dir by monkeypatching the module's output path.
            build_frontend.OUT = tmp
            build_args = []
            if not args.include_icons:
                build_args.append("--skip-icons")
            rc = build_frontend.main(build_args)
            if rc != 0:
                print(f"PARITY: frontend build failed (rc={rc})")
                return rc

            built = files(tmp)

        if args.vs_ref is None:
            if args.baseline_snapshot is not None:
                reference = load_snapshot(args.baseline_snapshot)
                if args.area is None:
                    # Without an area filter, exclude vendored assets the pipeline
                    # intentionally doesn't produce (icons unless requested, katex,
                    # pygments stylesheet, static images) — otherwise they would all
                    # report as "removed" and drown the signal.
                    reference = {
                        rel: h for rel, h in reference.items()
                        if (args.include_icons or not rel.startswith(".icons/"))
                        and not rel.startswith("assets/katex/")
                        and rel != "assets/stylesheets/pygments.css"
                        and not rel.startswith("assets/images/")
                    }
                else:
                    reference = {
                        rel: h for rel, h in reference.items()
                        if area_match(rel, args.area)
                    }
                # Snapshot mode ignores the whitelist by design: every delta against
                # the pre-migration output is reported so nothing is silently lost.
                whitelist = []
            else:
                reference = files(args.baseline)

        added = sorted(set(built) - set(reference))
        removed = sorted(set(reference) - set(built))
        changed = sorted(
            rel for rel in set(reference) & set(built) if reference[rel] != built[rel]
        )

        # Sentinel content check: DocsForge customization markers must survive
        # the build. Hash diffs can't catch a marker that was never ported into
        # src/, so scan the fresh build directly. (Not applicable in --vs-ref
        # mode, which has no build.)
        missing_markers: list[str] = []
        if args.vs_ref is None:
            for rel, markers in SENTINEL_MARKERS.items():
                if not area_match(rel, args.area):
                    continue
                path = tmp / rel
                if not path.exists():
                    missing_markers.append(f"{rel} (file missing)")
                    continue
                content = path.read_text(encoding="utf-8", errors="replace")
                for marker in markers:
                    if marker not in content:
                        missing_markers.append(f"{rel}: {marker}")

        def is_whitelisted(rel: str) -> bool:
            for pat in whitelist:
                # Patterns ending in '/' are directory prefixes.
                if pat.endswith("/"):
                    if rel.startswith(pat):
                        return True
                elif fnmatch.fnmatch(rel, pat):
                    return True
            return False

        unexpected = (
            [r for r in added if not is_whitelisted(r)]
            + [r for r in removed if not is_whitelisted(r)]
            + [r for r in changed if not is_whitelisted(r)]
        )

        print(f"PARITY area={args.area or 'all'} added={len(added)} "
              f"removed={len(removed)} changed={len(changed)} "
              f"unexpected={len(unexpected)} "
              f"markers-missing={len(missing_markers)}")
        for label, items in (("added", added), ("removed", removed), ("changed", changed)):
            shown = items if args.full else items[:10]
            for rel in shown:
                mark = "OK " if is_whitelisted(rel) else "!! "
                print(f"  {mark}{label}: {rel}")
            if not args.full and len(items) > 10:
                print(f"  ... and {len(items) - 10} more {label}")
        for missing in missing_markers:
            print(f"  !! missing marker: {missing}")

        if args.report_only:
            return 0
        if unexpected or missing_markers:
            print("PARITY: unexpected differences (see above); update the "
                  "whitelist only for intentional deltas.")
            return 1
        print("PARITY: OK — no unexpected differences")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
