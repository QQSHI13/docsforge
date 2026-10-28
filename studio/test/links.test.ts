import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

import {
  extractLinks,
  extractLinksRaw,
  maskCode,
  extractHeadings,
  splitAnchor,
  resolveLinkTarget,
  lineOfLink,
  linesOfLink,
  linkAtPosition,
  docAbsPathSafe,
  toRelativeDisplay,
  linkFromWarning,
  severityForLevel,
  docsDirFromConfig,
  parseDocsDir,
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
  fenceMarker,
  inFencedCode,
  matchAnchors,
  snippetDocCandidates,
  detectLocales,
  findMissingTwins,
  sanitizePageName,
  humanizePageName,
  parseNavParents,
  appendNavEntry,
  snippetPathPrefix,
  anchorPrefix,
  frontmatterRange,
  FRONTMATTER_KEYS,
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

    it('finds destinations containing spaces', () => {
      // python-markdown renders both of these with a space in the href, so the
      // scanner must see them too - otherwise rename leaves a dead link and no
      // hover/definition/quick-fix fires on it.
      const src = 'a [one](my page.md) b [two](<other page.md>) c';
      assert.deepStrictEqual(
        extractLinks(src).map((l) => l.dest),
        ['my page.md', 'other page.md'],
      );
    });

    it('strips a trailing link title', () => {
      assert.deepStrictEqual(
        extractLinks('[a](x.md "the title")').map((l) => l.dest),
        ['x.md'],
      );
      assert.deepStrictEqual(
        extractLinks(`[a](y.md 'the title')`).map((l) => l.dest),
        ['y.md'],
      );
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

  describe('link offsets', () => {
    it('records the opening paren so offset + 1 is the destination', () => {
      // Every consumer computes edits as `offset + 1 … offset + 1 + len`; the
      // old match-start offset landed on the closing `]` and rewrote labels.
      const src = 'See [text](target.md) here.';
      const [link] = extractLinks(src);
      assert.strictEqual(src[link.offset], '(');
      assert.strictEqual(src.slice(link.offset + 1, link.offset + 1 + link.dest.length), 'target.md');
    });

    it('keeps offsets correct for images and repeated links', () => {
      const src = '![img](a.png) [x](b.md) [y](b.md)';
      for (const link of extractLinks(src)) {
        assert.strictEqual(src[link.offset], '(');
        assert.strictEqual(src.slice(link.offset + 1, link.offset + 1 + link.dest.length), link.dest);
      }
    });

    it('linkAtPosition hits the label and the destination', () => {
      const line = 'see [text](target.md) end';
      const links = extractLinks(line);
      assert.strictEqual(linkAtPosition(line, links, 6)?.dest, 'target.md'); // inside '[text]'
      assert.strictEqual(linkAtPosition(line, links, 12)?.dest, 'target.md'); // inside dest
      assert.strictEqual(linkAtPosition(line, links, 23), null); // after it
    });
  });

  describe('extractLinks on Windows separators', () => {
    it('normalizes backslashes in the destination', () => {
      const links = extractLinks('a [one](guide\\foo.md#sec) b');
      assert.deepStrictEqual(links.map((l) => l.dest), ['guide/foo.md#sec']);
    });

    it('normalization is length-preserving', () => {
      const src = '[x](a\\b\\c.md)';
      const [link] = extractLinks(src);
      assert.strictEqual(src.slice(link.offset + 1, link.offset + 1 + link.dest.length), 'a\\b\\c.md');
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

    it('resolves Windows-style backslash targets', () => {
      // A link written `guide\\foo.md` must resolve with posix math; the
      // backslash used to make every match fail silently.
      const win = resolveLinkTarget('C:\\site\\docs', 'guide/index.md', 'sub\\foo.md');
      assert.strictEqual(win?.srcUri, 'guide/sub/foo.md');
      assert.strictEqual(win?.absPath, path.join('C:\\site\\docs', 'guide', 'sub', 'foo.md'));
      // Mixed separators resolve the same way.
      assert.strictEqual(
        resolveLinkTarget(docs, 'a/b.md', 'c\\d.md')?.srcUri,
        resolveLinkTarget(docs, 'a/b.md', 'c/d.md')?.srcUri,
      );
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

    it('reads a quoted docs_dir containing spaces', () => {
      // The old regex captured only `my` here, so every later path missed and
      // the extension went silent.
      fs.writeFileSync(path.join(tmp, 'docsforge.yml'), 'site_name: X\ndocs_dir: "my docs"\n');
      assert.strictEqual(docsDirFromConfig(tmp), 'my docs');
    });
  });

  describe('parseDocsDir', () => {
    it('reads quoted, unquoted and commented values', () => {
      assert.strictEqual(parseDocsDir('docs_dir: "my docs"\n'), 'my docs');
      assert.strictEqual(parseDocsDir("docs_dir: 'my docs'\n"), 'my docs');
      assert.strictEqual(parseDocsDir('docs_dir: content\n'), 'content');
      assert.strictEqual(parseDocsDir('docs_dir: content  # the docs\n'), 'content');
      assert.strictEqual(parseDocsDir('site_name: X\n  docs_dir: src/site\n'), 'src/site');
    });

    it('returns null when the key is absent or unusable', () => {
      assert.strictEqual(parseDocsDir('site_name: X\n'), null);
      assert.strictEqual(parseDocsDir('docs_dir:\n'), null);
      assert.strictEqual(parseDocsDir('docs_dir: ../escape\n'), null);
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
      const { edits, ambiguous } = computeAnchorRenameEdits(tmp, 'b.md', 'old-anchor', 'new-anchor');
      assert.strictEqual(ambiguous.length, 0);
      assert.strictEqual(edits.size, 1);
      const fileEdits = edits.get(path.join(tmp, 'docs', 'a.md'))!;
      assert.strictEqual(fileEdits.length, 1);
      assert.strictEqual(fileEdits[0].text, 'new-anchor');
    });

    it('computeAnchorRenameEdits ignores links to other docs', () => {
      fs.writeFileSync(path.join(tmp, 'docs', 'a.md'), '# A\n\n[Sec](c.md#old-anchor)\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'b.md'), '# B\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'c.md'), '# C\n\n## Old Anchor\n');
      const { edits } = computeAnchorRenameEdits(tmp, 'b.md', 'old-anchor', 'new-anchor');
      assert.strictEqual(edits.size, 0);
    });

    it('computeAnchorRenameEdits returns no edits for an empty slug', () => {
      fs.writeFileSync(path.join(tmp, 'docs', 'a.md'), '# A\n\n[Sec](b.md#install)\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'b.md'), '# B\n\n## Install\n');
      // `## !!!` slugifies to '' - an empty anchor is never a rename target.
      for (const [oldSlug, newSlug] of [['install', ''], ['', 'install']]) {
        const { edits } = computeAnchorRenameEdits(tmp, 'b.md', oldSlug, newSlug);
        assert.strictEqual(edits.size, 0);
      }
    });

    it('computeAnchorRenameEdits skips links when two headings share a slug', () => {
      // Both headings slugify to #install; rewriting every #install link would
      // repoint the ones that belong to the other heading.
      fs.writeFileSync(
        path.join(tmp, 'docs', 'a.md'),
        '# A\n\n[one](b.md#install) and [two](b.md#install)\n',
      );
      fs.writeFileSync(
        path.join(tmp, 'docs', 'b.md'),
        '# B\n\n## Install\n\ntext\n\n## Install!\n',
      );
      const { edits, ambiguous } = computeAnchorRenameEdits(tmp, 'b.md', 'install', 'setup');
      assert.deepStrictEqual(ambiguous.map((a) => a.line), [2, 6]);
      assert.strictEqual(edits.size, 0);
    });

    it('computeAnchorRenameEdits only touches links in the renamed heading\'s window', () => {
      // Same page, two #install headings: a link after the first heading but
      // before the second belongs to the first; the one after the second
      // belongs to the second.
      fs.writeFileSync(
        path.join(tmp, 'docs', 'b.md'),
        [
          '# B',
          '',
          '## Install',
          '',
          'see [a](#install)',
          '',
          '## Install!',
          '',
          'see [b](#install)',
          '',
        ].join('\n'),
      );
      const first = computeAnchorRenameEdits(tmp, 'b.md', 'install', 'setup', 2);
      assert.strictEqual(first.edits.get(path.join(tmp, 'docs', 'b.md'))!.length, 1);
      // Line 4 is the first occurrence's link; line 8 belongs to the second.
      const fileEdits = first.edits.get(path.join(tmp, 'docs', 'b.md'))!;
      const text = fs.readFileSync(path.join(tmp, 'docs', 'b.md'), 'utf-8');
      assert.strictEqual(text.slice(fileEdits[0].start, fileEdits[0].end), 'install');
      assert.ok(text.slice(0, fileEdits[0].start).endsWith('see [a](#'), 'link inside the first window');
      // Renaming the second occurrence hits only its own link.
      const second = computeAnchorRenameEdits(tmp, 'b.md', 'install', 'setup', 6);
      const secondEdits = second.edits.get(path.join(tmp, 'docs', 'b.md'))!;
      assert.strictEqual(secondEdits.length, 1);
      assert.ok(text.slice(0, secondEdits[0].start).endsWith('see [b](#'));
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

describe('translation twins', () => {
  const files = [
    { absPath: '/w/docs/a.md', srcUri: 'a.md' },
    { absPath: '/w/docs/a.zh.md', srcUri: 'a.zh.md' },
    { absPath: '/w/docs/guide/b.md', srcUri: 'guide/b.md' },
    { absPath: '/w/docs/lonely.fr.md', srcUri: 'lonely.fr.md' },
  ];

  it('detects locales', () => {
    assert.deepStrictEqual(detectLocales(files.map((f) => ({ srcUri: f.srcUri }))), ['fr', 'zh']);
    assert.deepStrictEqual(detectLocales([{ srcUri: 'a.md' }]), []);
  });

  it('flags missing twins and orphans', () => {
    const gaps = findMissingTwins(files, ['zh']);
    const missing = gaps.filter((g) => g.kind === 'missing');
    assert.deepStrictEqual(missing.map((g) => g.expected), ['guide/b.zh.md']);
    assert.strictEqual(missing[0].baseAbsPath, '/w/docs/guide/b.md');
    const orphans = gaps.filter((g) => g.kind === 'orphan');
    assert.deepStrictEqual(orphans.map((g) => g.expected), ['lonely.fr.md']);
  });

  it('is quiet when complete', () => {
    const full = [
      { absPath: '/w/a.md', srcUri: 'a.md' },
      { absPath: '/w/a.zh.md', srcUri: 'a.zh.md' },
    ];
    assert.deepStrictEqual(findMissingTwins(full, ['zh']), []);
  });
});

describe('page scaffolding', () => {
  it('sanitizes page names', () => {
    assert.strictEqual(sanitizePageName('my-page'), 'my-page.md');
    assert.strictEqual(sanitizePageName('guide/my-page.md'), 'guide/my-page.md');
    assert.strictEqual(sanitizePageName('../evil'), null);
    assert.strictEqual(sanitizePageName(''), null);
    assert.strictEqual(sanitizePageName('a/b/../c'), null);
  });

  it('humanizes file names', () => {
    assert.strictEqual(humanizePageName('guide/my-page.md'), 'My page');
    assert.strictEqual(humanizePageName('index.md'), 'Index');
  });

  const config = [
    'site_name: X',
    'nav:',
    '  - title: Home',
    '    path: index.md',
    '  - title: Guide',
    '    children:',
    '      - title: Install',
    '        path: guide/install.md',
    'theme:',
    '  name: material',
    '',
  ].join('\n');

  it('finds nav parents', () => {
    assert.deepStrictEqual(parseNavParents(config), ['Guide']);
  });

  it('appends top-level entries inside nav', () => {
    const next = appendNavEntry(config, 'New', 'new.md')!;
    assert.ok(next.includes('  - title: New\n    path: new.md\n'));
    assert.ok(next.indexOf('  - title: New') > next.indexOf('path: guide/install.md'));
    assert.ok(next.endsWith('theme:\n  name: material\n'));
  });

  it('appends under a parent', () => {
    const next = appendNavEntry(config, 'Usage', 'guide/usage.md', 'Guide')!;
    assert.ok(next.includes('      - title: Usage\n        path: guide/usage.md\n'));
  });

  it('returns null without nav or parent', () => {
    assert.strictEqual(appendNavEntry('site_name: X\n', 'N', 'n.md'), null);
    assert.strictEqual(appendNavEntry(config, 'N', 'n.md', 'Nope'), null);
  });

  it('quotes significant titles', () => {
    const next = appendNavEntry(config, 'A: B', 'ab.md')!;
    assert.ok(next.includes('- title: "A: B"'));
  });
});

describe('snippet and anchor prefixes', () => {
  it('finds snippet paths', () => {
    assert.strictEqual(snippetPathPrefix('--8<-- "inc/no'), 'inc/no');
    assert.strictEqual(snippetPathPrefix("-8<-- 'a.py"), 'a.py');
    assert.strictEqual(snippetPathPrefix('--8<-- "'), '');
    assert.strictEqual(snippetPathPrefix('plain "text'), null);
  });

  it('finds anchor context', () => {
    assert.deepStrictEqual(anchorPrefix('[t](guide.md#ins'), { target: 'guide.md', partial: 'ins' });
    assert.deepStrictEqual(anchorPrefix('[t](#sec'), { target: '', partial: 'sec' });
    assert.strictEqual(anchorPrefix('[t](guide.md'), null);
    assert.strictEqual(anchorPrefix('plain # text'), null);
  });
});

describe('frontmatter', () => {
  it('locates the block', () => {
    assert.deepStrictEqual(
      frontmatterRange('---\ntitle: X\n---\n# H\n'),
      { startLine: 0, endLine: 2 },
    );
    assert.strictEqual(frontmatterRange('# No block\n'), null);
    assert.strictEqual(frontmatterRange('---\nunclosed\n'), null);
  });

  it('curates engine-backed keys', () => {
    const keys = FRONTMATTER_KEYS.map((k) => k.key);
    for (const k of ['title', 'description', 'icon', 'tags', 'hide', 'search', 'template']) {
      assert.ok(keys.includes(k), k);
    }
  });
});

describe('review fixes', () => {
  it('slugifies CJK the way the engine does', () => {
    // Engine (markdown toc slugify, non-unicode mode) ASCII-folds: CJK has no
    // ASCII base so it is dropped, not kept. Verified against Python:
    //   slugify('你好', '-') == '' and slugify('Hello 你好', '-') == 'hello'.
    assert.strictEqual(slugifyHeading('你好'), '');
    assert.strictEqual(slugifyHeading('Hello 你好'), 'hello');
    assert.strictEqual(slugifyHeading('Hello_World'), 'hello_world');
  });

  it('matches locales case-insensitively', () => {
    assert.strictEqual(stripLocaleSuffix('a.ZH.md'), 'a');
    assert.strictEqual(stripLocaleSuffix('a.pt-BR.md'), 'a');
    assert.deepStrictEqual(
      detectLocales([{ srcUri: 'a.pt-BR.md' }, { srcUri: 'b.md' }]),
      ['pt-BR'],
    );
  });

  it('keeps fenced code blocks intact when formatting', () => {
    const src = '# H\n\n```\nline one  \n\n\nline two\n```\n\n\nbody  \n';
    assert.strictEqual(
      formatMarkdown(src),
      '# H\n\n```\nline one  \n\n\nline two\n```\n\nbody\n',
    );
  });

  it('tracks fenced code regions', () => {
    assert.strictEqual(fenceMarker('```python'), '```');
    assert.strictEqual(fenceMarker('  ~~~~'), '~~~~');
    assert.strictEqual(fenceMarker('plain'), null);
    const lines = ['# H', '', '```', '--8<-- "x"', '```', 'after'];
    assert.strictEqual(inFencedCode(lines, 3), true);
    assert.strictEqual(inFencedCode(lines, 5), false);
  });

  it('matches anchors case-insensitively and dedupes', () => {
    const got = matchAnchors(
      [
        { title: 'Install', slug: 'install' },
        { title: 'Install', slug: 'install' },
        { title: 'Intro', slug: 'intro' },
      ],
      'Ins',
    );
    assert.deepStrictEqual(got, [{ slug: 'install', title: 'Install', count: 2 }]);
  });

  it('lists every docs-tree snippet candidate', () => {
    const files = [
      { srcUri: 'guide/a.md' },
      { srcUri: 'guide/deep/b.md' },
      { srcUri: 'other/c.md' },
    ];
    assert.deepStrictEqual(
      snippetDocCandidates(files, 'guide', '', false).sort(),
      ['a.md', 'deep/b.md', '../other/c.md'].sort(),
    );
    assert.deepStrictEqual(
      snippetDocCandidates(files, 'guide', './deep', true),
      ['./deep/b.md'],
    );
  });

  it('finds the link under the cursor', () => {
    const line = '[a](x.md) and [b](y.md)';
    const links = extractLinks(line);
    assert.strictEqual(linkAtPosition(line, links, 2)?.dest, 'x.md');
    assert.strictEqual(linkAtPosition(line, links, 20)?.dest, 'y.md');
    assert.strictEqual(linkAtPosition(line, links, 11), null);
  });

  it('maps targets back to relative display form', () => {
    assert.strictEqual(toRelativeDisplay('guide/x.md', 'guide', false), 'x.md');
    assert.strictEqual(toRelativeDisplay('guide/x.md', 'guide', true), './x.md');
    assert.strictEqual(toRelativeDisplay('other/y.md', 'guide', false), '../other/y.md');
  });

  it('masks fenced and inline code, preserving offsets', () => {
    const src = 'See [a](a.md).\n\n```\n[x](nope.md) `[^y]`\n```\n\nUse `[^z]` here.\n';
    const masked = maskCode(src);
    assert.strictEqual(masked.length, src.length);
    assert.strictEqual(masked.split('\n').length, src.split('\n').length);
    // Raw scan still sees everything (documents what masking removes).
    assert.strictEqual(extractLinksRaw(src).length, 2);
    assert.deepStrictEqual(
      extractLinks(src).map((l) => l.dest),
      ['a.md'],
    );
    assert.deepStrictEqual(
      checkFootnotes(src).map((w) => w.kind),
      [],
    );
    assert.deepStrictEqual(
      checkFootnotes('Text[^a] and [^b].\n\n[^a]: defined\n').map((w) => w.kind),
      ['unresolved'],
    );
  });

  it('rejects escaping doc paths', () => {
    assert.strictEqual(docAbsPathSafe('/w', 'docs', '../evil.md'), null);
    assert.ok(docAbsPathSafe('/w', 'docs', 'a.md')?.endsWith(path.join('docs', 'a.md')));
  });

  it('rewrites same-page anchors on rename', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-anchor-'));
    try {
      fs.mkdirSync(path.join(tmp, 'docs'), { recursive: true });
      fs.writeFileSync(path.join(tmp, 'docsforge.yml'), 'site_name: T\ndocs_dir: docs\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'a.md'), '# Old Head\n\nSee [here](#old-head) and [o](b.md#old-head).\n');
      fs.writeFileSync(path.join(tmp, 'docs', 'b.md'), '# B\n');
      const aAbs = path.join(tmp, 'docs', 'a.md');
      // Renaming b.md's anchor: only the cross-page link moves.
      const forB = computeAnchorRenameEdits(tmp, 'b.md', 'old-head', 'new-head').edits;
      assert.strictEqual(forB.get(aAbs)?.length, 1);
      assert.strictEqual(forB.get(aAbs)![0].text, 'new-head');
      // Renaming a.md's anchor: only the same-page link moves.
      const forA = computeAnchorRenameEdits(tmp, 'a.md', 'old-head', 'new-head').edits;
      assert.strictEqual(forA.get(aAbs)?.length, 1);
      assert.strictEqual(forA.get(aAbs)![0].text, 'new-head');
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  });
});

describe('computeFolderRename', () => {  let tmp: string;
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

describe('slugifyHeading parity with engine', () => {
  // Reference vectors generated by the real engine:
  //   python -c "from markdown.extensions.toc import slugify; ..."
  // These pin the TS implementation to markdown.extensions.toc.slugify
  // (non-unicode mode: NFKD + ASCII-fold) so anchors predicted here match the
  // ids the build emits. If the engine slug changes, regenerate these.
  const CASES: Array<[string, string]> = [
    ['Getting Started (v2.0)', 'getting-started-v20'],
    ['Hello, World! 你好', 'hello-world'],
    ['  Multiple   spaces  ', 'multiple-spaces'],
    ['Café au lait', 'cafe-au-lait'],
    ['snake_case title', 'snake_case-title'],
    ['foo--bar__baz', 'foo-bar__baz'],
    ['100% Sure?', '100-sure'],
    ['Ünïcödé üüü', 'unicode-uuu'],
    ['你好 World', 'world'],
    ['a　b　c', 'a-b-c'],
    ['Intro: Part (1)', 'intro-part-1'],
    ['naïve résumé', 'naive-resume'],
    ['a_b  c', 'a_b-c'],
  ];
  for (const [input, expected] of CASES) {
    it(`slugs ${JSON.stringify(input)} -> ${JSON.stringify(expected)}`, () => {
      assert.strictEqual(slugifyHeading(input), expected);
    });
  }
});

describe('companion rename (auto-rename semantics)', () => {

  let tmp: string;
  beforeEach(() => {
    tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-vscode-'));
    fs.mkdirSync(path.join(tmp, 'docs'), { recursive: true });
    fs.writeFileSync(path.join(tmp, 'docsforge.yml'), 'site_name: T\ndocs_dir: docs\n');
  });
  afterEach(() => {
    fs.rmSync(tmp, { recursive: true, force: true });
  });

  it('renaming a .zh file renames the base companion too', () => {
    fs.writeFileSync(path.join(tmp, 'docs', 'migration.md'), '# M\n');
    fs.writeFileSync(path.join(tmp, 'docs', 'migration.zh.md'), '# M 中文\n');
    // Simulate VS Code already having moved the renamed file.
    fs.renameSync(path.join(tmp, 'docs', 'migration.zh.md'), path.join(tmp, 'docs', 'migratdsfion.zh.md'));
    const { files, edits } = computeDocumentRename(tmp, 'publishing/migration.zh.md'.replace('publishing/', ''), 'migratdsfion');
    // The base companion (still at old path) must be in the map.
    const baseOld = path.join(tmp, 'docs', 'migration.md');
    assert.ok(files.has(baseOld), 'base companion should be renamed');
    assert.strictEqual(files.get(baseOld), path.join(tmp, 'docs', 'migratdsfion.md'));
    void edits;
  });
});
