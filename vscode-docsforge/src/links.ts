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

/** Find the line number of a link destination within a source file. */
export function lineOfLink(source: string, dest: string): number | null {
  const escaped = dest.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(`\\(\\s*${escaped}[\\s)]`);
  const lines = source.split('\n');
  for (let i = 0; i < lines.length; i++) {
    if (re.test(lines[i])) {
      return i;
    }
  }
  return null;
}
