import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

import { getHeadings, invalidateHeadings, studioCachePath } from '../src/studioCache';

describe('studio headings cache', () => {
  let tmp: string;
  let doc: string;

  beforeEach(() => {
    tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-cache-'));
    doc = path.join(tmp, 'a.md');
    fs.writeFileSync(doc, '# Hello World\n\n## Sub_Section\n');
  });
  afterEach(() => {
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  it('indexes headings with slugs and persists the store', () => {
    const got = getHeadings(tmp, doc);
    assert.deepStrictEqual(got.map((h) => h.slug), ['hello-world', 'sub-section']);
    assert.ok(fs.existsSync(studioCachePath(tmp)));
    // Second call is served from cache (delete source → stale-free hit).
    const again = getHeadings(tmp, doc);
    assert.deepStrictEqual(again, got);
  });

  it('recomputes after edits (mtime validation)', async () => {
    assert.strictEqual(getHeadings(tmp, doc).length, 2);
    await new Promise((r) => setTimeout(r, 5));
    fs.writeFileSync(doc, '# Only\n');
    assert.deepStrictEqual(getHeadings(tmp, doc).map((h) => h.slug), ['only']);
  });

  it('survives a corrupt store', () => {
    getHeadings(tmp, doc);
    fs.writeFileSync(studioCachePath(tmp), '{oops');
    assert.strictEqual(getHeadings(tmp, doc).length, 2);
  });

  it('returns empty for missing files and invalidates', () => {
    assert.deepStrictEqual(getHeadings(tmp, path.join(tmp, 'nope.md')), []);
    getHeadings(tmp, doc);
    invalidateHeadings(tmp, doc);
    const store = JSON.parse(fs.readFileSync(studioCachePath(tmp), 'utf-8'));
    assert.ok(!(doc in store.files));
  });
});
