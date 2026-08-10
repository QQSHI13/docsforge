import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

import {
  extractLinks,
  extractHeadings,
  splitAnchor,
  resolveLinkTarget,
  lineOfLink,
  linkFromWarning,
  severityForLevel,
  docsDirFromConfig,
  loadValidation,
  docAbsPath,
} from '../src/links';

describe('links helpers', () => {
  describe('extractLinks', () => {
    it('finds inline links with lines', () => {
      const src = '# Home\n\nSee [docs](guide.md#install) and ![img](a.png).';
      const links = extractLinks(src);
      assert.deepStrictEqual(
        links.map((l) => ({ dest: l.dest, line: l.line })),
        [
          { dest: 'guide.md#install', line: 2 },
          { dest: 'a.png', line: 2 },
        ],
      );
    });

    it('skips links without parens', () => {
      assert.deepStrictEqual(extractLinks('no [links] here'), []);
    });
  });

  describe('extractHeadings', () => {
    it('extracts ATX headings with levels', () => {
      const src = '# One\n\n## Two\n### Three\n';
      assert.deepStrictEqual(extractHeadings(src), [
        { level: 1, title: 'One', line: 0 },
        { level: 2, title: 'Two', line: 2 },
        { level: 3, title: 'Three', line: 3 },
      ]);
    });

    it('ignores non-headings', () => {
      assert.deepStrictEqual(extractHeadings('plain\n##\n###\ntext'), []);
    });
  });

  describe('splitAnchor', () => {
    it('splits target and anchor', () => {
      assert.deepStrictEqual(splitAnchor('a.md#sec'), { target: 'a.md', anchor: 'sec' });
    });
    it('returns target only when no anchor', () => {
      assert.deepStrictEqual(splitAnchor('a.md'), { target: 'a.md' });
    });
  });

  describe('resolveLinkTarget', () => {
    const docs = '/site/docs';

    it('resolves same-dir links', () => {
      const r = resolveLinkTarget(docs, 'a/b.md', 'c.md');
      assert.strictEqual(r?.srcUri, 'a/c.md');
      assert.strictEqual(r?.absPath, path.join(docs, 'a', 'c.md'));
    });

    it('resolves parent links', () => {
      const r = resolveLinkTarget(docs, 'a/b.md', '../top.md');
      assert.strictEqual(r?.srcUri, 'top.md');
    });

    it('rejects escaping the docs dir', () => {
      assert.strictEqual(resolveLinkTarget(docs, 'a/b.md', '../../x.md'), null);
    });
  });

  describe('lineOfLink', () => {
    it('finds the line of a link dest', () => {
      const src = '# A\n\nSee [b](other.md#x).\n';
      assert.strictEqual(lineOfLink(src, 'other.md#x'), 2);
    });
    it('returns null when absent', () => {
      assert.strictEqual(lineOfLink('nothing here', 'x.md'), null);
    });
  });

  describe('linkFromWarning', () => {
    it('extracts the link from a validation warning', () => {
      assert.strictEqual(
        linkFromWarning("Doc file 'a.md' contains a link 'b.md#x', but the target is not found."),
        'b.md#x',
      );
    });
    it('returns null without a link', () => {
      assert.strictEqual(linkFromWarning('no link here'), null);
    });
  });

  describe('severityForLevel', () => {
    it('maps python logging levels', () => {
      assert.strictEqual(severityForLevel(40), 0); // ERROR
      assert.strictEqual(severityForLevel(30), 1); // WARNING
      assert.strictEqual(severityForLevel(20), 2); // INFO
    });
  });

  describe('docsDirFromConfig', () => {
    let tmp: string;
    beforeEach(() => {
      tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-vscode-'));
    });
    afterEach(() => {
      fs.rmSync(tmp, { recursive: true, force: true });
    });

    it('reads docs_dir from docsforge.yml', () => {
      fs.writeFileSync(path.join(tmp, 'docsforge.yml'), 'site_name: X\ndocs_dir: content\n');
      assert.strictEqual(docsDirFromConfig(tmp), 'content');
    });

    it('defaults to docs', () => {
      assert.strictEqual(docsDirFromConfig(tmp), 'docs');
    });
  });

  describe('loadValidation', () => {
    let tmp: string;
    beforeEach(() => {
      tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-vscode-'));
    });
    afterEach(() => {
      fs.rmSync(tmp, { recursive: true, force: true });
    });

    it('parses validation.json', () => {
      const dir = path.join(tmp, '.docsforge', 'cache');
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(
        path.join(dir, 'validation.json'),
        JSON.stringify({ 'a.md': { warnings: [[30, 'warn']] } }),
      );
      const data = loadValidation(tmp);
      assert.deepStrictEqual(data['a.md']?.warnings, [[30, 'warn']]);
    });

    it('returns empty when missing', () => {
      assert.deepStrictEqual(loadValidation(tmp), {});
    });
  });

  describe('docAbsPath', () => {
    it('joins docs dir with src uri', () => {
      assert.strictEqual(
        docAbsPath('/w', 'docs', 'a/b.md'),
        path.join('/w', 'docs', 'a', 'b.md'),
      );
    });
  });
});
