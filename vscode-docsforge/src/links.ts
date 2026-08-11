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

/** Slugify a heading title the way docsforge/markdown-toc does:
 *  lowercase, strip punctuation, whitespace → '-'. */
export function slugifyHeading(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
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

/** Strip the locale suffix from a doc name: foo.zh.md -> foo, foo.md -> foo. */
export function stripLocaleSuffix(srcUri: string): string {
  return srcUri.replace(/(\.[a-z]{2}(?:-[a-z]{2})?)?\.md$/, '');
}

/** Given a base doc name, return the variant name if srcUri is one.
 *  e.g. localeVariantOf('foo.zh.md', 'foo') -> 'foo.zh.md'; null otherwise. */
export function localeVariantOf(srcUri: string, base: string): string | null {
  const prefix = `${base}.`;
  if (srcUri.startsWith(prefix) && srcUri.endsWith('.md')) {
    const locale = srcUri.slice(prefix.length, -3);
    if (/^[a-z]{2}(-[a-z]{2})?$/.test(locale)) {
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
 * resolves to docSrcUri.
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
      if (!target || !anchor || anchor !== oldSlug) {
        continue;
      }
      const resolved = resolveLinkTarget(docsDirAbs, doc.srcUri, target);
      if (!resolved || resolved.srcUri !== docSrcUri) {
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
