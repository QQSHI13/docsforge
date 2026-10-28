/**
 * Link/anchor resolution for the DocsForge extension.
 *
 * Pure-ish helpers (no vscode imports) so they can be unit-tested.
 * Understands docsforge semantics: doc paths are relative to the docs_dir,
 * links are `[text](path#anchor)` resolved against the source file, and
 * validation.json (written by every build) provides per-file link/anchor
 * problems plus the anchor lists used for definition jumps.
 */
import * as fs from 'fs';
import * as path from 'path';

/** Canonical docs-relative path: forward slashes only, and collapse any
 *  doubled separator a user may have typed. Link targets and srcUris travel
 *  through many code paths; normalizing once at the boundary keeps the
 *  posix path math from silently missing Windows-style `guide\\foo.md`.
 *  A 1:1 character swap, so source offsets stay valid. */
export function normalizeDocPath(p: string): string {
  return p.replace(/\\/g, '/');
}

/** Absolute path of a doc uri inside the workspace docs dir. */
export function docAbsPath(workspaceRoot: string, docsDir: string, srcUri: string): string {
  return path.join(workspaceRoot, docsDir, ...normalizeDocPath(srcUri).split('/'));
}

/** Contained variant: null when a validation.json key would escape the docs
 *  dir (`../` traversal in a crafted or stale cache entry). */
export function docAbsPathSafe(
  workspaceRoot: string, docsDir: string, srcUri: string,
): string | null {
  const absPath = docAbsPath(workspaceRoot, docsDir, srcUri);
  const base = path.join(workspaceRoot, docsDir) + path.sep;
  return absPath === base.slice(0, -1) || absPath.startsWith(base) ? absPath : null;
}

/** Resolve a link target relative to a source file (posix semantics). */
export function resolveLinkTarget(
  docsDirAbs: string, srcUri: string, target: string,
): { absPath: string; srcUri: string } | null {
  const normalized = normalizeDocPath(target);
  const base = path.posix.join(path.posix.dirname(srcUri), normalized);
  const norm = path.posix.normalize(base);
  if (norm.startsWith('../')) {
    return null; // escapes docs dir
  }
  const absPath = path.join(docsDirAbs, ...norm.split('/'));
  return { absPath, srcUri: norm };
}

/** Extract link target + anchor from a markdown link destination. */
export function splitAnchor(dest: string): { target: string; anchor?: string } {
  const hash = dest.indexOf('#');
  if (hash === -1) {
    return { target: dest };
  }
  return { target: dest.slice(0, hash), anchor: dest.slice(hash + 1) };
}

/** Find all links in a markdown source: [text](dest) and ![alt](dest).
 *  Fenced code blocks and inline code spans are masked first (same length,
 *  so offsets stay valid): documented examples must not produce diagnostics,
 *  jumps, or link rewrites. */
export function extractLinks(source: string): Array<{ dest: string; offset: number; line: number }> {
  return extractLinksRaw(maskCode(source));
}

/** Raw link scan without code masking (internal; tests).
 *  `offset` is the absolute index of the `(` that opens the destination, so
 *  `offset + 1` is the destination itself — the convention every consumer
 *  already assumes (rename edits, quick fixes, `indexOf('(', offset)`).
 *  It used to record the match start (`[`), which left every edit computed as
 *  `offset + 1 … offset + 1 + dest.length` straddling the link label: renames
 *  rewrote the wrong characters. */
export function extractLinksRaw(source: string): Array<{ dest: string; offset: number; line: number }> {
  const links: Array<{ dest: string; offset: number; line: number }> = [];
  // The destination group accepts both forms the engine renders:
  //   [a](<my page.md>)  angle-bracketed - spaces need no quoting
  //   [a](my page.md)    bare, with spaces (python-markdown allows it even
  //                      though CommonMark forbids unescaped spaces here)
  //   [a](x.md "title")  bare + optional title
  // The old `([^)\s]+)` stopped at the first space, so every space-containing
  // link was invisible: rename left it pointing at a 404, and no hover,
  // definition or quick-fix fired on it. The whole parenthesised run is
  // captured and split below instead.
  const re = /!?\[[^\]]*\]\(\s*(<[^>\n]*>|[^)\n]*?)\s*\)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(source)) !== null) {
    const raw = m[1].trim();
    let dest: string;
    if (raw.startsWith('<') && raw.endsWith('>')) {
      dest = raw.slice(1, -1).trim();
    } else {
      // Drop a trailing title: `x.md "t"`, `x.md 't'`, `x.md (t)`.
      dest = raw.replace(/\s+(?:"[^"]*"|'[^']*'|\([^)]*\))\s*$/, '').trim();
    }
    if (!dest) {
      continue;
    }
    // Accept both separators: a target written `guide\foo.md` (the habit on
    // Windows) must resolve with posix math below, otherwise every definition,
    // hover, rename and quick fix silently misses it. The swap is 1:1, so the
    // recorded offsets stay valid.
    dest = normalizeDocPath(dest);
    const openParen = m[0].indexOf('(');
    const line = source.slice(0, m.index).split('\n').length - 1;
    links.push({ dest, offset: m.index + openParen, line });
  }
  return links;
}

/** Find all ATX headings with their line numbers. */
export function extractHeadings(source: string): Array<{ level: number; title: string; line: number }> {
  const headings: Array<{ level: number; title: string; line: number }> = [];
  const lines = source.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(/^(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (m) {
      headings.push({ level: m[1].length, title: m[2].trim(), line: i });
    }
  }
  return headings;
}

/** Extract the `docs_dir:` value from a config file's text, or null.
 *  Handles quoted (single/double) values including spaces — the naive
 *  `["']?([^"'\s#]+)` captured only `my` from `docs_dir: "my docs"` — plus
 *  unquoted values and trailing `#` comments. */
export function parseDocsDir(configText: string): string | null {
  const m = configText.match(
    /^[ \t]*docs_dir[ \t]*:[ \t]*(?:"([^"\n]*)"|'([^'\n]*)'|([^#\n]*))/m,
  );
  if (!m) {
    return null;
  }
  const raw = (m[1] ?? m[2] ?? m[3] ?? '').trim();
  if (!raw) {
    return null;
  }
  // A path, not a YAML scalar: reject anything that would escape the
  // workspace or that carries a nested mapping/flow value.
  const value = normalizeDocPath(raw).replace(/^\.\//, '').replace(/\/+$/, '');
  if (!value.startsWith('/') && value.split('/').includes('..')) {
    return null;
  }
  return value;
}

/** Replace a heading line's text, keeping its level and any trailing `#`s.
 *
 *  Uses a replacement FUNCTION, not a string: in a string replacement `$&`
 *  splices in the whole match, `$1` the captured hashes, and `` $` ``/`$'`
 *  the surrounding text — so renaming a heading to something like
 *  `A $& B` corrupted the heading instead of writing the title. A function
 *  receives the equivalent groups as arguments and treats the title
 *  literally. Public so the dollar-sign behaviour is unit-tested. */
export function renameHeadingLine(
  lineText: string, oldTitle: string, newTitle: string,
): string {
  const escaped = oldTitle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return lineText.replace(
    new RegExp(`^(#{1,6})\\s+${escaped}\\s*#*\\s*$`),
    (_match: string, hashes: string) => `${hashes} ${newTitle.trim()}`,
  );
}

/** Parse docsforge.yml for the docs_dir (default 'docs').
 *
 *  A config that simply omits `docs_dir` is normal (the default applies) and
 *  stays silent. A `docs_dir:` key that exists but cannot be parsed used to
 *  capture just the first word — `docs_dir: "my docs"` became `my`, so every
 *  later path missed and the whole extension went dead with no error. That
 *  case now falls back to 'docs' *and* logs which file it ignored. */
export function docsDirFromConfig(workspaceRoot: string): string {
  for (const name of ['docsforge.yml', 'docsforge.yaml']) {
    const p = path.join(workspaceRoot, name);
    if (!fs.existsSync(p)) {
      continue;
    }
    let text: string;
    try {
      text = fs.readFileSync(p, 'utf-8');
    } catch {
      continue;
    }
    const parsed = parseDocsDir(text);
    if (parsed) {
      return parsed;
    }
    if (/^[ \t]*docs_dir[ \t]*:/m.test(text)) {
      console.warn(
        `[docsforge] could not parse docs_dir in ${p}; falling back to "docs".`,
      );
    }
    return 'docs';
  }
  return 'docs';
}

/** Load validation.json (per-source link/anchor data from the last build). */
export function loadValidation(
  workspaceRoot: string,
): Record<string, { warnings?: number[][]; links?: Record<string, Record<string, string>>; anchors?: string[] }> {
  const p = path.join(workspaceRoot, '.docsforge', 'cache', 'validation.json');
  try {
    return JSON.parse(fs.readFileSync(p, 'utf-8'));
  } catch {
    return {};
  }
}

/** Severity for a validation warning level (python logging levels). */
export function severityForLevel(level: number): 0 | 1 | 2 | 3 {
  if (level >= 40) return 0; // ERROR
  if (level >= 30) return 1; // WARNING
  return 2; // INFO
}

/** Extract the offending link from a validation warning message. */
export function linkFromWarning(message: string): string | null {
  const m = message.match(/link\s+'([^']+)'/);
  return m ? m[1] : null;
}

/** Find ALL line numbers of a link destination within a source file.
 *  Returns empty array when absent. */
export function linesOfLink(source: string, dest: string): number[] {
  const escaped = dest.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(`\\(\\s*${escaped}[\\s)]`);
  const lines = source.split('\n');
  const hits: number[] = [];
  for (let i = 0; i < lines.length; i++) {
    if (re.test(lines[i])) {
      hits.push(i);
    }
  }
  return hits;
}

/** First matching line (kept for compatibility). */
export function lineOfLink(source: string, dest: string): number | null {
  const hits = linesOfLink(source, dest);
  return hits.length ? hits[0] : null;
}

/** Link under a cursor column within one line (offsets are line-relative
 *  when the source is a single line), or null. Used so go-to-definition
 *  and hover act on the link at the cursor, not the line's first link. */
export function linkAtPosition(
  line: string,
  links: Array<{ dest: string; offset: number; line: number }>,
  character: number,
): { dest: string; offset: number; line: number } | null {
  for (const link of links) {
    // `offset` is the opening paren; extend the hit range back over the
    // label so hovering/clicking `[text]` acts on the link too.
    const label = line.lastIndexOf('[', link.offset);
    const start = label === -1 ? link.offset : label;
    const close = line.indexOf(')', link.offset);
    const end = close === -1 ? line.length : close + 1;
    if (character >= start && character <= end) {
      return link;
    }
  }
  return null;
}

/** Rules describing how the engine turns a heading into an anchor id. */
export interface SlugRules {
  separator: string;
  unicode: boolean;
}

/** Rules matching markdown.extensions.toc.slugify in non-unicode mode (the
 *  engine default): NFKD + ASCII-fold, then strip non-word, collapse
 *  whitespace/underscore runs to the separator. Used when the engine-written
 *  slug-rules.json is not present yet. */
export const FALLBACK_SLUG_RULES: SlugRules = { separator: '-', unicode: false };

/** Absolute path of the engine-written slug rules file. */
export function slugRulesPath(workspaceRoot: string): string {
  return path.join(workspaceRoot, '.docsforge', 'cache', 'slug-rules.json');
}

/** Load the canonical slug rules the engine wrote at build time
 *  (`docsforge/slugger.py` → `.docsforge/cache/slug-rules.json`).
 *  Returns null when absent (pre-build workspace) so callers fall back to
 *  FALLBACK_SLUG_RULES. Kept in the same cache dir as validation.json, which
 *  the extension already knows how to reach. */
export function loadSlugRules(workspaceRoot: string): SlugRules | null {
  let raw: string;
  try {
    raw = fs.readFileSync(slugRulesPath(workspaceRoot), 'utf-8');
  } catch {
    return null;
  }
  try {
    const data = JSON.parse(raw);
    if (typeof data.separator === 'string' && typeof data.unicode === 'boolean') {
      // An empty/whitespace separator cannot be compiled into a regex
      // character class (an empty class is a SyntaxError), and a separator
      // made only of spaces is not a separator at all. Fall back rather than
      // throw: hover runs on a hot path and must never brick.
      if (!data.separator.trim()) {
        return null;
      }
      // A custom `toc.slugify` callable makes anchors unpredictable from
      // parameters — the engine flags that, and we use our own fallback.
      if (data.predictable === false) {
        return null;
      }
      return { separator: data.separator, unicode: data.unicode };
    }
  } catch {
    /* fall through to null */
  }
  return null;
}

/** Per-root memo for loadSlugRules, keyed on the file's mtime+size: a build
 *  that (re)writes slug-rules.json is picked up without a window reload,
 *  while hot paths (hover, completion, per-keystroke calls) pay only a stat.
 *  Returns null when the file is absent or unusable (callers fall back). */
const slugRulesCache = new Map<string, { mtimeMs: number; size: number; rules: SlugRules | null }>();

export function slugRulesFor(workspaceRoot: string): SlugRules | null {
  let mtimeMs = 0;
  let size = -1;
  try {
    const st = fs.statSync(slugRulesPath(workspaceRoot));
    mtimeMs = st.mtimeMs;
    size = st.size;
  } catch {
    // No file yet: nothing to cache, and a build will create it later.
    slugRulesCache.delete(workspaceRoot);
    return null;
  }
  const hit = slugRulesCache.get(workspaceRoot);
  if (hit && hit.mtimeMs === mtimeMs && hit.size === size) {
    return hit.rules;
  }
  const rules = loadSlugRules(workspaceRoot);
  slugRulesCache.set(workspaceRoot, { mtimeMs, size, rules });
  return rules;
}

/** Drop the memoized rules for a root (or all roots). */
export function invalidateSlugRules(workspaceRoot?: string): void {
  if (workspaceRoot === undefined) {
    slugRulesCache.clear();
    return;
  }
  slugRulesCache.delete(workspaceRoot);
}

/** `toc.unique()` duplicate suffix: `install_1` → `['install', 1]`. */
const UNIQUE_SUFFIX = /^(.*)_(\d+)$/;

/** Resolve a link anchor to the heading it points at, honoring `toc.unique()`
 *  numbering: `#install` is the first heading slugged `install`, `#install_1`
 *  the second, `#install_2` the third. Returns undefined when the anchor
 *  points at nothing (a genuinely broken anchor). */
export function findHeadingForAnchor<T extends { title: string }>(
  headings: T[], anchor: string, rules?: SlugRules,
): T | undefined {
  const wanted = slugifyHeading(anchor, rules);
  const slugs = headings.map((h) => slugifyHeading(h.title, rules));
  const exact = slugs.indexOf(wanted);
  if (exact !== -1) {
    return headings[exact];
  }
  const m = wanted.match(UNIQUE_SUFFIX);
  if (!m) {
    return undefined;
  }
  const base = m[1];
  const occurrence = Number(m[2]);
  if (occurrence < 1) {
    return undefined;
  }
  const matches = slugs.reduce<number[]>((acc, s, i) => (s === base ? [...acc, i] : acc), []);
  return occurrence < matches.length ? headings[matches[occurrence]] : undefined;
}

/** ASCII-fold the way Python's unicodedata.normalize('NFKD') +
 *  encode('ascii','ignore') does. JS supports NFKD natively via
 *  String.prototype.normalize, so decompose the whole string and drop any
 *  char still non-ASCII afterward (CJK, Cyrillic, ß, 你) — exactly the
 *  ascii/ignore fold. Chars NFKD maps to ASCII (é→e, ü→u, ideographic space
 *  U+3000→space) survive and are then treated as word chars / whitespace by
 *  the collapse below. */
function asciiFold(s: string): string {
  let out = '';
  for (const ch of s.normalize('NFKD')) {
    if (ch.charCodeAt(0) < 0x80) {
      out += ch;
    }
  }
  return out;
}

/** Escape a separator for use inside a regex character class. `-` is escaped
 *  too (the generic metacharacter escape omits it because it is only special
 *  inside a class) and is listed first so it never forms a range. */
function escapeForCharClass(sep: string): string {
  return sep.replace(/[-.*+?^${}()|[\]\\/]/g, '\\$&');
}

/** Slugify a heading title exactly as the engine does
 *  (`docsforge/slugger.py`, mirroring markdown.extensions.toc.slugify):
 *  optional NFKD+ASCII-fold, strip non-word, collapse whitespace/underscore
 *  runs to the separator. Edge separators are NOT trimmed — the engine keeps
 *  them, so `Foo-` slugs to `foo-` and `- Foo` to `-foo`.
 *  Prefers the engine-written slug-rules.json; falls back to the compiled-in
 *  default when not present. */
export function slugifyHeading(title: string, rules?: SlugRules): string {
  // A rules object with an unusable separator (empty/whitespace) would build
  // an invalid character class — treat it as "no rules" instead of throwing.
  const r = rules && rules.separator.trim() ? rules : FALLBACK_SLUG_RULES;
  const value = r.unicode ? title : asciiFold(title);
  const esc = escapeForCharClass(r.separator);
  // Python `re` `\w` is Unicode-aware in BOTH modes. In non-unicode mode the
  // ASCII fold above already dropped every non-ASCII char, so JS `\w` is an
  // exact stand-in. In unicode mode `\w` is ASCII-only in JS and would drop
  // CJK/Cyrillic — use the property classes Python's `\w` actually matches
  // (letters, numbers, underscore; combining marks are excluded, verified
  // against docsforge/slugger.py: slugify('e\u0301tude', unicode) == 'etude').
  // The literal `-` is kept in the strip class in both modes, exactly like the
  // engine's `[^\w\s-]` — and nothing else is exempt: the configured
  // separator is stripped like any other punctuation unless it is `-` or a
  // word char (verified: slugify('a.b c', separator='.') == 'ab.c' in BOTH
  // modes). The separator only takes part in the collapse below.
  const strip = r.unicode
    ? /[^\p{L}\p{N}_\s\-]/gu
    : /[^\w\s-]/g;
  return value
    .replace(strip, '')
    .trim()
    .toLowerCase()
    .replace(new RegExp(`[${esc}\\s]+`, 'g'), r.separator);
}

/** Walk all .md files under docs_dir, yielding {absPath, srcUri}. */
export function walkDocs(
  docsDirAbs: string,
): Array<{ absPath: string; srcUri: string }> {
  const out: Array<{ absPath: string; srcUri: string }> = [];
  const walk = (dir: string, prefix: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(p, `${prefix}${entry.name}/`);
      } else if (entry.name.endsWith('.md')) {
        out.push({ absPath: p, srcUri: `${prefix}${entry.name}` });
      }
    }
  };
  walk(docsDirAbs, '');
  return out;
}

/**
 * Rename a DOCUMENT (base + all locale variants): oldSrcUri may be the base
 * (foo.md) or any variant (foo.zh.md). Computes the set of files to rename
 * and the edits for every link that resolves to any of them.
 *
 * Returns { files: Map<absPath, newAbsPath>, edits: Map<absPath, edits> }.
 */
export function computeDocumentRename(
  workspaceRoot: string, oldSrcUri: string, newBaseName: string,
): {
  files: Map<string, string>;
  edits: Map<string, Array<{ start: number; end: number; text: string }>>;
} {
  const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));
  const files = new Map<string, string>();
  const edits = new Map<string, Array<{ start: number; end: number; text: string }>>();
  if (!fs.existsSync(docsDirAbs)) {
    return { files, edits };
  }

  // Old variant names: base + each locale suffix found on disk.
  const oldBase = stripLocaleSuffix(oldSrcUri);
  const oldVariants = [`${oldBase}.md`];
  for (const doc of walkDocs(docsDirAbs)) {
    const variant = localeVariantOf(doc.srcUri, oldBase);
    if (variant !== null && !oldVariants.includes(variant)) {
      oldVariants.push(variant);
    }
  }

  // Old -> new name map.
  const newBase = stripLocaleSuffix(newBaseName);
  const renameMap = new Map<string, string>();
  for (const variant of oldVariants) {
    const locale = variant === oldBase ? null : variant.slice(oldBase.length + 1, -3);
    const newName = locale ? `${newBase}.${locale}.md` : `${newBase}.md`;
    renameMap.set(variant, newName);
    const oldAbs = path.join(docsDirAbs, ...variant.split('/'));
    const newAbs = path.join(docsDirAbs, ...newName.split('/'));
    if (fs.existsSync(oldAbs)) {
      files.set(oldAbs, newAbs);
    }
  }

  // Rewrite links that resolve to any old variant.
  for (const doc of walkDocs(docsDirAbs)) {
    const source = fs.readFileSync(doc.absPath, 'utf-8');
    const fileEdits: Array<{ start: number; end: number; text: string }> = [];
    for (const link of extractLinks(source)) {
      const { target, anchor } = splitAnchor(link.dest);
      if (!target) {
        continue;
      }
      const resolved = resolveLinkTarget(docsDirAbs, doc.srcUri, target);
      if (!resolved || !renameMap.has(resolved.srcUri)) {
        continue;
      }
      // New relative target from the same source file.
      let newTarget = path.posix.relative(
        path.posix.dirname(doc.srcUri), renameMap.get(resolved.srcUri)!,
      );
      if (!newTarget.startsWith('.')) {
        newTarget = `./${newTarget}`;
      }
      if (anchor) {
        newTarget += `#${anchor}`;
      }
      fileEdits.push({
        start: link.offset + 1, // skip '('
        end: link.offset + 1 + link.dest.length,
        text: newTarget,
      });
    }
    if (fileEdits.length) {
      edits.set(doc.absPath, fileEdits);
    }
  }

  return { files, edits };
}

/** Strip the locale suffix from a doc name: foo.zh.md -> foo, foo.md -> foo.
 *  Case-insensitive: BCP 47 tags may be uppercase (`pt-BR`). */
export function stripLocaleSuffix(srcUri: string): string {
  return srcUri.replace(/(\.[a-z]{2}(?:-[a-z]{2})?)?\.md$/i, '');
}

/** Given a base doc name, return the variant name if srcUri is one.
 *  e.g. localeVariantOf('foo.zh.md', 'foo') -> 'foo.zh.md'; null otherwise. */
export function localeVariantOf(srcUri: string, base: string): string | null {
  const prefix = `${base}.`;
  if (srcUri.startsWith(prefix) && srcUri.endsWith('.md')) {
    const locale = srcUri.slice(prefix.length, -3);
    if (/^[a-z]{2}(-[a-z]{2})?$/i.test(locale)) {
      return srcUri;
    }
  }
  return null;
}

/**
 * Compute the edits needed to rename oldSrcUri → newSrcUri: rewrite every
 * link across all docs that resolves to oldSrcUri. Returns a map of
 * absolute file path → (start offset, end offset, new text) edits.
 */
export function computeRenameEdits(
  workspaceRoot: string, oldSrcUri: string, newSrcUri: string,
): Map<string, Array<{ start: number; end: number; text: string }>> {
  const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));
  const edits = new Map<string, Array<{ start: number; end: number; text: string }>>();
  if (!fs.existsSync(docsDirAbs)) {
    return edits;
  }
  for (const doc of walkDocs(docsDirAbs)) {
    const source = fs.readFileSync(doc.absPath, 'utf-8');
    const fileEdits: Array<{ start: number; end: number; text: string }> = [];
    for (const link of extractLinks(source)) {
      const { target, anchor } = splitAnchor(link.dest);
      if (!target) {
        continue;
      }
      const resolved = resolveLinkTarget(docsDirAbs, doc.srcUri, target);
      if (!resolved || resolved.srcUri !== oldSrcUri) {
        continue;
      }
      // New relative target from the same source file.
      let newTarget = path.posix.relative(
        path.posix.dirname(doc.srcUri), newSrcUri,
      );
      if (!newTarget.startsWith('.')) {
        newTarget = `./${newTarget}`;
      }
      if (anchor) {
        newTarget += `#${anchor}`;
      }
      fileEdits.push({
        start: link.offset + 1, // skip '('
        end: link.offset + 1 + link.dest.length,
        text: newTarget,
      });
    }
    if (fileEdits.length) {
      edits.set(doc.absPath, fileEdits);
    }
  }
  return edits;
}

/** Result of an anchor rename computation.
 *  `edits` maps absPath → the anchor rewrites. `ambiguous` lists the headings
 *  whose slug collides with another heading in the same document — in that
 *  case the niche links cannot be attributed to one heading, so they are left
 *  untouched and the caller can surface a warning. */
export interface AnchorRenameResult {
  edits: Map<string, Array<{ start: number; end: number; text: string }>>;
  /** Headings (1-based line + title) sharing the old slug, when > 1. */
  ambiguous: Array<{ line: number; title: string }>;
}

/**
 * Compute edits for renaming a heading anchor: rewrite every link across the
 * docs tree whose anchor slug matches oldSlug into newSlug, when the link
 * resolves to docSrcUri. Anchor-only links (`[#slug]`, same page) resolve
 * to their own file and are rewritten too.
 *
 * Duplicate slugs: two headings can slugify to the same value (`## Install`
 * and `## Install!` both give `install`). Links to `#install` are then
 * ambiguous — the target is whichever heading comes first, and a same-page
 * link additionally depends on where it sits in the file. Renaming one of
 * them and rewriting every `#install` link would silently repoint links that
 * belonged to the other heading, so a colliding slug produces no edits at
 * all; `ambiguous` carries the competing headings for the caller to report.
 *
 * `renamedHeadingLine` (0-based) disambiguates when the caller knows which
 * occurrence is being renamed: only same-page links on lines after that
 * heading and before the next heading with the same slug are rewritten, and
 * cross-page links stay untouched because the anchor cannot target a specific
 * occurrence from another file.
 */
export function computeAnchorRenameEdits(
  workspaceRoot: string,
  docSrcUri: string,
  oldSlug: string,
  newSlug: string,
  renamedHeadingLine?: number,
  rules?: SlugRules,
): AnchorRenameResult {
  const effectiveRules = rules ?? slugRulesFor(workspaceRoot) ?? FALLBACK_SLUG_RULES;
  const edits = new Map<string, Array<{ start: number; end: number; text: string }>>();
  const ambiguous: Array<{ line: number; title: string }> = [];
  // An empty slug is not a valid anchor: `#` alone targets the page top, so
  // "renaming" to it is always a mistake.
  if (!oldSlug.trim() || !newSlug.trim() || oldSlug === newSlug) {
    return { edits, ambiguous };
  }
  const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));
  if (!fs.existsSync(docsDirAbs)) {
    return { edits, ambiguous };
  }

  // Same-slug headings in the renamed document, in source order.
  const docAbsPath = path.join(docsDirAbs, ...normalizeDocPath(docSrcUri).split('/'));
  let occurrences: Array<{ line: number; title: string }> = [];
  let docOccurrenceLines: number[] = [];
  try {
    const headings = extractHeadings(fs.readFileSync(docAbsPath, 'utf-8'));
    occurrences = headings
      .filter((h) => slugifyHeading(h.title, effectiveRules) === oldSlug)
      .map((h) => ({ line: h.line, title: h.title }));
    docOccurrenceLines = occurrences.map((o) => o.line);
  } catch {
    occurrences = [];
  }

  // With a collision and no way to tell which occurrence the user means, skip
  // rather than rewrite links that may point at the other heading.
  const collides = occurrences.length > 1;
  if (collides) {
    ambiguous.push(...occurrences);
    if (renamedHeadingLine === undefined) {
      return { edits, ambiguous };
    }
  }

  // Same-page links to a specific occurrence: from that heading's line up to
  // the next heading sharing the slug.
  const windowsForOccurrence = (line: number): Array<[number, number]> | null => {
    if (!collides) {
      return null; // no collision: position does not matter
    }
    if (!docOccurrenceLines.includes(line)) {
      return null;
    }
    const next = docOccurrenceLines.find((l) => l > line);
    return [[line, next ?? Number.POSITIVE_INFINITY]];
  };

  for (const doc of walkDocs(docsDirAbs)) {
    const source = fs.readFileSync(doc.absPath, 'utf-8');
    const fileEdits: Array<{ start: number; end: number; text: string }> = [];
    for (const link of extractLinks(source)) {
      const { target, anchor } = splitAnchor(link.dest);
      if (!anchor || anchor !== oldSlug) {
        continue;
      }
      const isSamePage = !target;
      // Empty target = same-page link: only the file being renamed matches.
      const resolvedSrc = isSamePage
        ? doc.srcUri
        : resolveLinkTarget(docsDirAbs, doc.srcUri, target)?.srcUri ?? null;
      if (resolvedSrc !== docSrcUri) {
        continue;
      }
      if (isSamePage && collides) {
        // A same-page link can only be attributed to an occurrence when the
        // user told us which heading is being renamed.
        if (renamedHeadingLine === undefined) {
          continue;
        }
        const windows = windowsForOccurrence(renamedHeadingLine);
        if (!windows || !windows.some(([from, to]) => link.line >= from && link.line < to)) {
          continue;
        }
      }
      if (!isSamePage && collides) {
        // Cross-page links cannot select an occurrence: ambiguous, leave it.
        continue;
      }
      fileEdits.push({
        start: link.offset + 1 + link.dest.indexOf('#') + 1,
        end: link.offset + 1 + link.dest.length,
        text: newSlug,
      });
    }
    if (fileEdits.length) {
      edits.set(doc.absPath, fileEdits);
    }
  }
  return { edits, ambiguous };
}

/* ------------------------------------------------------------------ */
/* Footnote / formatting diagnostics (Zensical-style breadth)         */
/* ------------------------------------------------------------------ */

/** Blank out fenced code blocks and inline code spans, preserving length
 *  (and newlines) so downstream offsets stay valid. */
export function maskCode(source: string): string {
  const lines = source.split('\n');
  let fence: string | null = null;
  const masked = lines.map((line) => {
    const marker = fenceMarker(line);
    if (marker) {
      if (fence === null) {
        fence = marker;
      } else if (marker[0] === fence[0] && marker.length >= fence.length) {
        fence = null;
      }
      return line;
    }
    if (fence !== null) {
      return ' '.repeat(line.length);
    }
    return line.replace(/(`+)[^`\n]*?\1(?!`)/g, (m) => ' '.repeat(m.length));
  });
  return masked.join('\n');
}

/** Footnote references `[^label]` and definitions `[^label]: …`. */
export function checkFootnotes(
  source: string,
): Array<{ line: number; message: string; kind: 'unresolved' | 'duplicate' }> {
  const warnings: Array<{ line: number; message: string; kind: 'unresolved' | 'duplicate' }> = [];
  const refs = new Map<string, number>();   // label -> first line
  const defs = new Map<string, number>();   // label -> first line
  const lines = maskCode(source).split('\n');
  const refRe = /\[\^([^\]]+)\](?!:)/g;
  const defRe = /^\[\^([^\]]+)\]:\s*/;
  for (let i = 0; i < lines.length; i++) {
    let m: RegExpExecArray | null;
    while ((m = refRe.exec(lines[i])) !== null) {
      if (!refs.has(m[1])) {
        refs.set(m[1], i);
      }
    }
    const d = defRe.exec(lines[i]);
    if (d) {
      if (!defs.has(d[1])) {
        defs.set(d[1], i);
      } else {
        warnings.push({ line: i, message: `Duplicate footnote definition: [^${d[1]}]`, kind: 'duplicate' });
      }
    }
  }
  for (const [label, line] of refs) {
    if (!defs.has(label)) {
      warnings.push({ line, message: `Unresolved footnote: [^${label}]`, kind: 'unresolved' });
    }
  }
  return warnings;
}

/** Minimal markdown formatting: normalize trailing whitespace + blank lines.
 *  Fenced code blocks (``` / ~~~) pass through untouched: blank lines and
 *  trailing spaces can be significant inside them. */
export function formatMarkdown(source: string): string {
  const lines = source.split('\n');
  const out: string[] = [];
  let blank = 0;
  let fence: string | null = null;
  for (const line of lines) {
    const marker = fenceMarker(line);
    if (marker) {
      if (fence === null) {
        fence = marker;
      } else if (marker[0] === fence[0] && marker.length >= fence.length) {
        fence = null;
      }
      blank = 0;
      out.push(line);
      continue;
    }
    if (fence !== null) {
      out.push(line);
      continue;
    }
    const trimmed = line.replace(/[ \t]+$/, '');
    if (trimmed === '') {
      blank++;
      if (blank > 1) {
        continue; // collapse runs of blank lines
      }
    } else {
      blank = 0;
    }
    out.push(trimmed);
  }
  // Ensure the file ends with exactly one trailing newline.
  while (out.length && out[out.length - 1] === '') {
    out.pop();
  }
  return out.join('\n') + '\n';
}

/** Rename a folder (and everything under it) plus all links into it. */
export function computeFolderRename(
  workspaceRoot: string, oldDirSrc: string, newDirSrc: string,
): {
  files: Map<string, string>;
  edits: Map<string, Array<{ start: number; end: number; text: string }>>;
} {
  const docsDirAbs = path.join(workspaceRoot, docsDirFromConfig(workspaceRoot));
  const files = new Map<string, string>();
  const edits = new Map<string, Array<{ start: number; end: number; text: string }>>();
  if (!fs.existsSync(docsDirAbs)) {
    return { files, edits };
  }
  const oldPrefix = `${oldDirSrc}/`;
  const renameMap = new Map<string, string>();
  for (const doc of walkDocs(docsDirAbs)) {
    if (doc.srcUri === oldDirSrc || doc.srcUri.startsWith(oldPrefix)) {
      const newName = newDirSrc + doc.srcUri.slice(oldDirSrc.length);
      renameMap.set(doc.srcUri, newName);
      files.set(doc.absPath, path.join(docsDirAbs, ...newName.split('/')));
    }
  }
  for (const doc of walkDocs(docsDirAbs)) {
    const source = fs.readFileSync(doc.absPath, 'utf-8');
    const fileEdits: Array<{ start: number; end: number; text: string }> = [];
    for (const link of extractLinks(source)) {
      const { target, anchor } = splitAnchor(link.dest);
      if (!target) {
        continue;
      }
      const resolved = resolveLinkTarget(docsDirAbs, doc.srcUri, target);
      if (!resolved || !renameMap.has(resolved.srcUri)) {
        continue;
      }
      let newTarget = path.posix.relative(
        path.posix.dirname(doc.srcUri), renameMap.get(resolved.srcUri)!,
      );
      if (!newTarget.startsWith('.')) {
        newTarget = `./${newTarget}`;
      }
      if (anchor) {
        newTarget += `#${anchor}`;
      }
      fileEdits.push({
        start: link.offset + 1,
        end: link.offset + 1 + link.dest.length,
        text: newTarget,
      });
    }
    if (fileEdits.length) {
      edits.set(doc.absPath, fileEdits);
    }
  }
  return { files, edits };
}

/* ------------------------------------------------------------------ */
/* Extension-side pure helpers (vscode-free, unit-tested)             */
/* ------------------------------------------------------------------ */

/** Docs-relative URI for a file, or null when outside the docs dir.
 *  Guards non-docs .md files (e.g. root README.md) that match the broad
 *  `root/**​/*.md` selector but would otherwise produce garbage via
 *  `fsPath.slice(docsDir.length + 1)`. */
export function srcUriOfPath(docsDirAbs: string, fsPath: string): string | null {
  if (fsPath !== docsDirAbs && !fsPath.startsWith(docsDirAbs + path.sep)) {
    return null;
  }
  if (fsPath === docsDirAbs) {
    return null;
  }
  return fsPath.slice(docsDirAbs.length + 1).split(path.sep).join('/');
}

/** Whether the cursor is inside a markdown link destination `](…)`.
 *  Returns the partial target, or null when not in link context (so plain
 *  `(…)` parens don't trigger path completions on every keystroke). */
export function linkTargetPrefix(beforeCursor: string): string | null {
  const m = beforeCursor.match(/\]\(([^)]*)$/);
  return m ? m[1] : null;
}

/** Map a docs-relative target back to what the user should see in `](…)`:
 *  relative to the source file's directory, keeping the user's `./` style
 *  (typed `gui` → `guide/x.md`, typed `./gui` → `./guide/x.md`). */
export function toRelativeDisplay(
  targetSrcUri: string, fromDir: string, keepDotSlash: boolean,
): string {
  let rel = path.posix.relative(fromDir, targetSrcUri);
  if (!rel.startsWith('.')) {
    rel = `./${rel}`;
  }
  return keepDotSlash ? rel : rel.replace(/^\.\//, '');
}

/** Filter cached docs URIs by a typed prefix (with directory-prune). */
export function filterDocsByPrefix(
  files: Array<{ srcUri: string }>, partial: string, limit: number,
): string[] {
  const out: string[] = [];
  let prefixDir: string | null = null;
  const slash = partial.lastIndexOf('/');
  if (slash > 0) {
    prefixDir = partial.slice(0, slash + 1);
  }
  for (const f of files) {
    if (prefixDir && !f.srcUri.startsWith(prefixDir)) {
      continue;
    }
    if (!f.srcUri.startsWith(partial)) {
      continue;
    }
    out.push(f.srcUri);
    if (out.length >= limit) {
      break;
    }
  }
  return out;
}

/** Whether an onDidRenameFiles entry is a folder rename.
 *  Post-move `oldFsPath` no longer exists, so stat `newFsPath`; fall back to
 *  an extension heuristic (folders lack a `.md` suffix on both ends). */
export function isFolderRenameEvent(oldFsPath: string, newFsPath: string): boolean {
  try {
    if (fs.existsSync(newFsPath)) {
      return fs.statSync(newFsPath).isDirectory();
    }
  } catch {
    /* fall through to heuristic */
  }
  const oldIsMd = oldFsPath.endsWith('.md');
  const newIsMd = newFsPath.endsWith('.md');
  return !oldIsMd && !newIsMd;
}

/** Pre-validate rename targets: return the first colliding target, if any
 *  (existing file on disk or duplicate target within the map). */
export function findRenameCollision(files: Map<string, string>): string | null {
  const seen = new Set<string>();
  for (const [, newAbs] of files) {
    if (seen.has(newAbs)) {
      return newAbs;
    }
    seen.add(newAbs);
    if (fs.existsSync(newAbs)) {
      return newAbs;
    }
  }
  return null;
}

/** Collect footnote warnings for every .md file under the docs dir,
 *  independent of validation.json coverage. */
export function collectFootnoteWarnings(
  docsDirAbs: string,
): Map<string, Array<{ line: number; message: string }>> {
  const out = new Map<string, Array<{ line: number; message: string }>>();
  let docs: Array<{ absPath: string; srcUri: string }>;
  try {
    docs = walkDocs(docsDirAbs);
  } catch {
    return out;
  }
  for (const doc of docs) {
    let text: string;
    try {
      text = fs.readFileSync(doc.absPath, 'utf-8');
    } catch {
      continue;
    }
    const warnings = checkFootnotes(text);
    if (warnings.length) {
      out.set(
        doc.absPath,
        warnings.map((w) => ({ line: w.line, message: w.message })),
      );
    }
  }
  return out;
}

/** Parse validation.json without swallowing the failure mode.
 *  `{ ok: true, data }` on success (including file-missing → empty),
 *  `{ ok: false }` when the file exists but cannot be parsed (e.g. mid
 *  atomic-write) so callers keep stale diagnostics instead of flashing. */
export function tryLoadValidation(
  workspaceRoot: string,
): { ok: true; data: Record<string, { warnings?: number[][] }> } | { ok: false } {
  const p = path.join(workspaceRoot, '.docsforge', 'cache', 'validation.json');
  let raw: string;
  try {
    raw = fs.readFileSync(p, 'utf-8');
  } catch (err) {
    const code = (err as NodeJS.ErrnoException)?.code;
    if (code === 'ENOENT') {
      return { ok: true, data: {} };
    }
    return { ok: false };
  }
  try {
    return { ok: true, data: JSON.parse(raw) as Record<string, { warnings?: number[][] }> };
  } catch {
    return { ok: false };
  }
}

/* ------------------------------------------------------------------ */
/* Scaffolding, twins, snippet/anchor and frontmatter helpers          */
/* ------------------------------------------------------------------ */

/** Locale suffixes observed in a docs tree, e.g. `['zh']`. */
export function detectLocales(files: Array<{ srcUri: string }>): string[] {
  const locales = new Set<string>();
  for (const f of files) {
    const m = f.srcUri.match(/\.([a-z]{2}(?:-[a-z]{2})?)\.md$/i);
    if (m) {
      locales.add(m[1]);
    }
  }
  return [...locales].sort();
}

export interface MissingTwin {
  /** `guide/foo` (no suffix, no extension). */
  base: string;
  kind: 'missing' | 'orphan';
  /** e.g. `zh` for `guide/foo.zh.md`. */
  locale: string;
  /** Expected variant srcUri. */
  expected: string;
  /** Base file absPath when it exists (for copying the H1 into a stub). */
  baseAbsPath: string | null;
}

/** Every base page should have one variant per locale; flag gaps and
 *  orphan translations (variant without a base file). */
export function findMissingTwins(
  files: Array<{ absPath: string; srcUri: string }>, locales: string[],
): MissingTwin[] {
  const bySrc = new Map(files.map((f) => [f.srcUri, f.absPath]));
  const bases = new Set<string>();
  for (const f of files) {
    bases.add(stripLocaleSuffix(f.srcUri));
  }
  const out: MissingTwin[] = [];
  const reported = new Set<string>();
  for (const base of [...bases].sort()) {
    const baseSrc = `${base}.md`;
    const baseAbs = bySrc.get(baseSrc) ?? null;
    if (!baseAbs) {
      // No base file: every present variant is an orphan translation.
      for (const [src] of bySrc) {
        if (!src.startsWith(`${base}.`) || !src.endsWith('.md')) {
          continue;
        }
        const m = src.match(/\.([a-z]{2}(?:-[a-z]{2})?)\.md$/i);
        if (!m || reported.has(src)) {
          continue;
        }
        reported.add(src);
        out.push({ base, kind: 'orphan', locale: m[1], expected: src, baseAbsPath: null });
      }
      continue;
    }
    for (const locale of locales) {
      const expected = `${base}.${locale}.md`;
      if (!bySrc.has(expected)) {
        out.push({ base, kind: 'missing', locale, expected, baseAbsPath: baseAbs });
      }
    }
  }
  return out;
}

/** Sanitize a user-typed page path (`guide/my-page` or `my-page.md`) into a
 *  docs-relative srcUri, or null when invalid. */
export function sanitizePageName(input: string): string | null {
  const cleaned = input.trim().replace(/\\/g, '/').replace(/^\/+/, '');
  if (!cleaned || cleaned.includes('\0')) {
    return null;
  }
  const parts = cleaned.split('/');
  if (parts.some((p) => p === '' || p === '.' || p === '..')) {
    return null;
  }
  if (parts.some((p) => /[<>:"|?*]/.test(p))) {
    return null;
  }
  const withExt = cleaned.endsWith('.md') ? cleaned : `${cleaned}.md`;
  return withExt;
}

/** `guide/my-page` → `My page` (default H1 for a new file). */
export function humanizePageName(srcUri: string): string {
  const base = srcUri.split('/').pop()!.replace(/\.md$/, '');
  const words = base.replace(/[-_]+/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Titles of top-level nav items that have a `children:` block. */
export function parseNavParents(configText: string): string[] {
  const parents: string[] = [];
  const lines = configText.split('\n');
  let current: string | null = null;
  let hasChildren = false;
  const push = () => {
    if (current !== null && hasChildren) {
      parents.push(current);
    }
  };
  for (const line of lines) {
    const item = line.match(/^  - title:\s*(.+?)\s*$/);
    if (item) {
      push();
      current = item[1];
      hasChildren = false;
      continue;
    }
    if (current !== null && /^    children:\s*$/.test(line)) {
      hasChildren = true;
    }
    if (/^[A-Za-z_][\w-]*:/.test(line)) {
      push();
      current = null;
      hasChildren = false;
    }
  }
  push();
  return parents;
}

/** Quote a nav title when it contains YAML-significant characters. */
function yamlTitle(title: string): string {
  return /[:#{}[\],&*!|>'"%@`]/.test(title)
    ? JSON.stringify(title)
    : title;
}

/** Insert `- title / path` into the `nav:` block (top level, or under a
 *  parent's `children:`). Returns the new text, or null when there is no
 *  `nav:` key / the parent is unknown (caller falls back to manual edit). */
export function appendNavEntry(
  configText: string, title: string, srcUri: string, parentTitle?: string | null,
): string | null {
  const lines = configText.split('\n');
  const navIdx = lines.findIndex((l) => /^nav:\s*$/.test(l));
  if (navIdx === -1) {
    return null;
  }
  const endIdx = (() => {
    for (let i = navIdx + 1; i < lines.length; i++) {
      if (/^[A-Za-z_][\w-]*:/.test(lines[i])) {
        return i;
      }
    }
    return lines.length;
  })();
  const entry = (indent: string) => [
    `${indent}- title: ${yamlTitle(title)}`,
    `${indent}  path: ${srcUri}`,
  ];
  if (!parentTitle) {
    const next = [...lines.slice(0, endIdx), ...entry('  '), ...lines.slice(endIdx)];
    return next.join('\n');
  }
  for (let i = navIdx + 1; i < endIdx; i++) {
    const item = lines[i].match(/^  - title:\s*(.+?)\s*$/);
    if (!item || item[1] !== parentTitle) {
      continue;
    }
    let childIdx = -1;
    for (let j = i + 1; j < endIdx; j++) {
      if (/^  - title:/.test(lines[j])) {
        break;
      }
      if (/^    children:\s*$/.test(lines[j])) {
        childIdx = j;
        break;
      }
    }
    if (childIdx === -1) {
      return null;
    }
    let insertAt = endIdx;
    for (let j = childIdx + 1; j < endIdx; j++) {
      if (/^  - title:/.test(lines[j])) {
        insertAt = j;
        break;
      }
    }
    const next = [...lines.slice(0, insertAt), ...entry('      '), ...lines.slice(insertAt)];
    return next.join('\n');
  }
  return null;
}

/** Partial path inside a `--8<-- "…"` / `-8<-- '…'` snippet marker, or null. */
export function snippetPathPrefix(lineBeforeCursor: string): string | null {
  const m = lineBeforeCursor.match(/--?8<--\s*["']([^"']*)$/);
  return m ? m[1] : null;
}

/** Anchor context inside a link destination `](target#partial)`: the target
 *  plus the typed anchor prefix, or null when there is no `#`. An empty
 *  target means the current file (`](#…)`). */
export function anchorPrefix(
  beforeCursor: string,
): { target: string; partial: string } | null {
  const link = beforeCursor.match(/\]\(([^)]*)$/);
  if (!link) {
    return null;
  }
  const hash = link[1].indexOf('#');
  if (hash === -1) {
    return null;
  }
  return { target: link[1].slice(0, hash), partial: link[1].slice(hash + 1) };
}

/** Line range of the YAML frontmatter block, or null when absent. */
export function frontmatterRange(
  text: string,
): { startLine: number; endLine: number } | null {
  const lines = text.split('\n');
  if (lines.length < 2 || lines[0].trim() !== '---') {
    return null;
  }
  for (let i = 1; i < lines.length; i++) {
    if (lines[i].trim() === '---') {
      return { startLine: 0, endLine: i };
    }
  }
  return null;
}

/** Fence marker of a line (``` / ~~~ run), e.g. "```" or "~~~~".
 *  Shared by formatting (pass-through) and completion suppression. */
export function fenceMarker(line: string): string | null {
  const m = line.match(/^\s*(`{3,}|~{3,})/);
  return m ? m[1] : null;
}

/** Whether a 0-based line sits inside a fenced code block. */
export function inFencedCode(lines: string[], lineNo: number): boolean {
  let fence: string | null = null;
  for (let i = 0; i < lineNo && i < lines.length; i++) {
    const marker = fenceMarker(lines[i]);
    if (!marker) {
      continue;
    }
    if (fence === null) {
      fence = marker;
    } else if (marker[0] === fence[0] && marker.length >= fence.length) {
      fence = null;
    }
  }
  return fence !== null;
}

/** Anchor completion candidates: case-insensitive slug-prefix match,
 *  deduplicated (duplicate headings collapse to one item with a count). */
export function matchAnchors(
  headings: Array<{ title: string; slug: string }>, partial: string,
): Array<{ slug: string; title: string; count: number }> {
  const needle = partial.toLowerCase();
  const seen = new Map<string, { slug: string; title: string; count: number }>();
  for (const h of headings) {
    if (!h.slug.toLowerCase().startsWith(needle)) {
      continue;
    }
    const hit = seen.get(h.slug);
    if (hit) {
      hit.count++;
    } else {
      seen.set(h.slug, { slug: h.slug, title: h.title, count: 1 });
    }
  }
  return [...seen.values()];
}

/** Docs-tree snippet candidates: every file expressed relative to the
 *  source file's directory and filtered by the typed partial (no silent
 *  result cap — the caller bounds the final list). */
export function snippetDocCandidates(
  files: Array<{ srcUri: string }>, fromDir: string, partial: string, keepDotSlash: boolean,
): string[] {
  const out: string[] = [];
  for (const f of files) {
    const display = toRelativeDisplay(f.srcUri, fromDir, keepDotSlash);
    if (display.startsWith(partial)) {
      out.push(display);
    }
  }
  return out;
}

/** Frontmatter keys understood by the engine (completion source; custom keys
 *  stay legal, so unknown keys are never diagnosed). */
export const FRONTMATTER_KEYS: Array<{ key: string; detail: string }> = [
  { key: 'title', detail: 'Override the page title' },
  { key: 'description', detail: 'Page description (search, social cards)' },
  { key: 'icon', detail: 'Nav/tab icon, e.g. material/home' },
  { key: 'tags', detail: 'Tag list, e.g. [guide, setup]' },
  { key: 'hide', detail: 'Hide page parts: navigation, toc' },
  { key: 'search', detail: 'Search options: exclude, boost' },
  { key: 'template', detail: 'Custom template, e.g. main.html' },
  { key: 'date', detail: 'Blog post date (YYYY-MM-DD)' },
  { key: 'authors', detail: 'Blog post author list' },
];

/** Value completions for `hide:` list items. */
export const HIDE_VALUES = ['navigation', 'toc'];

/** Child keys for a `search:` mapping. */
export const SEARCH_CHILD_KEYS: Array<{ key: string; detail: string }> = [
  { key: 'exclude', detail: 'true to drop the page from search' },
  { key: 'boost', detail: 'Ranking boost, e.g. 2' },
];
