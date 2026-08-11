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
  linesOfLink,
  linkFromWarning,
  severityForLevel,
  docsDirFromConfig,
  loadValidation,
  docAbsPath,
  slugifyHeading,
  computeAnchorRenameEdits,
  computeDocumentRename,
  computeRenameEdits,
  computeFolderRename,
  stripLocaleSuffix,
  checkFootnotes,
  formatMarkdown,
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

  describe('linesOfLink', () => {
    it('finds every matching line', () => {
      const src = '[a](#x)\nno\n[a](#x)\n';
      assert.deepStrictEqual(linesOfLink(src, '#x'), [0, 2]);
    });
    it('returns empty when absent', () => {
      assert.deepStrictEqual(linesOfLink('nothing', '#x'), []);
    });
  });

  describe('stripLocaleSuffix', () => {
    it('strips 2-letter locale', () => {
      assert.strictEqual(stripLocaleSuffix('foo.zh.md'), 'foo');
    });
    it('keeps base name', () => {
      assert.strictEqual(stripLocaleSuffix('foo.md'), 'foo');
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

  describe('slugifyHeading', () => {
    it('lowercases and dashes', () => {
      assert.strictEqual(slugifyHeading('My Heading!'), 'my-heading');
      assert.strictEqual(slugifyHeading('Section Title?'), 'section-title');
      assert.strictEqual(slugifyHeading('A B C'), 'a-b-c');
    });
  });

  describe('rename edits', () => {
    let tmp: string;
    beforeEach(() => {
      tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-vscode-'));
      fs.mkdirSync(path.join(tmp, 'docs'), { recursive: true });
      fs.writeFileSync(path.join(tmp, 'docsforge.yml'), 'site_name: T\ndocs_dir: docs\n');
    });
    afterEach(() => {
      fs.rmSync(tmp, { recursive: true, force: true });
    });

    it('computeRenameEdits rewrites links to a renamed doc', () => {
      fs.writeFileSync(path.join(tmp, 'docs', 'a.md'), '# A\n\n[Sec](b.md#x)\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'b.md'), '# B\n');
      const edits = computeRenameEdits(tmp, 'b.md', 'c.md');
      assert.strictEqual(edits.size, 1);
      const fileEdits = edits.get(path.join(tmp, 'docs', 'a.md'))!;
      assert.strictEqual(fileEdits.length, 1);
      assert.strictEqual(fileEdits[0].text, './c.md#x');
    });

    it('computeDocumentRename renames base + translations', () => {
      fs.writeFileSync(path.join(tmp, 'docs', 'a.md'), '# A\n\n[Sec](b.md#x)\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'b.md'), '# B\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'b.zh.md'), '# B 中文\n');
      const { files, edits } = computeDocumentRename(tmp, 'b.md', 'c');
      // Both variants renamed.
      assert.strictEqual(files.size, 2);
      assert.strictEqual(files.get(path.join(tmp, 'docs', 'b.md')), path.join(tmp, 'docs', 'c.md'));
      assert.strictEqual(files.get(path.join(tmp, 'docs', 'b.zh.md')), path.join(tmp, 'docs', 'c.zh.md'));
      // Link to base rewritten.
      const fileEdits = edits.get(path.join(tmp, 'docs', 'a.md'))!;
      assert.strictEqual(fileEdits[0].text, './c.md#x');
    });

    it('computeDocumentRename works when editing a translation file', () => {
      fs.writeFileSync(path.join(tmp, 'docs', 'a.zh.md'), '# A\n\n[Sec](b.zh.md#x)\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'b.md'), '# B\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'b.zh.md'), '# B 中文\n');
      const { files, edits } = computeDocumentRename(tmp, 'b.zh.md', 'c');
      assert.strictEqual(files.size, 2);
      assert.strictEqual(files.get(path.join(tmp, 'docs', 'b.zh.md')), path.join(tmp, 'docs', 'c.zh.md'));
      // Link to the zh variant rewritten to the new zh name.
      const fileEdits = edits.get(path.join(tmp, 'docs', 'a.zh.md'))!;
      assert.strictEqual(fileEdits[0].text, './c.zh.md#x');
    });

    it('computeDocumentRename leaves unrelated variants alone', () => {
      fs.writeFileSync(path.join(tmp, 'docs', 'b.md'), '# B\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'b.fr.md'), '# B FR\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'other.md'), '# O\n');
      const { files } = computeDocumentRename(tmp, 'b.md', 'c');
      assert.strictEqual(files.size, 2); // b.md + b.fr.md only
      assert.ok(!files.has(path.join(tmp, 'docs', 'other.md')));
    });

    it('computeAnchorRenameEdits rewrites links with the old anchor', () => {
      fs.writeFileSync(path.join(tmp, 'docs', 'a.md'), '# A\n\n[Sec](b.md#old-anchor)\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'b.md'), '# B\n\n## Old Anchor\n');
      const edits = computeAnchorRenameEdits(tmp, 'b.md', 'old-anchor', 'new-anchor');
      assert.strictEqual(edits.size, 1);
      const fileEdits = edits.get(path.join(tmp, 'docs', 'a.md'))!;
      assert.strictEqual(fileEdits.length, 1);
      assert.strictEqual(fileEdits[0].text, 'new-anchor');
    });

    it('computeAnchorRenameEdits ignores links to other docs', () => {
      fs.writeFileSync(path.join(tmp, 'docs', 'a.md'), '# A\n\n[Sec](c.md#old-anchor)\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'b.md'), '# B\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'c.md'), '# C\n\n## Old Anchor\n');
      const edits = computeAnchorRenameEdits(tmp, 'b.md', 'old-anchor', 'new-anchor');
      assert.strictEqual(edits.size, 0);
    });
  });
});

describe('footnote diagnostics', () => {
  it('flags unresolved footnotes', () => {
    const src = 'Text[^a] and [^b].\n\n[^a]: defined\n';
    const w = checkFootnotes(src);
    assert.deepStrictEqual(w.map((x) => x.kind), ['unresolved']);
    assert.ok(w[0].message.includes('Unresolved footnote: [^b]'));
  });

  it('flags duplicate definitions', () => {
    const src = '[^a]: one\n\n[^a]: two\n';
    const w = checkFootnotes(src);
    assert.ok(w.some((x) => x.kind === 'duplicate'));
  });

  it('no warnings for well-formed footnotes', () => {
    assert.deepStrictEqual(checkFootnotes('Text[^a]\n\n[^a]: def\n'), []);
  });
});

describe('formatMarkdown', () => {
  it('strips trailing whitespace and collapses blank runs', () => {
    const src = '# H  \n\n\n\nbody  \n\n';
    assert.strictEqual(formatMarkdown(src), '# H\n\nbody\n');
  });
});

describe('computeFolderRename', () => {
  let tmp: string;
  beforeEach(() => {
    tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-vscode-'));
    fs.mkdirSync(path.join(tmp, 'docs', 'guide'), { recursive: true });
    fs.writeFileSync(path.join(tmp, 'docsforge.yml'), 'site_name: T\ndocs_dir: docs\n');
  });
  afterEach(() => {
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  it('renames links into a moved folder', () => {
    fs.writeFileSync(path.join(tmp, 'docs', 'guide', 'a.md'), '# A\n');
    fs.writeFileSync(path.join(tmp, 'docs', 'index.md'), '# I\n\n[See](guide/a.md)\n');
    const { files, edits } = computeFolderRename(tmp, 'guide', 'ref');
    assert.strictEqual(files.size, 1);
    assert.strictEqual(files.get(path.join(tmp, 'docs', 'guide', 'a.md')),
      path.join(tmp, 'docs', 'ref', 'a.md'));
    const fileEdits = edits.get(path.join(tmp, 'docs', 'index.md'))!;
    assert.strictEqual(fileEdits[0].text, './ref/a.md');
  });
});
