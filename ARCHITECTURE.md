# DocsForge Architecture Decisions

**Date**: 2026-05-09  
**Status**: Draft — skeleton phase

---

## 1. Why repackage instead of fork?

**Context**: ProperDocs already supports both `mkdocs.*` and `properdocs.*` entrypoints. Material for MkDocs registers itself under `mkdocs.*` themes and `material.*` plugins. This means Material works with ProperDocs today without any code changes.

**Decision**: DocsForge is a **packaging and CLI layer**, not a code fork.

**Consequences**:
- We inherit ProperDocs bug fixes automatically via `pip install --upgrade properdocs`.
- We inherit Material theme updates via `pip install --upgrade mkdocs-material`.
- Our maintenance burden is tiny: CLI wrapper + config loader + auto-register logic.
- If ProperDocs or Material go fully unmaintained later, we can still fork then.

---

## 2. Why keep the plugin system?

**Context**: An early idea was a "Dense Pipeline" that eliminated plugins entirely and rewrote Material's features as build steps. This would remove plugin hook overhead.

**Decision**: **Keep the plugin system alive.** Auto-register Material plugins instead of rewriting them.

**Rationale**:
- Rewriting blog, tags, privacy, social, and search as non-plugin build steps would be a massive effort with no user-visible benefit.
- The plugin hook system is already well-tested and documented.
- Users who *want* to customize plugins can still do so by defining `plugins:` in their config.

**Consequences**:
- Plugin hook overhead remains (negligible for most sites).
- We can support any MkDocs-compatible plugin without extra work.
- Future Material features arrive automatically.

---

## 3. Unified config loader priority

**Context**: Three config file formats exist in the ecosystem: `mkdocs.yml` (legacy), `properdocs.yml` (ProperDocs native), and `docsforge.yml` (our unified format).

**Decision**: Look for configs in this priority:

1. `docsforge.yml` / `docsforge.yaml`
2. `properdocs.yml` / `properdocs.yaml`
3. `mkdocs.yml` / `mkdocs.yaml`

**Rationale**:
- Encourages adoption of the new `docsforge.yml` format.
- Does not break existing MkDocs sites — they continue to work untouched.
- ProperDocs users can migrate by simply renaming their file.

---

## 4. Auto-register strategy

**Context**: Material for MkDocs ships several plugins (`search`, `tags`, `blog`, `privacy`, `social`, `optimize`). Users typically have to list them in `plugins:`.

**Decision**: If the user does NOT define `plugins:`, inject the Material default set. If the user DOES define `plugins:`, merge defaults under their explicit choices.

**Implementation path**:
1. Load config via `UnifiedConfig`.
2. Before handing to ProperDocs build/serve, call `inject_material_plugins(config)`.
3. The function checks `config["plugins"]`. If `None`, populate with defaults. If present, append missing defaults.
4. ProperDocs' normal config validation then instantiates the plugins.

**Consequences**:
- Zero-config sites get search + tags + optional plugins automatically.
- Power users retain full control by writing their own `plugins:` list.
- We avoid monkey-patching ProperDocs internals — we just mutate the config dict before validation.

---

## 5. Git subtree vs. submodule for vendored sources

**Context**: We want to preserve the full git history of ProperDocs and Material for MkDocs inside the DocsForge repo for transparency and offline builds.

**Decision**: Use **git subtrees** (not submodules).

**Rationale**:
- Subtrees embed full history; `git clone` Just Works with no `--recursive` needed.
- Submodules break for casual contributors who forget `git submodule update`.
- We can still pull upstream updates via `git subtree pull`.

**Directory layout**:
```
docsforge/engine/   ← subtree of https://github.com/properdocs/properdocs
docsforge/themes/   ← subtree of https://github.com/squidfunk/mkdocs-material
```

**Commands to set up** (run once by maintainers):
```bash
git remote add properdocs https://github.com/properdocs/properdocs.git
git subtree add --prefix=docsforge/engine properdocs main --squash

git remote add material https://github.com/squidfunk/mkdocs-material.git
git subtree add --prefix=docsforge/themes material master --squash
```

**Note**: The subtrees are NOT required for normal `pip install docsforge`. They are for:
- Development and debugging inside the monorepo.
- Offline or air-gapped builds.
- Transparent audit of vendored code.

---

## 6. Dependency model

**Decision**: `docsforge` PyPI package declares runtime dependencies on `properdocs` and `mkdocs-material`.

```python
dependencies = [
    "properdocs>=1.6.7",
    "mkdocs-material>=9.7.0",
    "mkdocs-minify-plugin>=0.8.0",
    "mkdocs-redirects>=1.2.0",
    "pymdown-extensions>=10.0",
]
```

**Rationale**:
- `pip install docsforge` gives you everything.
- We pin minimum versions that are known to work together.
- We do NOT vendor the Python packages — subtrees are for source reference only.

---

## 7. CLI design

**Decision**: Mirror MkDocs/ProperDocs CLI structure with DocsForge branding.

| ProperDocs | DocsForge |
|------------|-----------|
| `properdocs new` | `docsforge new` |
| `properdocs serve` | `docsforge serve` |
| `properdocs build` | `docsforge build` |
| `properdocs gh-deploy` | `docsforge gh-deploy` |

**New features**:
- `docsforge new` scaffolds `docsforge.yml` with Material theme pre-selected.
- All commands auto-discover `docsforge.yml` → `properdocs.yml` → `mkdocs.yml`.
- All commands auto-register Material plugins before handing off to ProperDocs.

---

## 8. Theme default

**Decision**: If the user does not specify a theme, default to `material`.

**Rationale**:
- DocsForge is explicitly built around Material for MkDocs as the premier theme.
- Users can still override with `theme: name: readthedocs` or any other ProperDocs-compatible theme.
- The default is injected in `UnifiedConfig._merge_defaults()` only when no theme is present.

---

## Open Questions

1. **Should we bundle a local copy of Material's static assets?**  
   *Current thinking*: No. Let `pip` handle it. Subtrees are for source reference only.

2. **How do we handle Material Insiders features?**  
   *Current thinking*: Expose as `pip install docsforge[insiders]` when/if an open-source equivalent emerges.

3. **Search plugin conflict**  
   *Current thinking*: Material's enhanced search plugin replaces MkDocs core search. We only auto-register `search` once. ProperDocs' dual entrypoints handle the rest.

4. **Version pinning strategy**  
   *Current thinking*: Pin minimum versions, not exact. Allow patch-level upgrades. Test against latest ProperDocs + Material before each DocsForge release.

---

*This document will evolve as the project moves from skeleton to working prototype.*
