/**
 * Self-update for DocsForge Studio: engine (pip) + extension (VSIX).
 *
 * - `docsforge.checkForUpdates` runs an on-demand check with progress UI.
 * - `autoCheckUpdates` runs once per startup (delayed, silent unless an
 *   update is found) when `docsforge.autoCheckUpdates` is enabled.
 * - `docsforge.includePrereleases` opts beta/alpha releases into the check.
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { hasConfig, compareVersions, pickLatestVersion } from './pure';
import { detectEnvironment, upgradeDocsforge } from './environment';
import { DocsForgeLogPanel } from './logPanel';

const PYPI_URL = 'https://pypi.org/pypi/docsforge/json';
const RELEASES_URL = 'https://api.github.com/repos/QQSHI13/docsforge/releases?per_page=20';
const RELEASE_TAG_URL = 'https://github.com/QQSHI13/docsforge/releases/tag/';
const FETCH_TIMEOUT_MS = 15000;
const VSIX_TIMEOUT_MS = 180000;
const AUTO_CHECK_DELAY_MS = 45000;

interface PypiResponse {
  info?: { version?: string };
  releases?: Record<string, unknown[]>;
}

interface GithubRelease {
  draft?: boolean;
  prerelease?: boolean;
  tag_name?: string;
  assets?: { name?: string; browser_download_url?: string }[];
}

export interface EngineUpdate {
  kind: 'engine';
  current: string;
  latest: string;
}

export interface ExtensionUpdate {
  kind: 'extension';
  current: string;
  latest: string;
  tag: string;
  vsixUrl: string;
}

/** GET JSON with a user agent and a hard timeout. Throws on failure. */
async function fetchJson<T>(url: string, timeoutMs: number): Promise<T> {
  const res = await fetch(url, {
    headers: {
      'User-Agent': 'docsforge-studio',
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${url}`);
  }
  return (await res.json()) as T;
}

/** Latest engine version on PyPI (stable, or newest pre-release if opted in). */
export async function getEngineLatest(includePre: boolean): Promise<string | null> {
  const data = await fetchJson<PypiResponse>(PYPI_URL, FETCH_TIMEOUT_MS);
  const candidates = Object.entries(data.releases ?? {})
    .filter(([, files]) => Array.isArray(files) && files.length > 0)
    .map(([version]) => version);
  if (!candidates.length && data.info?.version) {
    candidates.push(data.info.version);
  }
  return pickLatestVersion(candidates, includePre);
}

export interface GithubLatest {
  version: string;
  tag: string;
  vsixUrl: string;
}

/** Latest extension release on GitHub with an attached VSIX. */
export async function getExtensionLatest(includePre: boolean): Promise<GithubLatest | null> {
  const releases = await fetchJson<GithubRelease[]>(RELEASES_URL, FETCH_TIMEOUT_MS);
  for (const rel of releases) {
    if (rel.draft) {
      continue;
    }
    if (rel.prerelease && !includePre) {
      continue;
    }
    const tag = rel.tag_name ?? '';
    const version = tag.replace(/^v/i, '');
    const vsixUrl = rel.assets?.find(
      (a) => a.name?.endsWith('.vsix') && a.browser_download_url,
    )?.browser_download_url;
    if (version && vsixUrl) {
      return { version, tag, vsixUrl };
    }
  }
  return null;
}

/** This extension's own version, found by package name (id varies by host). */
export function getOwnVersion(): string | null {
  const ext = vscode.extensions.all.find(
    (e) => e.packageJSON?.name === 'docsforge-studio',
  );
  return ext?.packageJSON?.version ?? null;
}

/** First workspace root containing a config, else the active file's folder. */
function resolveRoot(): string | undefined {
  const folders = vscode.workspace.workspaceFolders ?? [];
  const configured = folders.find((f) => hasConfig(f.uri.fsPath));
  if (configured) {
    return configured.uri.fsPath;
  }
  const active = vscode.window.activeTextEditor?.document.uri.fsPath;
  if (active) {
    const folder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(active));
    if (folder) {
      return folder.uri.fsPath;
    }
  }
  return folders[0]?.uri.fsPath;
}

function releaseNotesUrl(version: string): string {
  return `${RELEASE_TAG_URL}v${version}`;
}

/** Offer the engine upgrade. */
async function offerEngineUpdate(
  root: string, update: EngineUpdate,
): Promise<void> {
  const action = await vscode.window.showInformationMessage(
    `DocsForge engine ${update.current} → ${update.latest} is available.`,
    'Update', 'Release notes', 'Later',
  );
  if (action === 'Release notes') {
    await vscode.commands.executeCommand(
      'vscode.open', vscode.Uri.parse(releaseNotesUrl(update.latest)),
    );
    return offerEngineUpdate(root, update);
  }
  if (action !== 'Update') {
    return;
  }
  const state = await detectEnvironment(root);
  if (!state.docsforgeVersion) {
    vscode.window.showWarningMessage('DocsForge: no Python environment found to update.');
    return;
  }
  const log = DocsForgeLogPanel.get();
  const ok = await upgradeDocsforge(
    state.python, root, state.installKind, update.latest,
    (line) => log.append(line),
  );
  if (!ok) {
    return;
  }
  const after = await detectEnvironment(root);
  vscode.window.showInformationMessage(
    `DocsForge engine updated to ${after.docsforgeVersion ?? update.latest}.`,
  );
}

/** Download a VSIX and hand it to VS Code's installer, then offer reload. */
async function offerExtensionUpdate(update: ExtensionUpdate): Promise<void> {
  const action = await vscode.window.showInformationMessage(
    `DocsForge Studio ${update.current} → ${update.latest} is available.`,
    'Download & install', 'Release notes', 'Later',
  );
  if (action === 'Release notes') {
    await vscode.commands.executeCommand(
      'vscode.open', vscode.Uri.parse(releaseNotesUrl(update.latest)),
    );
    return offerExtensionUpdate(update);
  }
  if (action !== 'Download & install') {
    return;
  }
  const dest = path.join(
    fs.mkdtempSync(path.join(os.tmpdir(), 'docsforge-vsix-')),
    `docsforge-vscode-${update.latest}.vsix`,
  );
  let downloaded = false;
  try {
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: `Downloading DocsForge Studio ${update.latest}…`,
        cancellable: false,
      },
      async () => {
        const res = await fetch(update.vsixUrl, {
          headers: { 'User-Agent': 'docsforge-studio' },
          signal: AbortSignal.timeout(VSIX_TIMEOUT_MS),
        });
        if (!res.ok) {
          throw new Error(`HTTP ${res.status} downloading the VSIX`);
        }
        fs.writeFileSync(dest, Buffer.from(await res.arrayBuffer()));
      },
    );
    downloaded = true;
  } catch (err) {
    vscode.window.showErrorMessage(`DocsForge extension download failed: ${(err as Error).message}`);
  }
  if (!downloaded) {
    return;
  }
  try {
    await vscode.commands.executeCommand(
      'workbench.extensions.installExtension', vscode.Uri.file(dest),
    );
  } catch (err) {
    vscode.window.showErrorMessage(
      `DocsForge extension install failed: ${(err as Error).message}`,
    );
    return;
  }
  const reload = await vscode.window.showInformationMessage(
    `DocsForge Studio ${update.latest} installed. Reload to apply it.`,
    'Reload now', 'Later',
  );
  if (reload === 'Reload now') {
    await vscode.commands.executeCommand('workbench.action.reloadWindow');
  }
}

/** Check both update channels; network failures resolve to null (offline-safe). */
async function collectUpdates(root: string): Promise<{
  engine: EngineUpdate | null;
  extension: ExtensionUpdate | null;
  offline: boolean;
}> {
  const cfg = vscode.workspace.getConfiguration('docsforge');
  const includePre = cfg.get<boolean>('includePrereleases', false);
  const [engineLatest, extLatest] = await Promise.all([
    getEngineLatest(includePre).catch(() => null),
    getExtensionLatest(includePre).catch(() => null),
  ]);
  const offline = engineLatest === null && extLatest === null;
  let engine: EngineUpdate | null = null;
  const state = await detectEnvironment(root);
  if (state.docsforgeVersion && engineLatest
    && compareVersions(state.docsforgeVersion, engineLatest) < 0) {
    engine = { kind: 'engine', current: state.docsforgeVersion, latest: engineLatest };
  }
  let extension: ExtensionUpdate | null = null;
  const own = getOwnVersion();
  if (own && extLatest && compareVersions(own, extLatest.version) < 0) {
    extension = {
      kind: 'extension', current: own, latest: extLatest.version,
      tag: extLatest.tag, vsixUrl: extLatest.vsixUrl,
    };
  }
  return { engine, extension, offline };
}

/** Manual command: check for engine + extension updates with progress UI. */
export async function checkForUpdates(): Promise<void> {
  const root = resolveRoot();
  if (!root || !hasConfig(root)) {
    vscode.window.showInformationMessage(
      'DocsForge: open a DocsForge project first, then check for updates.',
    );
    return;
  }
  const updates = await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: 'Checking for DocsForge updates…',
      cancellable: false,
    },
    () => collectUpdates(root),
  );
  if (updates.offline) {
    vscode.window.showWarningMessage(
      'DocsForge: could not reach the update server. Check your connection and try again.',
    );
    return;
  }
  const { engine, extension } = updates;
  if (!engine && !extension) {
    vscode.window.showInformationMessage('DocsForge is up to date.');
    return;
  }
  if (engine && extension) {
    const choice = await vscode.window.showQuickPick(
      [
        { label: 'Update all', description: `engine + extension`, value: 'all' as const },
        { label: `Update engine only`, description: `${engine.current} → ${engine.latest}`, value: 'engine' as const },
        { label: `Update extension only`, description: `${extension.current} → ${extension.latest}`, value: 'extension' as const },
      ],
      { placeHolder: 'DocsForge engine and extension updates are available.' },
    );
    if (!choice) {
      return;
    }
    if (choice.value === 'all' || choice.value === 'engine') {
      await offerEngineUpdate(root, engine);
    }
    if (choice.value === 'all' || choice.value === 'extension') {
      await offerExtensionUpdate(extension);
    }
    return;
  }
  if (engine) {
    await offerEngineUpdate(root, engine);
    return;
  }
  if (extension) {
    await offerExtensionUpdate(extension);
  }
}

/** Silent startup check: notifies only when an update is found (once per version). */
export async function autoCheckUpdates(
  context: vscode.ExtensionContext,
): Promise<void> {
  const cfg = vscode.workspace.getConfiguration('docsforge');
  if (!cfg.get<boolean>('autoCheckUpdates', true)) {
    return;
  }
  const root = resolveRoot();
  if (!root || !hasConfig(root)) {
    return;
  }
  await new Promise((resolve) => setTimeout(resolve, AUTO_CHECK_DELAY_MS));
  let updates;
  try {
    updates = await collectUpdates(root);
  } catch {
    return;
  }
  if (updates.offline || (!updates.engine && !updates.extension)) {
    return;
  }
  const seen = [
    updates.engine ? `engine:${updates.engine.latest}` : '',
    updates.extension ? `extension:${updates.extension.latest}` : '',
  ].filter(Boolean).join(',');
  if (context.globalState.get<string>('docsforge.update.dismissed', '') === seen) {
    return;
  }
  const parts = [
    updates.engine ? `engine ${updates.engine.current} → ${updates.engine.latest}` : '',
    updates.extension ? `extension ${updates.extension.current} → ${updates.extension.latest}` : '',
  ].filter(Boolean).join(', ');
  const action = await vscode.window.showInformationMessage(
    `DocsForge update available (${parts}).`,
    'Update now', 'Later', "Don't ask again",
  );
  if (action === 'Update now') {
    await checkForUpdates();
  } else if (action === "Don't ask again") {
    await context.globalState.update('docsforge.update.dismissed', seen);
  }
}

/** Register the update command (always available; guards live in handlers). */
export function registerUpdateCommands(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('docsforge.checkForUpdates', () => checkForUpdates()),
  );
  void autoCheckUpdates(context);
}
