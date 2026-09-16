/**
 * Studio-owned on-disk cache under `.docsforge/studio/` (gitignored like the
 * rest of `.docsforge/`): an mtime-validated heading index so anchor
 * completion and anchor checks don't re-read + re-parse target files on
 * every keystroke.
 *
 * Shape: `{ version: 1, files: { [absPath]: { mtimeMs, headings } } }`.
 * Best-effort only: every read/write is guarded so a corrupt or unwritable
 * cache degrades to direct file reads, never to a broken feature.
 */
import * as fs from 'fs';
import * as path from 'path';
import { extractHeadings, slugifyHeading } from './links';

export interface CachedHeading {
  title: string;
  slug: string;
  line: number;
}

interface StoreFile {
  mtimeMs: number;
  headings: CachedHeading[];
}

interface Store {
  version: 1;
  files: Record<string, StoreFile>;
}

const STORE_VERSION = 1;

/** Absolute path of the Studio cache file for a workspace root. */
export function studioCachePath(workspaceRoot: string): string {
  return path.join(workspaceRoot, '.docsforge', 'studio', 'headings.json');
}

function freshStore(): Store {
  return { version: STORE_VERSION, files: {} };
}

function readStore(workspaceRoot: string): Store {
  try {
    const raw = fs.readFileSync(studioCachePath(workspaceRoot), 'utf-8');
    const parsed = JSON.parse(raw) as Partial<Store>;
    if (parsed?.version === STORE_VERSION && parsed.files && typeof parsed.files === 'object') {
      return { version: STORE_VERSION, files: parsed.files };
    }
  } catch {
    /* missing / corrupt → recompute */
  }
  return freshStore();
}

function writeStore(workspaceRoot: string, store: Store): void {
  try {
    fs.mkdirSync(path.dirname(studioCachePath(workspaceRoot)), { recursive: true });
    fs.writeFileSync(studioCachePath(workspaceRoot), JSON.stringify(store));
  } catch {
    /* unwritable (read-only checkout) → callers already have the data */
  }
}

/** Headings (+ slugs) for a doc, served from cache when mtime matches. */
export function getHeadings(workspaceRoot: string, absPath: string): CachedHeading[] {
  let mtimeMs = 0;
  try {
    mtimeMs = fs.statSync(absPath).mtimeMs;
  } catch {
    return [];
  }
  const store = readStore(workspaceRoot);
  const hit = store.files[absPath];
  if (hit && hit.mtimeMs === mtimeMs && Array.isArray(hit.headings)) {
    return hit.headings;
  }
  let text: string;
  try {
    text = fs.readFileSync(absPath, 'utf-8');
  } catch {
    return [];
  }
  const headings = extractHeadings(text).map((h) => ({
    title: h.title,
    slug: slugifyHeading(h.title),
    line: h.line,
  }));
  store.files[absPath] = { mtimeMs, headings };
  // Bound growth: drop entries for deleted files on write.
  for (const key of Object.keys(store.files)) {
    if (key !== absPath && !fs.existsSync(key)) {
      delete store.files[key];
    }
  }
  writeStore(workspaceRoot, store);
  return headings;
}

/** Drop one file (or everything) from the cache. */
export function invalidateHeadings(workspaceRoot: string, absPath?: string): void {
  if (absPath) {
    const store = readStore(workspaceRoot);
    if (store.files[absPath]) {
      delete store.files[absPath];
      writeStore(workspaceRoot, store);
    }
    return;
  }
  try {
    fs.rmSync(studioCachePath(workspaceRoot), { force: true });
  } catch {
    /* ignore */
  }
}
