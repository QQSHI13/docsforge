"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const assert = __importStar(require("assert"));
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const pure_1 = require("../src/pure");
describe('pure helpers', () => {
    describe('findConfig / hasConfig', () => {
        let tmp;
        beforeEach(() => {
            tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-vscode-'));
        });
        afterEach(() => {
            fs.rmSync(tmp, { recursive: true, force: true });
        });
        it('prefers docsforge.yml over docsforge.yaml', () => {
            fs.writeFileSync(path.join(tmp, 'docsforge.yaml'), 'site_name: Y\n');
            fs.writeFileSync(path.join(tmp, 'docsforge.yml'), 'site_name: Y\n');
            assert.strictEqual((0, pure_1.findConfig)(tmp), 'docsforge.yml');
        });
        it('falls back to docsforge.yaml', () => {
            fs.writeFileSync(path.join(tmp, 'docsforge.yaml'), 'site_name: Y\n');
            assert.strictEqual((0, pure_1.findConfig)(tmp), 'docsforge.yaml');
        });
        it('returns null when no config present', () => {
            assert.strictEqual((0, pure_1.findConfig)(tmp), null);
            assert.strictEqual((0, pure_1.hasConfig)(tmp), false);
        });
        it('hasConfig is true when a config exists', () => {
            fs.writeFileSync(path.join(tmp, 'docsforge.yml'), 'site_name: Y\n');
            assert.strictEqual((0, pure_1.hasConfig)(tmp), true);
        });
        it('CONFIG_FILES lists both names', () => {
            assert.deepStrictEqual(pure_1.CONFIG_FILES, ['docsforge.yml', 'docsforge.yaml']);
        });
    });
    describe('extractServerUrl', () => {
        it('extracts the URL from a serve line', () => {
            assert.strictEqual((0, pure_1.extractServerUrl)('INFO - Serving on http://127.0.0.1:8000/'), 'http://127.0.0.1:8000/');
        });
        it('extracts a subpath URL', () => {
            assert.strictEqual((0, pure_1.extractServerUrl)('Serving on http://0.0.0.0:9000/docs/'), 'http://0.0.0.0:9000/docs/');
        });
        it('is case-insensitive', () => {
            assert.strictEqual((0, pure_1.extractServerUrl)('serving on http://localhost:8000/'), 'http://localhost:8000/');
        });
        it('returns null for non-serve lines', () => {
            assert.strictEqual((0, pure_1.extractServerUrl)('Building documentation...'), null);
            assert.strictEqual((0, pure_1.extractServerUrl)(''), null);
        });
        it('does not match bare http without the marker', () => {
            assert.strictEqual((0, pure_1.extractServerUrl)('see http://example.com for info'), null);
        });
    });
});
//# sourceMappingURL=pure.test.js.map