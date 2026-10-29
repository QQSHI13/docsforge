# Benchmarks

Engine benchmarks for DocsForge, compared against MkDocs + Material.

## Why a generated site

Benchmarking on a real repository measures that repository's content, not the
engine. `gen_site.py` produces a deterministic Markdown corpus with a mix that
actually exercises the hot paths — headings, CJK prose, Python code fences,
mermaid diagrams, tables, admonitions, inline math. Both engines build
byte-identical input with the same `markdown_extensions`, so a difference is the
engine, not the content.

Nothing here is a marketing number. A shared CI runner is noisy; use these to
spot regressions and to compare scenarios *within* one run.

## Running

```bash
pip install -e . && pip install mkdocs mkdocs-material

# Smoke test: 1 repetition, 51 pages, ~1 minute
python bench/run_bench.py --quick

# Default: 201 pages, 3 repetitions per scenario
python bench/run_bench.py --engine both --json bench/results.json

# Bigger site, more repetitions
python bench/run_bench.py --pages 500 --reps 5 --json bench/results.json

# DocsForge only, forcing a specific thread count
python bench/run_bench.py --engine docsforge --concurrency 4

# MkDocs installed in a different venv than DocsForge
python bench/run_bench.py --mkdocs-python /path/to/mkdocs-venv/bin/python
```

DocsForge and MkDocs are often installed in **different** interpreters (especially
when DocsForge is an editable checkout). `--mkdocs-python` points the MkDocs
side at whatever venv has `mkdocs` + `mkdocs-material`; without it, both engines
run in the current interpreter.

Generated sites and build output land in `bench/.site-*` and `bench/.work/`.
Both are safe to delete; nothing is committed from them.

## Scenarios

| Name | What it measures |
| --- | --- |
| `full` | Cold full build (cache removed). Run at small/medium/large page counts. |
| `incr-1` | Rebuild after touching one file, from a warm cache. |
| `incr-10` | Rebuild after touching ten files. |
| `nocache` | DocsForge full build with `.docsforge/` deleted each run, isolating cache cost. |
| `concurrency` | DocsForge at `concurrency: 1` vs all cores — shows CPU scaling. |
| `determinism` | Two cold builds, tree SHA-256 compared. Catches nondeterministic output. |

MkDocs has no incremental mode, so its `incr-*` rows are full rebuilds. That is
the point of the row: it shows what a rebuild costs you when the engine has no
cache.

## Metrics

Every run records:

- **wall_s** — `perf_counter` around the subprocess.
- **cpu_s** — user+sys CPU seconds from `getrusage(RUSAGE_CHILDREN)`, so it
  catches work that parallelises well (wall drops, CPU does not).
- **peak_rss_mb** — child high-water RSS after the run. Note this is a
  monotonic high-water mark across all children; the report shows the absolute
  value, which is the honest upper bound.
- **html_pages** / **output_mb** — sanity checks that both engines built the
  same site. A page-count mismatch means the comparison is invalid.

Averages are median, plus min and stdev. Median, not mean, because a single
noisy run should not move the headline number.

## Reading the output

The harness prints an environment block first — CPU model, core count, Python
and library versions, 1-minute load average. **Check the load average before
trusting any number.** A `loadavg_1m` above `cpu_count` means something else is
using the machine and the timings are garbage.

Then each scenario's wall/CPU/RSS/output, then a comparison table:

```
  scenario             docsforge       mkdocs    ratio
  ------------------------------------------------------
  full                     12.34s       15.67s    0.79x
  incr-1                    0.42s        9.88s    0.04x
```

`ratio` below 1.0 means DocsForge was faster for that scenario. Only compare
rows from the *same* run — cross-run comparisons on a shared runner are not
meaningful.

## CI

`.github/workflows/bench.yml` runs on `workflow_dispatch` and weekly. It is a
single job with no matrix and no parallel steps, so nothing competes for CPU.
It runs a deterministic-input check, a `--quick` smoke test, then the full
benchmark, and uploads `bench/results*.json` plus a text summary as artifacts.

## What this harness does not do

- No profiling. Use `cProfile` for where time goes inside a build; this measures
  the outside.
- No statistical significance test. With `--reps 3` on a noisy runner, a 10%
  difference is not distinguishable from noise. Raise `--reps` for real claims.
- No MkDocs `--strict` handling. Strict mode aborts on the pre-existing link
  warnings in some real sites, so the harness builds without it.
