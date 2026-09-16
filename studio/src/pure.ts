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

/** Parse `docsforge.__version__` output: accept `12.4.0`, `13.0.0b3`,
 *  `13.0.0-beta.3` (local `+...` suffix stripped). */
export function parseDocsforgeVersion(raw: string): string | null {
  const match = raw.trim().match(
    /^\d+\.\d+\.\d+(?:[-_.]?(?:alpha|beta|rc|a|b)[-_.]?\d*)?/i,
  );
  return match ? match[0] : null;
}

/** Whether a `direct_url.json` payload marks an editable (dev-checkout) install. */
export function isEditableDirectUrl(raw: string): boolean {
  return raw.replace(/\s+/g, '').includes('"editable":true');
}

/** Whether a spawned process still needs SIGKILL escalation.
 *  `ChildProcess.killed` only means a signal was delivered, so it must not
 *  gate escalation — check real exit state instead. */
export function shouldEscalateToSigkill(
  proc: { exitCode: number | null; signalCode: NodeJS.Signals | null },
): boolean {
  return proc.exitCode === null && proc.signalCode == null;
}

/** Pre-release precedence: stable > rc > beta/b > alpha/a. */
const PRE_ORDER: Record<string, number> = { a: 0, alpha: 0, b: 1, beta: 1, rc: 2 };

/** Normalize a version for comparison: `13.0.0-beta.1` -> `13.0.0b1`. */
export function normalizeVersion(raw: string): string {
  return raw.trim().replace(/[-_.]?(alpha|beta|rc|a|b)[-_.]?(\d*)$/i, (_, pre: string, num: string) => {
    const short = pre.toLowerCase().startsWith('alpha') ? 'a' : pre.toLowerCase().startsWith('beta') ? 'b' : pre.toLowerCase();
    return `${short}${num || '0'}`;
  });
}

interface ParsedVersion {
  major: number;
  minor: number;
  patch: number;
  preKind: string | null;
  preNum: number;
}

/** Parse `12.5.7`, `13.0.0b1`, `13.0.0-beta.1` (local `+...` suffix ignored). */
export function parseVersion(raw: string): ParsedVersion | null {
  // Strip local metadata BEFORE normalizing: the prerelease regex is
  // end-anchored, so `13.0.0-beta.3+build` would otherwise miss normalization
  // and fail the strict match below as "unparseable".
  const cleaned = normalizeVersion(raw.split('+', 1)[0]);
  const match = cleaned.match(/^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d*))?$/i);
  if (!match) {
    return null;
  }
  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    patch: Number(match[3]),
    preKind: match[4] ? match[4].toLowerCase() : null,
    preNum: match[5] ? Number(match[5]) : 0,
  };
}

/** Compare versions: -1 if a < b, 0 if equal, 1 if a > b. Unparseable loses. */
export function compareVersions(a: string, b: string): -1 | 0 | 1 {
  const pa = parseVersion(a);
  const pb = parseVersion(b);
  if (!pa && !pb) {
    return 0;
  }
  if (!pa) {
    return -1;
  }
  if (!pb) {
    return 1;
  }
  for (const key of ['major', 'minor', 'patch'] as const) {
    if (pa[key] !== pb[key]) {
      return pa[key] < pb[key] ? -1 : 1;
    }
  }
  if (pa.preKind === pb.preKind) {
    if (pa.preNum === pb.preNum) {
      return 0;
    }
    return pa.preNum < pb.preNum ? -1 : 1;
  }
  if (pa.preKind === null) {
    return 1;
  }
  if (pb.preKind === null) {
    return -1;
  }
  const orderA = PRE_ORDER[pa.preKind] ?? -1;
  const orderB = PRE_ORDER[pb.preKind] ?? -1;
  return orderA < orderB ? -1 : 1;
}

/** Whether a version string is a pre-release (alpha/beta/rc). */
export function isPrereleaseVersion(raw: string): boolean {
  return parseVersion(raw)?.preKind !== null && parseVersion(raw) !== null;
}

/** Pick the newest version from a list, skipping pre-releases unless asked. */
export function pickLatestVersion(versions: string[], includePre: boolean): string | null {
  let best: string | null = null;
  for (const v of versions) {
    if (!parseVersion(v)) {
      continue;
    }
    if (!includePre && isPrereleaseVersion(v)) {
      continue;
    }
    if (best === null || compareVersions(v, best) > 0) {
      best = v;
    }
  }
  return best;
}
