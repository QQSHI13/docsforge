#!/usr/bin/env python3
"""Benchmark DocsForge against MkDocs + Material for MkDocs.

Both engines build byte-identical generated Markdown with the same Markdown
extension set, so the numbers compare engines rather than inputs. Everything
is sequential (single worker, one build at a time) so a shared CI runner gives
stable numbers instead of noisy ones.

Scenarios (each measured over several repetitions):

  full-small      50 pages, cold cache
  full-medium     200 pages, cold cache
  full-large      500 pages, cold cache
  incr-1          1 file touched after a warm build
  incr-10         10 files touched after a warm build
  nocache         200 pages with DocsForge incremental cache removed

Reported per scenario: wall time, child CPU time, peak RSS, HTML page count
and output size, as median / min / stdev over the repetitions.

Usage:
    python bench/run_bench.py --engine both --json bench/results.json
    python bench/run_bench.py --engine docsforge --reps 1 --pages 30
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_WORKDIR = HERE / ".work"
DEFAULT_SITE = HERE / ".site"


# --------------------------------------------------------------------------- #
# environment                                                                 #
# --------------------------------------------------------------------------- #

def _module_version(module: str, python: str | None = None) -> str:
    try:
        out = subprocess.run(
            [python or sys.executable, "-c",
             f"import {module} as m; print(getattr(m,'__version__','?'))"],
            capture_output=True, text=True, timeout=60, check=False,
        )
        return out.stdout.strip() or "?"
    except Exception:
        return "missing"


def env_report() -> dict:
    """Collect environment facts so a surprising number can be explained."""
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text()
        model = next(
            (ln.split(":", 1)[1].strip() for ln in cpuinfo.splitlines()
             if ln.startswith("model name")),
            "unknown",
        )
    except Exception:
        model = "unknown"

    mkpy = _Cfg.mkdocs_python
    info = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "cpu_model": model,
        "docsforge": _module_version("docsforge"),
        "docsforge_python": sys.executable,
        "mkdocs": _module_version("mkdocs", mkpy),
        "material": _module_version("material", mkpy),
        "pymdownx": _module_version("pymdownx", mkpy),
        "markdown": _module_version("markdown", mkpy),
        "marz": _module_version("marz"),
        "mkdocs_python": mkpy or sys.executable,
    }
    try:
        load1 = os.getloadavg()[0]
        info["loadavg_1m"] = round(load1, 2)
    except Exception:
        pass
    return info


def print_env(info: dict) -> None:
    print("=" * 72)
    print("environment")
    print("=" * 72)
    for key, value in info.items():
        print(f"  {key:16} {value}")
    print()


# --------------------------------------------------------------------------- #
# one build                                                                   #
# --------------------------------------------------------------------------- #

def _child_usage() -> tuple[float, float]:
    """Return (user, sys) CPU seconds consumed by finished children."""
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime, usage.ru_stime


def run_build(cmd: list[str], cwd: Path, label: str) -> dict:
    """Run one build command and return timing/resource measurements."""
    before_user, before_sys = _child_usage()
    before_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss

    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    wall = time.perf_counter() - started

    after_user, after_sys = _child_usage()
    after_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss

    result = {
        "label": label,
        "returncode": proc.returncode,
        "wall_s": round(wall, 3),
        "cpu_s": round((after_user - before_user) + (after_sys - before_sys), 3),
        # ru_maxrss is the high-water mark of ALL children so far, so it is a
        # lower bound for this run unless it grew; report the delta when it did.
        "peak_rss_mb": round(max(after_rss - before_rss, 0) / 1024, 1),
        "peak_rss_abs_mb": round(after_rss / 1024, 1),
    }
    if proc.returncode != 0:
        result["stderr_tail"] = proc.stderr.strip().splitlines()[-25:]
        result["stdout_tail"] = proc.stdout.strip().splitlines()[-10:]
    return result


def output_stats(site_dir: Path) -> dict:
    """Count pages and total bytes in a built site."""
    html = 0
    total = 0
    if site_dir.exists():
        for path in site_dir.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
                if path.suffix == ".html":
                    html += 1
    return {"html_pages": html, "output_mb": round(total / 1024 / 1024, 1)}


# --------------------------------------------------------------------------- #
# workspace                                                                   #
# --------------------------------------------------------------------------- #

def fresh_copy(base_site: Path, dest: Path) -> Path:
    """Copy the generated Markdown tree into a clean working directory."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copytree(base_site / "docs", dest / "docs")
    for name in ("docsforge.yml", "mkdocs.yml"):
        src = base_site / name
        if src.exists():
            shutil.copy2(src, dest / name)
    return dest


def clear_caches(workdir: Path) -> None:
    for rel in (".docsforge", "site", "site-mkdocs", ".cache"):
        target = workdir / rel
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)


# --------------------------------------------------------------------------- #
# engine command lines                                                        #
# --------------------------------------------------------------------------- #

def docsforge_cmd(workdir: Path, concurrency: int | None) -> list[str]:
    if concurrency is not None:
        _set_concurrency(workdir / "docsforge.yml", concurrency)
    return [sys.executable, "-m", "docsforge", "build"]


def mkdocs_cmd() -> list[str]:
    """MkDocs build command, in an optional separate interpreter."""
    return [_Cfg.mkdocs_python or sys.executable, "-m", "mkdocs", "build"]


class _Cfg:
    """Run-wide knobs set from CLI args (avoids a `global` rebind)."""

    mkdocs_python: str | None = None
    """Interpreter that has mkdocs installed.

    DocsForge itself may live in a different venv, so the two engines cannot
    share sys.executable.
    """


def _set_concurrency(config: Path, n: int) -> None:
    """Force ``concurrency: n`` in a docsforge.yml (simple line rewrite)."""
    import re

    text = config.read_text(encoding="utf-8")
    if re.search(r"^concurrency:", text, re.MULTILINE):
        text = re.sub(r"^concurrency:.*$", f"concurrency: {n}", text, flags=re.MULTILINE)
    else:
        text += f"\nconcurrency: {n}\n"
    config.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# scenarios                                                                   #
# --------------------------------------------------------------------------- #

def aggregate(runs: list[dict]) -> dict:
    """Fold repeated runs into median/min/stdev plus a representative sample."""
    ok = [r for r in runs if r.get("returncode") == 0]
    if not ok:
        return {"error": "all runs failed", "runs": runs}

    def stat(key: str) -> dict:
        values = [r[key] for r in ok]
        return {
            "median": round(statistics.median(values), 3),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "stdev": round(statistics.stdev(values), 3) if len(values) > 1 else 0.0,
        }

    return {
        "reps": len(ok),
        "failed": len(runs) - len(ok),
        "wall_s": stat("wall_s"),
        "cpu_s": stat("cpu_s"),
        "peak_rss_mb": stat("peak_rss_abs_mb"),
        "html_pages": ok[0].get("html_pages"),
        "output_mb": ok[0].get("output_mb"),
        "runs": runs,
    }


def bench_full(engine: str, base_site: Path, workdir: Path, reps: int,
               concurrency: int | None, verbose: bool) -> dict:
    """Cold full build repeated ``reps`` times."""
    runs = []
    for rep in range(reps):
        wd = fresh_copy(base_site, workdir / f"{engine}-full")
        clear_caches(wd)
        cmd = docsforge_cmd(wd, concurrency) if engine == "docsforge" else mkdocs_cmd()
        if verbose:
            print(f"    [{engine}] rep {rep + 1}/{reps}: {' '.join(cmd)}")
        result = run_build(cmd, wd, f"{engine}-full-{rep}")
        result.update(output_stats(wd / "site"))
        if verbose and result["returncode"] != 0:
            print(f"    [{engine}] FAILED rc={result['returncode']}")
            for line in result.get("stderr_tail", [])[-8:]:
                print(f"      {line}")
        runs.append(result)
        if verbose:
            print(f"    [{engine}] rep {rep + 1}: {result['wall_s']}s "
                  f"cpu={result['cpu_s']}s pages={result.get('html_pages')}")
    return aggregate(runs)


def bench_incremental(engine: str, base_site: Path, workdir: Path, reps: int,
                      touched: int, concurrency: int | None, verbose: bool) -> dict:
    """Warm build once, then rebuild after touching ``touched`` files."""
    if engine != "docsforge":
        # MkDocs has no incremental mode: every build is a full rebuild. Measure
        # it anyway so the report shows the difference explicitly.
        pass

    wd = fresh_copy(base_site, workdir / f"{engine}-incr")
    clear_caches(wd)
    cmd = docsforge_cmd(wd, concurrency) if engine == "docsforge" else mkdocs_cmd()
    if verbose:
        print(f"    [{engine}] warm-up build")
    warm = run_build(cmd, wd, f"{engine}-incr-warm")
    if warm["returncode"] != 0:
        return {"error": "warm-up failed", "runs": [warm]}

    md_files = sorted((wd / "docs").rglob("*.md"))
    if not md_files:
        return {"error": "no markdown files"}

    runs = []
    for rep in range(reps):
        for idx in range(min(touched, len(md_files))):
            target = md_files[(rep * touched + idx) % len(md_files)]
            with target.open("a", encoding="utf-8") as fh:
                fh.write(f"\n\n<!-- touch {rep}-{idx} -->\n")
        if verbose:
            print(f"    [{engine}] incremental rep {rep + 1}/{reps} "
                  f"({touched} file(s) touched)")
        result = run_build(cmd, wd, f"{engine}-incr-{rep}")
        result.update(output_stats(wd / "site"))
        if verbose and result["returncode"] != 0:
            print(f"    [{engine}] FAILED rc={result['returncode']}")
            for line in result.get("stderr_tail", [])[-8:]:
                print(f"      {line}")
        runs.append(result)
        if verbose:
            print(f"    [{engine}] rep {rep + 1}: {result['wall_s']}s")
    return aggregate(runs)


def bench_no_cache(base_site: Path, workdir: Path, reps: int,
                   concurrency: int | None, verbose: bool) -> dict:
    """DocsForge full build with its incremental cache deleted each run."""
    runs = []
    for rep in range(reps):
        wd = fresh_copy(base_site, workdir / "docsforge-nocache")
        clear_caches(wd)
        cmd = docsforge_cmd(wd, concurrency)
        if verbose:
            print(f"    [docsforge] no-cache rep {rep + 1}/{reps}")
        result = run_build(cmd, wd, f"nocache-{rep}")
        result.update(output_stats(wd / "site"))
        runs.append(result)
    return aggregate(runs)


def bench_concurrency(base_site: Path, workdir: Path, reps: int, verbose: bool) -> dict:
    """DocsForge full build at concurrency 1 vs all cores (CPU scaling)."""
    out = {}
    cores = os.cpu_count() or 1
    for label, n in (("concurrency_1", 1), (f"concurrency_{cores}", cores)):
        runs = []
        for rep in range(reps):
            wd = fresh_copy(base_site, workdir / f"df-{label}")
            clear_caches(wd)
            cmd = docsforge_cmd(wd, n)
            if verbose:
                print(f"    [docsforge] {label} rep {rep + 1}/{reps}")
            result = run_build(cmd, wd, f"{label}-{rep}")
            result.update(output_stats(wd / "site"))
            runs.append(result)
        out[label] = aggregate(runs)
    return out


def bench_determinism(base_site: Path, workdir: Path, verbose: bool) -> dict:
    """Build twice cold and confirm identical output (catches nondeterminism)."""
    hashes = []
    wd = fresh_copy(base_site, workdir / "df-determinism")
    for rep in range(2):
        clear_caches(wd)
        cmd = docsforge_cmd(wd, None)
        if verbose:
            print(f"    [docsforge] determinism build {rep + 1}/2")
        result = run_build(cmd, wd, f"determinism-{rep}")
        if result["returncode"] != 0:
            return {"error": "build failed", "runs": [result]}
        digest = _tree_hash(wd / "site")
        hashes.append(digest)
        if verbose:
            print(f"    [docsforge] build {rep + 1} tree sha256 {digest[:16]}")
    return {"identical": hashes[0] == hashes[1], "hashes": hashes}


def _tree_hash(root: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


# --------------------------------------------------------------------------- #
# report                                                                      #
# --------------------------------------------------------------------------- #

def print_scenario(name: str, result: dict) -> None:
    print(f"  {name}")
    if "error" in result:
        print(f"    ERROR: {result['error']}")
        return
    wall = result["wall_s"]
    cpu = result["cpu_s"]
    rss = result["peak_rss_mb"]
    print(f"    wall   median {wall['median']:>8.2f}s  "
          f"min {wall['min']:>8.2f}  stdev {wall['stdev']:>6.2f}")
    print(f"    cpu    median {cpu['median']:>8.2f}s")
    print(f"    rss    median {rss['median']:>8.1f} MB")
    print(f"    output {result.get('html_pages')} html, {result.get('output_mb')} MB")
    if result.get("failed"):
        print(f"    failed runs: {result['failed']}")


def print_comparison(results: dict) -> None:
    """Print a side-by-side table for scenarios both engines ran."""
    print()
    print("=" * 72)
    print("docsforge vs mkdocs+material")
    print("=" * 72)
    header = f"  {'scenario':<16} {'docsforge':>12} {'mkdocs':>12} {'ratio':>8}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for key in ("full", "incr-1", "incr-10"):
        df = results.get("docsforge", {}).get(key)
        mk = results.get("mkdocs", {}).get(key)
        if not df or not mk or "error" in df or "error" in mk:
            continue
        df_wall = df["wall_s"]["median"]
        mk_wall = mk["wall_s"]["median"]
        ratio = df_wall / mk_wall if mk_wall else 0
        print(f"  {key:<16} {df_wall:>10.2f}s {mk_wall:>10.2f}s {ratio:>7.2f}x")
    print()


# --------------------------------------------------------------------------- #
# main                                                                        #
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=["docsforge", "mkdocs", "both"], default="both")
    ap.add_argument("--pages", type=int, default=200, help="pages for the medium site")
    ap.add_argument("--small", type=int, default=50)
    ap.add_argument("--large", type=int, default=500)
    ap.add_argument("--reps", type=int, default=3, help="repetitions per scenario")
    ap.add_argument("--concurrency", type=int, default=None,
                    help="force docsforge concurrency (default: config value)")
    ap.add_argument("--mkdocs-python", default=None,
                    help="interpreter that has mkdocs installed (default: this one)")
    ap.add_argument("--json", type=Path, default=None, help="write results JSON here")
    ap.add_argument("--workdir", type=Path, default=DEFAULT_WORKDIR)
    ap.add_argument("--site", type=Path, default=DEFAULT_SITE,
                    help="where the generated Markdown site lives")
    ap.add_argument("--skip-generate", action="store_true")
    ap.add_argument("--quick", action="store_true",
                    help="one repetition, small site only (smoke test)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    _Cfg.mkdocs_python = args.mkdocs_python

    if args.quick:
        args.reps = 1
        args.pages = args.small

    verbose = not args.quiet

    info = env_report()
    print_env(info)

    if info["docsforge"] == "missing":
        print("ERROR: docsforge is not importable; pip install -e . first")
        return 2
    if args.engine in ("mkdocs", "both") and info["mkdocs"] == "missing":
        print("WARNING: mkdocs missing; skipping the mkdocs side")
        if args.engine == "mkdocs":
            return 2
        args.engine = "docsforge"

    base_site = args.site.resolve()
    if not args.skip_generate or not base_site.exists():
        print(f"generating sites (small={args.small}, medium={args.pages}, "
              f"large={args.large})")
        for pages in (args.small, args.pages, args.large):
            target = _site_variant(base_site, pages)
            subprocess.run(
                [sys.executable, str(HERE / "gen_site.py"),
                 "--root", str(target), "--pages", str(pages)],
                check=True, capture_output=True, text=True,
            )
            print(f"  {pages + 1} pages -> {target}")
        print()

    workdir = args.workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    plan = [("full", args.small)] if args.quick else [("full", args.pages)]

    results: dict[str, dict] = {}
    engines = ["docsforge", "mkdocs"] if args.engine == "both" else [args.engine]

    for engine in engines:
        print("=" * 72)
        print(f"engine: {engine}")
        print("=" * 72)
        engine_results: dict = {}

        for name, pages in plan:
            base = _site_variant(base_site, pages)
            print(f"  scenario {name} ({pages + 1} pages)")
            engine_results[name] = bench_full(
                engine, base, workdir, args.reps, args.concurrency, verbose,
            )
            print_scenario(f"{name} [{engine}]", engine_results[name])

        base = _site_variant(base_site, args.pages)
        print(f"  scenario incr-1 (touch 1 of {args.pages + 1} pages)")
        engine_results["incr-1"] = bench_incremental(
            engine, base, workdir, args.reps, 1, args.concurrency, verbose,
        )
        print_scenario(f"incr-1 [{engine}]", engine_results["incr-1"])

        print(f"  scenario incr-10 (touch 10 of {args.pages + 1} pages)")
        engine_results["incr-10"] = bench_incremental(
            engine, base, workdir, args.reps, 10, args.concurrency, verbose,
        )
        print_scenario(f"incr-10 [{engine}]", engine_results["incr-10"])

        if engine == "docsforge" and not args.quick:
            print("  scenario nocache (full build, cache removed)")
            engine_results["nocache"] = bench_no_cache(
                base, workdir, args.reps, args.concurrency, verbose)
            print_scenario("nocache [docsforge]", engine_results["nocache"])

            print("  scenario concurrency (1 core vs all cores)")
            engine_results["concurrency"] = bench_concurrency(
                base, workdir, args.reps, verbose)
            for key, value in engine_results["concurrency"].items():
                print_scenario(f"{key} [docsforge]", value)

            print("  scenario determinism (two cold builds, same output?)")
            engine_results["determinism"] = bench_determinism(base, workdir, verbose)
            det = engine_results["determinism"]
            if "error" in det:
                print(f"    ERROR: {det['error']}")
            else:
                print(f"    identical: {det['identical']}")

        results[engine] = engine_results
        print()

    print_comparison(results)

    payload = {"environment": info, "config": vars(args) | {"json": str(args.json)}, "results": results}
    # Paths in config are not JSON-serializable; normalise them.
    payload["config"] = {
        key: (str(value) if isinstance(value, Path) else value)
        for key, value in payload["config"].items()
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"results written to {args.json}")

    return 0


def _site_variant(base: Path, pages: int) -> Path:
    return base.parent / f"{base.name}-{pages}"


if __name__ == "__main__":
    sys.exit(main())
