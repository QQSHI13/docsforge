/**
 * Pure (vscode-free) helpers extracted from ServerManager so they can be
 * unit-tested without launching VS Code.
 */
import * as fs from 'fs';
import * as path from 'path';

export const CONFIG_FILES = ['docsforge.yml', 'docsforge.yaml'];

/** Find the docsforge config file in the workspace root. */
export function findConfig(workspaceRoot: string): string | null {
  for (const name of CONFIG_FILES) {
    if (fs.existsSync(path.join(workspaceRoot, name))) {
      return name;
    }
  }
  return null;
}

/** Check whether a config file exists (for activation). */
export function hasConfig(workspaceRoot: string): boolean {
  return findConfig(workspaceRoot) !== null;
}

/** Extract a docsforge server URL from a stdout/stderr line.
 *  Matches: "Serving on http://host:port/path" */
export function extractServerUrl(text: string): string | null {
  const match = text.match(/Serving on\s+(https?:\/\/[^\s]+)/i);
  return match ? match[1] : null;
}

/** Strip ANSI escape sequences (colors) from CLI output for display. */
export function stripAnsi(text: string): string {
  return text.replace(/\u001b\[[0-9;?]*[ -/]*[@-~]/g, '');
}

/** Absolute path of the Python interpreter inside a project venv, if any. */
export function venvPythonPath(workspaceRoot: string): string | null {
  const dir = process.platform === 'win32' ? 'Scripts' : 'bin';
  const exe = process.platform === 'win32' ? 'python.exe' : 'python';
  return path.join(workspaceRoot, '.venv', dir, exe);
}

/** Parse `docsforge.__version__` output: accept `12.4.0` or `12.4.0+dev.1`. */
export function parseDocsforgeVersion(raw: string): string | null {
  const match = raw.trim().match(/^\d+\.\d+\.\d+/);
  return match ? match[0] : null;
}
