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
