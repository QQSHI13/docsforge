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

/** Absolute path of a doc uri inside the workspace docs dir. */
export function docAbsPath(workspaceRoot: string, docsDir: string, srcUri: string): string {
  return path.join(workspaceRoot, docsDir, ...srcUri.split('/'));
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
  const base = path.posix.join(path.posix.dirname(srcUri), target);
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

/** Find all links in a markdown source: [text](dest) and ![alt](dest). */
export function extractLinks(source: string): Array<{ dest: string; offset: number; line: number }> {
  const links: Array<{ dest: string; offset: number; line: number }> = [];
  const re = /!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+["'][^"']*["'])?\s*\)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(source)) !== null) {
    const line = source.slice(0, m.index).split('\n').length - 1;
    links.push({ dest: m[1], offset: m.index, line });
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

/** Parse docsforge.yml for the docs_dir (default 'docs'). */
export function docsDirFromConfig(workspaceRoot: string): string {
  for (const name of ['docsforge.yml', 'docsforge.yaml']) {
    const p = path.join(workspaceRoot, name);
    if (!fs.existsSync(p)) {
      continue;
    }
    try {
      const text = fs.readFileSync(p, 'utf-8');
      const m = text.match(/^docs_dir\s*:\s*["']?([^"'\s#]+)/m);
      if (m) {
        return m[1];
      }
    } catch {
      /* ignore */
    }
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
    const close = line.indexOf(')', link.offset);
    const end = close === -1 ? line.length : close + 1;
    if (character >= link.offset && character <= end) {
      return link;
    }
  }
  return null;
}

/** Slugify a heading title the way docsforge/markdown-toc does:
 *  lowercase, strip punctuation, whitespace → '-'.
 *  Unicode-aware: the engine's Python `\w` keeps CJK, so `# 你好` slugs to
 *  `你好` — an ASCII-only class would yield `''` and break anchor jumps. */
export function slugifyHeading(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s_-]/gu, '')
    .replace(/[\s_]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
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

/**
 * Compute edits for renaming a heading anchor: rewrite every link across the
 * docs tree whose anchor slug matches oldSlug into newSlug, when the link
 * resolves to docSrcUri. Anchor-only links (`[#slug]`, same page) resolve
 * to their own file and are rewritten too.
 */
export function computeAnchorRenameEdits(
  workspaceRoot: string,
  docSrcUri: string,
  oldSlug: string,
  newSlug: string,
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
      if (!anchor || anchor !== oldSlug) {
        continue;
      }
      // Empty target = same-page link: only the file being renamed matches.
      const resolvedSrc = target
        ? resolveLinkTarget(docsDirAbs, doc.srcUri, target)?.srcUri ?? null
        : doc.srcUri;
      if (resolvedSrc !== docSrcUri) {
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
  return edits;
}

/* ------------------------------------------------------------------ */
/* Footnote / formatting diagnostics (Zensical-style breadth)         */
/* ------------------------------------------------------------------ */

/** Footnote references `[^label]` and definitions `[^label]: …`. */
export function checkFootnotes(
  source: string,
): Array<{ line: number; message: string; kind: 'unresolved' | 'duplicate' }> {
  const warnings: Array<{ line: number; message: string; kind: 'unresolved' | 'duplicate' }> = [];
  const refs = new Map<string, number>();   // label -> first line
  const defs = new Map<string, number>();   // label -> first line
  const lines = source.split('\n');
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
    const fenceMatch = line.match(/^\s*(`{3,}|~{3,})/);
    if (fenceMatch) {
      const marker = fenceMatch[1][0] === '`' ? '`' : '~';
      const len = fenceMatch[1].length;
      if (fence === null) {
        fence = `${marker}${len}`;
      } else if (fence[0] === marker && len >= Number(fence.slice(1))) {
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
