# Troubleshooting

Something not working? This page covers the most common issues and how to fix them. Each section lists symptoms, likely causes, and step-by-step solutions.

---

## Build errors

### Strict mode fails the build

**Symptom:** `docsforge build` exits with `ERROR: Strict mode is enabled` and points to a file.

**Cause:** Strict mode treats warnings as errors. Common triggers include missing internal links, invalid Markdown, or files that can't be parsed.

**Solution:**

1. Check the error message for the exact file and line.
2. Fix the underlying issue, or temporarily disable strict mode to see all warnings:

```yaml
# docsforge.yml
strict: false
```

3. Rebuild, note all warnings, fix them, then re-enable `strict: true`.

### Missing files or includes

**Symptom:** `File not found` or `Include file not found` during build.

**Cause:** The path in `!include` or `markdown_extensions` references a file that doesn't exist, or the path is relative to the wrong directory.

**Solution:**

- All paths in `docsforge.yml` are relative to the project root (where `docsforge.yml` lives).
- Check that the file exists at the exact path shown in the error.
- For `extra_css` and `extra_javascript`, paths are relative to the `docs/` directory:

```yaml
# docsforge.yml
extra_css:
  - stylesheets/extra.css   # resolves to docs/stylesheets/extra.css
```

### Config validation errors

**Symptom:** `Config value: 'foo'. Expected: str, received: int` or similar schema errors.

**Cause:** A value in `docsforge.yml` has the wrong type.

**Solution:**

- Check the [Reference](reference/index.md) for the expected type.
- Common mistakes:
  - `site_name` must be a string, not a list
  - `nav` items must be strings or nested lists, not integers
  - Plugin options must match their documented schema

---

## Search not working

### Search index not found

**Symptom:** Search box shows "No results found" for every query, or the console shows `404` for `search_index.json`.

**Cause:** The search plugin is disabled, or the index wasn't generated during build.

**Solution:**

1. Ensure the search plugin is enabled (it is by default):

```yaml
plugins:
  - search
```

2. Run `docsforge build` — the index is generated at build time, not on the fly.
3. If using a custom `site_url`, verify the base path is correct so the browser can fetch `search_index.json`.

### No results for common terms

**Symptom:** Search box works, but common words return nothing.

**Cause:** Lunr.js excludes common stop words (`the`, `and`, `is`) and requires exact stem matches.

**Solution:**

- Use more specific keywords (e.g., search `strict mode` instead of `why is strict mode not working`).
- If you need full-text search with synonyms, consider a third-party search integration.

### 404 on search page

**Symptom:** Directly visiting `/search.html` returns 404.

**Cause:** DocsForge search is a client-side overlay; there is no standalone `/search.html` page.

**Solution:** Use the search box in the header. It works on every page.

---

## Navigation issues

### Sidebar not showing

**Symptom:** The left sidebar is blank or missing entirely.

**Cause:** No `nav` section in `docsforge.yml`, or all pages are hidden.

**Solution:**

1. Explicitly define your navigation:

```yaml
nav:
  - Home: index.md
  - Guide: guide.md
```

2. Or rely on automatic discovery by leaving `nav` empty. If the sidebar is still blank, check that your `docs/` directory contains `.md` files.

### Sections not expanding

**Symptom:** Clicking a section header doesn't reveal its children.

**Cause:** The section page is missing or the section is configured as a link, not a container.

**Solution:**

- Ensure every section has an `index.md` (or matching file) to act as the parent:

```yaml
nav:
  - User Guide:
    - user-guide/index.md
    - user-guide/installation.md
    - user-guide/configuration.md
```

- Or use `navigation.expand` to auto-expand all sections:

```yaml
extra:
  features:
    - navigation.expand
```

### Active state wrong

**Symptom:** The wrong page is highlighted in the sidebar, or nothing is highlighted.

**Cause:** The `site_url` or `base_url` is misconfigured, causing path matching to fail.

**Solution:**

- Set `site_url` to the exact URL where the site is hosted:

```yaml
site_url: https://username.github.io/repository-name/
```

- For local `docsforge serve`, this is handled automatically.

---

## Asset 404s

### CSS or JS not loading

**Symptom:** Page renders unstyled, or interactive features (tabs, search, dark mode) don't work.

**Cause:** Browser console shows 404 errors for `.css` or `.js` files.

**Solution:**

1. Open DevTools → Network tab and check which files are 404.
2. If the paths are wrong, verify `site_url` matches your deployment URL.
3. For GitHub Pages project sites, ensure `site_url` includes the repository path:

```yaml
site_url: https://username.github.io/repository-name/
```

4. If using a CDN or reverse proxy, check that trailing slashes and path rewriting are correct.

### Images broken after deployment

**Symptom:** Images render locally but show as broken links on the deployed site.

**Cause:** Absolute paths (`/images/foo.png`) or incorrect relative paths.

**Solution:**

- Use relative paths from the Markdown file location:

```markdown
![Alt text](../images/foo.png)
```

- Or use page-relative syntax with `attr_list`:

```markdown
![Alt text](images/foo.png){ loading=lazy }
```

---

## Math not rendering

### KaTeX math blocks not showing

**Symptom:** `$$...$$` or `\\(...\\)` appears as raw text instead of rendered math.

**Cause:** The `pymdownx.arithmatex` extension is disabled, or KaTeX assets are blocked.

**Solution:**

1. Ensure the extension is enabled (default in new projects):

```yaml
markdown_extensions:
  - pymdownx.arithmatex:
      generic: true
```

2. Use the correct syntax:

```markdown
$$E = mc^2$$

Inline: \\(E = mc^2\\)
```

3. If deploying to a CSP-restricted environment, allow `unsafe-inline` for styles or switch to MathJax (configured via custom `extra_javascript`).

---

## Code highlighting not working

### No syntax colors

**Symptom:** Code blocks render as plain text without colors.

**Cause:** `pymdownx.highlight` is disabled, or the language specifier is missing/invalid.

**Solution:**

1. Ensure the extension is enabled:

```yaml
markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
```

2. Specify a valid language after the opening backticks:

```markdown
```python
def hello():
    print("hello")
```
```

3. Check the [Pygments lexers list](https://pygments.org/docs/lexers/) for the correct language name.

### Missing language support

**Symptom:** A specific language is not highlighted.

**Cause:** Pygments doesn't have a lexer for that language, or the language alias is wrong.

**Solution:**

- Try alternative names (e.g., `js` vs `javascript`, `bash` vs `shell`).
- For custom languages, use `text` as a fallback and open an issue to request a lexer.

---

## Dark mode not working

### Toggle missing or non-functional

**Symptom:** No moon/sun icon in the header, or clicking it does nothing.

**Cause:** The palette config is missing, or a custom CSS override is hiding the toggle.

**Solution:**

1. Ensure the palette is configured in `docsforge.yml`:

```yaml
extra:
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      toggle:
        icon: material/weather-night
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      toggle:
        icon: material/weather-sunny
        name: Switch to light mode
```

2. Check `extra_css` for rules that hide `.md-header__button` or override palette colors.

---

## Blog issues

### Posts not showing

**Symptom:** The blog index is empty or 404.

**Cause:** Blog plugin is disabled, or posts are not in the expected directory.

**Solution:**

1. Ensure the blog plugin is enabled:

```yaml
plugins:
  - blog
```

2. Place posts in `docs/blog/posts/` with a `YYYY-MM-DD-title.md` filename.

3. Include a `date` meta header in each post:

```markdown
---
date: 2024-01-15
---

# My Post Title
```

### RSS not generating

**Symptom:** No `feed_rss_created.xml` in the build output.

**Cause:** RSS generation is opt-in and requires additional config.

**Solution:**

```yaml
plugins:
  - blog:
      blog_dir: blog
      blog_toc: true
      post_date_format: full
      archive_date_format: yyyy
      archive_url_date_format: yyyy/MM
      post_url_date_format: yyyy/MM/dd
      post_url_format: "{date}/{slug}"
      archive_url_format: "{date}/archive.html"
      authors: true
      authors_file: "{blog}/.authors.yml"
      draft: true
      draft_on_serve: true
      draft_if_future_date: true
      pagination: true
      pagination_if_single_page: true
      pagination_keep_content: true
      categories: true
      categories_name: Categories
      categories_toc: true
      categories_url_format: "category/{slug}.html"
      pagination_url_format: "page/{page}.html"
      allowed_authors: all
      sort_by: date
      sort_order: descending
      show_total: true
      show_category: true
```

For RSS specifically, ensure `blog` plugin is enabled and `post_url_format` is set. RSS feeds are generated automatically in the `blog/` output directory.

---

## Performance issues

### Slow builds

**Symptom:** `docsforge build` takes minutes on a small site.

**Cause:** Large unoptimized images, many Mermaid/TikZ diagrams, or unnecessary file copying.

**Solution:**

1. Enable minification:

```yaml
plugins:
  - minify
```

2. Optimize images before adding them to `docs/` (use WebP or compressed PNG).
3. For TikZ diagrams, pre-compile them and commit the SVGs instead of building on every run.
4. Exclude large binary files from `docs/` using `.gitignore` patterns — they are copied to `site/` even if unused.

### Large site output

**Symptom:** `site/` directory is hundreds of megabytes.

**Cause:** Unoptimized images, video files, or large PDFs in `docs/`.

**Solution:**

- Use `exclude` in `docsforge.yml` to prevent copying unnecessary files:

```yaml
exclude:
  - "*.mp4"
  - "*.pdf"
  - drafts/
```

- Store large assets elsewhere (CDN, Git LFS) and link to them.

---

## Deployment issues

### GitHub Pages 404 on every page

**Symptom:** Only `index.html` works; all other pages return 404.

**Cause:** GitHub Pages project sites serve from a subdirectory (`/repo-name/`), but `site_url` is missing or incorrect.

**Solution:**

```yaml
# docsforge.yml
site_url: https://username.github.io/repository-name/
```

### CSS/JS broken on GitHub Pages

**Symptom:** Site loads but is unstyled.

**Cause:** Absolute asset paths assume root (`/`), but the site is in a subdirectory.

**Solution:** Always set `site_url` when deploying to a subdirectory. DocsForge rewrites asset paths based on this value.

### CNAME not working

**Symptom:** Custom domain shows 404 or GitHub Pages default domain.

**Cause:** `CNAME` file is missing, in the wrong place, or DNS isn't configured.

**Solution:**

1. Create `docs/CNAME` (no file extension, all caps):

```
docs.example.com
```

2. Configure DNS with a CNAME record pointing to `username.github.io` (for project sites) or `username.github.io` (for user/organization sites).
3. Wait for DNS propagation (up to 24 hours).

---

## Python and environment issues

### Version requirements

**Symptom:** `pip install docsforge` fails with dependency errors.

**Cause:** Python version is below 3.10, or pip is outdated.

**Solution:**

```bash
# Check Python version
python --version  # Must be 3.10 or higher

# Upgrade pip
pip install --upgrade pip

# Install in a fresh virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install docsforge
```

### Pip conflicts

**Symptom:** `docsforge build` fails with `ImportError` or `ModuleNotFoundError`.

**Cause:** Conflicting versions of `markdown`, `jinja2`, or other dependencies installed globally.

**Solution:**

1. Always use a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --force-reinstall docsforge
```

2. If using Conda, install via pip inside the Conda environment:

```bash
conda create -n docsforge python=3.11
conda activate docsforge
pip install docsforge
```

---

## FAQ

??? question "Why does `docsforge serve` show old content?"

    The dev server watches files and rebuilds automatically, but it may miss rapid changes. **Solution:** Save the file, wait 1–2 seconds, then refresh. If still stale, stop and restart `docsforge serve`.

??? question "Can I use DocsForge with Jupyter notebooks?"

    Yes. Use `mkdocs-jupyter` (a third-party plugin) or export notebooks to Markdown with `jupyter nbconvert --to markdown`. Include the `.md` files in your `docs/` directory and add them to `nav`.

??? question "How do I add a custom 404 page?"

    Create `docs/404.md`. DocsForge uses it automatically as the fallback page. You can customize the content and styling like any other page.

??? question "Why is my `!!! note` admonition not rendering?"

    The `admonition` extension must be enabled (it is by default). Ensure you use the correct syntax with four spaces for content:

    ```markdown
    !!! note
        This is the content.
    ```

    If the content is not indented, it will appear outside the admonition.

??? question "How do I exclude a page from search?"

    Add `search: false` to the page's metadata:

    ```markdown
    ---
    search: false
    ---

    # Secret Page
    ```

??? question "Can I deploy to a subdirectory without `site_url`?"

    Technically yes, but `site_url` is strongly recommended. Without it, absolute URLs, RSS feeds, search, and some plugins may break. Always set `site_url` for subdirectory deployments.

??? question "Why does the build fail with `jinja2.exceptions.TemplateNotFound`?"

    This usually means a custom theme directory is missing or misconfigured. Check `theme.custom_dir` in `docsforge.yml` and ensure the path points to an existing directory with valid Jinja2 templates.

??? question "How do I debug plugin issues?"

    Run the build with verbose logging:

    ```bash
    docsforge build --verbose
    ```

    This shows plugin load order, file processing, and any warnings. If a specific plugin fails, try disabling it temporarily to isolate the issue.

??? question "Does DocsForge support multi-language sites?"

    Native multi-language support is not built in. Common workarounds:

    - Maintain separate `docsforge.yml` files per language and build them independently.
    - Use a translation plugin like `mkdocs-static-i18n` (third-party).
    - Structure content with language subdirectories and switch via custom navigation.

??? question "How do I upgrade DocsForge?"

    ```bash
    pip install --upgrade docsforge
    ```

    Check the [Changelog](changelog/index.md) for breaking changes before upgrading major versions.

??? question "Where do I report bugs or request features?"

    Open an issue on the [GitHub repository](https://github.com/docsforge/docsforge). Include your `docsforge.yml`, Python version, and the full error output.

---

## Still stuck?

If none of the above solutions work:

1. Run `docsforge build --verbose` and capture the full output.
2. Check your `docsforge.yml` against the [Reference](reference/index.md).
3. Search existing [GitHub issues](https://github.com/docsforge/docsforge/issues) for the error message.
4. Open a new issue with:
   - `docsforge.yml`
   - Python version (`python --version`)
   - DocsForge version (`docsforge --version`)
   - The exact error message
   - Steps to reproduce
