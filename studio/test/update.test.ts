import * as assert from 'assert';
import {
  compareVersions,
  isPrereleaseVersion,
  normalizeVersion,
  parseDocsforgeVersion,
  parseVersion,
  pickLatestVersion,
} from '../src/pure';

describe('update version helpers', () => {
  it('normalizes VSIX prerelease style', () => {
    assert.strictEqual(normalizeVersion('13.0.0-beta.1'), '13.0.0b1');
    assert.strictEqual(normalizeVersion('13.0.0-rc.2'), '13.0.0rc2');
    assert.strictEqual(normalizeVersion('13.0.0-alpha.1'), '13.0.0a1');
    assert.strictEqual(normalizeVersion('12.5.7'), '12.5.7');
  });

  it('parses stable and prerelease versions', () => {
    assert.deepStrictEqual(parseVersion('12.5.7'), {
      major: 12, minor: 5, patch: 7, preKind: null, preNum: 0,
    });
    assert.strictEqual(parseVersion('13.0.0b1')?.preKind, 'b');
    assert.strictEqual(parseVersion('13.0.0-beta.1')?.preNum, 1);
    assert.strictEqual(parseVersion('not-a-version'), null);
  });

  it('orders stable above prereleases of the same tuple', () => {
    assert.strictEqual(compareVersions('13.0.0', '13.0.0b1'), 1);
    assert.strictEqual(compareVersions('13.0.0b1', '13.0.0'), -1);
    assert.strictEqual(compareVersions('13.0.0b1', '13.0.0b2'), -1);
    assert.strictEqual(compareVersions('13.0.0b1', '13.0.0rc1'), -1);
    assert.strictEqual(compareVersions('13.0.0a1', '13.0.0b1'), -1);
    assert.strictEqual(compareVersions('13.0.0-beta.1', '13.0.0b1'), 0);
    assert.strictEqual(compareVersions('12.5.7', '13.0.0b1'), -1);
    assert.strictEqual(compareVersions('12.5.7', '12.5.7'), 0);
  });

  it('detects prereleases', () => {
    assert.strictEqual(isPrereleaseVersion('13.0.0b1'), true);
    assert.strictEqual(isPrereleaseVersion('13.0.0-beta.1'), true);
    assert.strictEqual(isPrereleaseVersion('12.5.7'), false);
    assert.strictEqual(isPrereleaseVersion('garbage'), false);
  });

  it('picks latest, skipping prereleases unless asked', () => {
    const versions = ['12.5.7', '13.0.0b1', '12.5.6', 'garbage'];
    assert.strictEqual(pickLatestVersion(versions, false), '12.5.7');
    assert.strictEqual(pickLatestVersion(versions, true), '13.0.0b1');
    assert.strictEqual(pickLatestVersion([], false), null);
    assert.strictEqual(pickLatestVersion(['13.0.0b1'], false), null);
  });

  it('offers an engine update for a beta checkout behind stable', () => {
    // Regression: parseDocsforgeVersion used to truncate 13.0.0b3 to
    // 13.0.0, so an editable beta looked current and no engine update
    // was ever offered (only the extension update appeared).
    const installed = parseDocsforgeVersion('13.0.0b3\n');
    assert.strictEqual(installed, '13.0.0b3');
    assert.strictEqual(compareVersions(installed!, '13.0.0'), -1);
  });
});
