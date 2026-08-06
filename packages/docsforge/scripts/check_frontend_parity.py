#!/usr/bin/env python3
"""Frontend parity check: does a fresh build from src match the committed output?

Usage:
  check_frontend_parity.py [--baseline DIR] [--whitelist FILE] [--area AREA]
                           [--include-icons] [--report-only]

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

The baseline checksum snapshot (``scripts/parity/baseline-*.sha256``) is kept
for reference; the primary comparison is the live committed templates dir.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMITTED = ROOT / "docsforge" / "templates"
sys.path.insert(0, str(ROOT / "scripts"))

import build_frontend  # noqa: E402  (monkeypatches OUT to build to a temp dir)

AREA_PREFIXES = {
    "templates": ("*.html",),
    "css": ("assets/stylesheets/*.css",),
    "js": ("assets/javascripts/bundle.min.js", "assets/javascripts/workers/*.js"),
    "sw": ("assets/javascripts/sw.js",),
    "icons": (".icons/",),
    "lunr": ("assets/javascripts/lunr/",),
    "katex": ("assets/katex/",),
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
    args = parser.parse_args()

    whitelist = load_whitelist(args.whitelist)

    tmp = Path(tempfile.mkdtemp(prefix="docsforge-parity-"))
    try:
        # Build into the temp dir by monkeypatching the module's output path.
        build_frontend.OUT = tmp
        build_args = []
        if not args.include_icons:
            build_args.append("--skip-icons")
        rc = build_frontend.main(build_args)
        if rc != 0:
            print(f"PARITY: frontend build failed (rc={rc})")
            return rc

        # Compare file sets.
        def files(base: Path) -> dict[str, str]:
            out: dict[str, str] = {}
            for p in base.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(base).as_posix()
                    if area_match(rel, args.area):
                        out[rel] = sha256(p)
            return out

        built = files(tmp)

        if args.baseline_snapshot is not None:
            reference = load_snapshot(args.baseline_snapshot)
            if args.area is None:
                # Without an area filter, exclude icons unless requested: the
                # default build skips them, so they would all report "removed".
                reference = {
                    rel: h for rel, h in reference.items()
                    if args.include_icons or not rel.startswith(".icons/")
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
              f"unexpected={len(unexpected)}")
        for label, items in (("added", added), ("removed", removed), ("changed", changed)):
            for rel in items[:10]:
                mark = "OK " if is_whitelisted(rel) else "!! "
                print(f"  {mark}{label}: {rel}")
            if len(items) > 10:
                print(f"  ... and {len(items) - 10} more {label}")

        if args.report_only:
            return 0
        if unexpected:
            print("PARITY: unexpected differences (see above); update the "
                  "whitelist only for intentional deltas.")
            return 1
        print("PARITY: OK — no unexpected differences")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
