import * as assert from 'assert';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

import { CONFIG_FILES, findConfig, hasConfig, extractServerUrl } from '../src/pure';

describe('pure helpers', () => {
  describe('findConfig / hasConfig', () => {
    let tmp: string;
    beforeEach(() => {
      tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-vscode-'));
    });
    afterEach(() => {
      fs.rmSync(tmp, { recursive: true, force: true });
    });

    it('prefers docsforge.yml over docsforge.yaml', () => {
      fs.writeFileSync(path.join(tmp, 'docsforge.yaml'), 'site_name: Y\n');
      fs.writeFileSync(path.join(tmp, 'docsforge.yml'), 'site_name: Y\n');
      assert.strictEqual(findConfig(tmp), 'docsforge.yml');
    });

    it('falls back to docsforge.yaml', () => {
      fs.writeFileSync(path.join(tmp, 'docsforge.yaml'), 'site_name: Y\n');
      assert.strictEqual(findConfig(tmp), 'docsforge.yaml');
    });

    it('returns null when no config present', () => {
      assert.strictEqual(findConfig(tmp), null);
      assert.strictEqual(hasConfig(tmp), false);
    });

    it('hasConfig is true when a config exists', () => {
      fs.writeFileSync(path.join(tmp, 'docsforge.yml'), 'site_name: Y\n');
      assert.strictEqual(hasConfig(tmp), true);
    });

    it('CONFIG_FILES lists both names', () => {
      assert.deepStrictEqual(CONFIG_FILES, ['docsforge.yml', 'docsforge.yaml']);
    });
  });

  describe('extractServerUrl', () => {
    it('extracts the URL from a serve line', () => {
      assert.strictEqual(
        extractServerUrl('INFO - Serving on http://127.0.0.1:8000/'),
        'http://127.0.0.1:8000/'
      );
    });

    it('extracts a subpath URL', () => {
      assert.strictEqual(
        extractServerUrl('Serving on http://0.0.0.0:9000/docs/'),
        'http://0.0.0.0:9000/docs/'
      );
    });

    it('is case-insensitive', () => {
      assert.strictEqual(
        extractServerUrl('serving on http://localhost:8000/'),
        'http://localhost:8000/'
      );
    });

    it('returns null for non-serve lines', () => {
      assert.strictEqual(extractServerUrl('Building documentation...'), null);
      assert.strictEqual(extractServerUrl(''), null);
    });

    it('does not match bare http without the marker', () => {
      assert.strictEqual(extractServerUrl('see http://example.com for info'), null);
    });
  });
});
