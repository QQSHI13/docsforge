import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

import { shouldEscalateToSigkill } from '../src/pure';
import {
  extractLinks,
  srcUriOfPath,
  linkTargetPrefix,
  filterDocsByPrefix,
  isFolderRenameEvent,
  findRenameCollision,
  collectFootnoteWarnings,
  tryLoadValidation,
  slugifyHeading,
} from '../src/links';

describe('studio fixes', () => {
  describe('fix 4: SIGKILL escalation (pure exit-state check)', () => {
    it('escalates when the process is still running', () => {
      assert.strictEqual(
        shouldEscalateToSigkill({ exitCode: null, signalCode: null }),
        true,
      );
    });

    it('does not escalate after exit or signal', () => {
      assert.strictEqual(
        shouldEscalateToSigkill({ exitCode: 0, signalCode: null }),
        false,
      );
      assert.strictEqual(
        shouldEscalateToSigkill({ exitCode: null, signalCode: 'SIGTERM' }),
        false,
      );
      assert.strictEqual(
        shouldEscalateToSigkill({ exitCode: 1, signalCode: null }),
        false,
      );
    });
  });

  describe('fix 6: all links per line (images, titles, repeats)', () => {
    it('finds multiple links on one line', () => {
      const links = extractLinks('[a](x.md) and [b](y.md)');
      assert.deepStrictEqual(links.map((l) => l.dest), ['x.md', 'y.md']);
    });

    it('finds images and titled links', () => {
      const links = extractLinks('![alt](img.png) and [t](doc.md "Title")');
      assert.deepStrictEqual(links.map((l) => l.dest), ['img.png', 'doc.md']);
    });

    it('finds repeated anchors on one line', () => {
      const links = extractLinks('[a](#x) [b](#x)');
      assert.strictEqual(links.length, 2);
    });
  });

  describe('fix 8: atomic rename pre-validation', () => {
    let tmp: string;
    beforeEach(() => {
      tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-fix8-'));
    });
    afterEach(() => {
      fs.rmSync(tmp, { recursive: true, force: true });
    });

    it('returns null when no collision', () => {
      const files = new Map([
        [path.join(tmp, 'a.md'), path.join(tmp, 'b.md')],
      ]);
      assert.strictEqual(findRenameCollision(files), null);
    });

    it('detects an existing target on disk', () => {
      fs.writeFileSync(path.join(tmp, 'b.md'), '# B\n');
      const files = new Map([
        [path.join(tmp, 'a.md'), path.join(tmp, 'b.md')],
      ]);
      assert.strictEqual(findRenameCollision(files), path.join(tmp, 'b.md'));
    });

    it('detects duplicate targets within the map', () => {
      const files = new Map([
        [path.join(tmp, 'a.md'), path.join(tmp, 'c.md')],
        [path.join(tmp, 'b.md'), path.join(tmp, 'c.md')],
      ]);
      assert.strictEqual(findRenameCollision(files), path.join(tmp, 'c.md'));
    });
  });

  describe('fix 9: folder rename detection via newUri', () => {
    let tmp: string;
    beforeEach(() => {
      tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-fix9-'));
    });
    afterEach(() => {
      fs.rmSync(tmp, { recursive: true, force: true });
    });

    it('detects a folder from the new path even when old is gone', () => {
      const dir = path.join(tmp, 'guide');
      fs.mkdirSync(dir);
      // Old path no longer exists post-move; new path is a directory.
      assert.strictEqual(isFolderRenameEvent(path.join(tmp, 'old'), dir), true);
    });

    it('treats .md renames as files', () => {
      assert.strictEqual(
        isFolderRenameEvent(path.join(tmp, 'a.md'), path.join(tmp, 'b.md')),
        false,
      );
    });

    it('falls back to heuristic when neither path exists', () => {
      assert.strictEqual(
        isFolderRenameEvent(path.join(tmp, 'oldDir'), path.join(tmp, 'newDir')),
        true,
      );
      assert.strictEqual(
        isFolderRenameEvent(path.join(tmp, 'a.md'), path.join(tmp, 'b.md')),
        false,
      );
    });
  });

  describe('fix 10: validation parse + footnotes independent of map', () => {
    let tmp: string;
    beforeEach(() => {
      tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-fix10-'));
      fs.mkdirSync(path.join(tmp, 'docs'), { recursive: true });
      fs.writeFileSync(path.join(tmp, 'docsforge.yml'), 'site_name: T\ndocs_dir: docs\n');
    });
    afterEach(() => {
      fs.rmSync(tmp, { recursive: true, force: true });
    });

    it('tryLoadValidation ok-empty when missing', () => {
      const r = tryLoadValidation(tmp);
      assert.strictEqual(r.ok, true);
      if (r.ok) {
        assert.deepStrictEqual(r.data, {});
      }
    });

    it('tryLoadValidation fails closed on corrupt JSON', () => {
      const dir = path.join(tmp, '.docsforge', 'cache');
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, 'validation.json'), '{oops');
      assert.strictEqual(tryLoadValidation(tmp).ok, false);
    });

    it('tryLoadValidation parses valid JSON', () => {
      const dir = path.join(tmp, '.docsforge', 'cache');
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(
        path.join(dir, 'validation.json'),
        JSON.stringify({ 'a.md': { warnings: [] } }),
      );
      const r = tryLoadValidation(tmp);
      assert.strictEqual(r.ok, true);
    });

    it('collectFootnoteWarnings covers files absent from validation', () => {
      fs.writeFileSync(path.join(tmp, 'docs', 'clean.md'), '# C\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'broken.md'), 'Ref[^x]\n');
      const got = collectFootnoteWarnings(path.join(tmp, 'docs'));
      assert.ok(!got.has(path.join(tmp, 'docs', 'clean.md')));
      assert.ok(got.has(path.join(tmp, 'docs', 'broken.md')));
    });
  });

  describe('fix 11: docs-relative URIs and canonical slugs', () => {
    it('srcUriOfPath returns null outside the docs dir', () => {
      const docs = path.join('/w', 'docs');
      assert.strictEqual(srcUriOfPath(docs, path.join('/w', 'README.md')), null);
      assert.strictEqual(srcUriOfPath(docs, path.join('/w', 'docs')), null);
      assert.strictEqual(
        srcUriOfPath(docs, path.join('/w', 'docs', 'a.md')),
        'a.md',
      );
    });

    it('linkTargetPrefix only fires inside ](…)', () => {
      assert.strictEqual(linkTargetPrefix('see [t](par'), 'par');
      assert.strictEqual(linkTargetPrefix('fn(arg'), null);
      assert.strictEqual(linkTargetPrefix('plain text'), null);
    });

    it('filterDocsByPrefix prunes by directory', () => {
      const files = [{ srcUri: 'guide/a.md' }, { srcUri: 'ref/b.md' }];
      assert.deepStrictEqual(filterDocsByPrefix(files, 'guide/', 10), ['guide/a.md']);
      assert.deepStrictEqual(filterDocsByPrefix(files, '', 10).length, 2);
    });

    it('slugifyHeading is the single canonical slug', () => {
      // Underscore/heading edge where the old ad-hoc regex diverged.
      assert.strictEqual(slugifyHeading('Hello_World'), 'hello-world');
      assert.strictEqual(slugifyHeading('Hello_World'), slugifyHeading('hello_world'));
    });
  });
});
