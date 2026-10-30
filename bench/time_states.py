#!/usr/bin/env python3
"""Time DocsForge builds in three states, with repeats for a median.

  fresh   cold: no site/, no .docsforge/ cache
  warm    nothing changed since the last build
  incr-1  one Markdown file touched

Prints median / min / stdev of wall time and peak RSS per state.
"""
from __future__ import annotations

import argparse
import os
import resource
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


def run_once(site: Path, mode: str) -> tuple[float, float, int]:
    """Run one build in the given state; return (wall_s, cpu_s, rss_mb)."""
    if mode == "fresh":
        shutil.rmtree(site / "site", ignore_errors=True)
        shutil.rmtree(site / ".docsforge", ignore_errors=True)
    elif mode == "incr-1":
        md = sorted((site / "docs").rglob("*.md"))
        target = md[len(md) // 3]
        with target.open("a", encoding="utf-8") as fh:
            fh.write(f"\n<!-- touch {time.time_ns()} -->\n")

    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "docsforge", "build"],
        check=False, cwd=str(site), capture_output=True, text=True,
    )
    wall = time.perf_counter() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN)

    if proc.returncode != 0:
        print(proc.stderr[-2000:], file=sys.stderr)
        raise SystemExit(f"build failed rc={proc.returncode}")

    cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    return wall, cpu, after.ru_maxrss / 1024


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="project dir (docs/, docsforge.yml)")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--states", default="fresh,warm,incr-1")
    args = ap.parse_args()

    site = Path(args.site).resolve()
    print(f"site: {site}")
    print(f"cpus: {os.cpu_count()}")
    print()

    for state in args.states.split(","):
        walls, cpus, rsss = [], [], []
        for _ in range(args.reps):
            w, c, r = run_once(site, state)
            walls.append(w)
            cpus.append(c)
            rsss.append(r)
        print(
            f"{state:<8} wall median {statistics.median(walls):7.2f}s "
            f"min {min(walls):7.2f}s stdev {statistics.stdev(walls) if len(walls) > 1 else 0:5.2f} "
            f"| cpu {statistics.median(cpus):7.2f}s "
            f"| rss {statistics.median(rsss):6.0f} MB"
        )
        # A 'fresh' run leaves a cold cache; a warm run needs one, so make sure
        # the next state starts from a built state.
        if state == "fresh":
            run_once(site, "warm")


if __name__ == "__main__":
    main()
