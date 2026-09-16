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
import { hasConfig, compareVersions, isPrereleaseVersion, pickLatestVersion } from './pure';
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
  /** True when the installed engine is an editable (source-checkout) install. */
  editable: boolean;
  /** `docsforge.__file__` for the installed engine, if known. */
  location: string | null;
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

/** Last successfully fetched versions, so update checks degrade gracefully
 *  offline (sidebar badge + manual check reuse them, clearly labeled). */
interface CachedUpdates {
  engineLatest: string | null;
  ext: GithubLatest | null;
  fetchedAt: number;
}

const UPDATE_CACHE_KEY = 'docsforge.update.lastSeen';

function readUpdateCache(
  context?: vscode.ExtensionContext,
): CachedUpdates | null {
  try {
    return context?.globalState.get<CachedUpdates>(UPDATE_CACHE_KEY) ?? null;
  } catch {
    return null;
  }
}

async function writeUpdateCache(
  context: vscode.ExtensionContext | undefined,
  cache: CachedUpdates,
): Promise<void> {
  if (!context) {
    return;
  }
  try {
    await context.globalState.update(UPDATE_CACHE_KEY, cache);
  } catch {
    /* cache is best-effort */
  }
}

function cachedDate(fetchedAt: number): string {
  try {
    return new Date(fetchedAt).toLocaleString();
  } catch {
    return 'unknown time';
  }
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

/** Offer the engine upgrade. Editable installs get a dedicated prompt:
 *  pip would replace the source checkout, so the user must opt in. */
async function offerEngineUpdate(
  root: string, update: EngineUpdate,
): Promise<void> {
  const state = await detectEnvironment(root);
  if (!state.docsforgeVersion) {
    vscode.window.showWarningMessage('DocsForge: no Python environment found to update.');
    return;
  }
  if (state.editable) {
    const where = state.location ? ` at ${state.location}` : '';
    const action = await vscode.window.showWarningMessage(
      `DocsForge engine ${state.docsforgeVersion} is an editable install${where}. `
      + `Updating to ${update.latest} via pip would replace your source checkout. `
      + 'To track source instead, pull the repo and reinstall (`pip install -e .`).',
      'Replace with PyPI version', 'Later',
    );
    if (action !== 'Replace with PyPI version') {
      return;
    }
  } else {
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

/** Check both update channels; network failures resolve to null (offline-safe).
 *  When `context` is given, successful fetches refresh the offline cache and
 *  total failures fall back to it (`stale: true`, clearly labeled). */
async function collectUpdates(
  root: string, context?: vscode.ExtensionContext,
): Promise<{
  engine: EngineUpdate | null;
  extension: ExtensionUpdate | null;
  offline: boolean;
  /** True when versions come from cache (no network at all). */
  stale: boolean;
  /** Per-channel staleness (mixed fresh/stale rounds). */
  engineStale: boolean;
  extStale: boolean;
  fetchedAt: number | null;
  /** Installed versions, for messaging when nothing newer is found. */
  ownVersion: string | null;
  engineCurrent: string | null;
  includePre: boolean;
}> {
  const cfg = vscode.workspace.getConfiguration('docsforge');
  const includePre = cfg.get<boolean>('includePrereleases', false);
  const [engineLatest, extLatest] = await Promise.all([
    getEngineLatest(includePre).catch(() => null),
    getExtensionLatest(includePre).catch(() => null),
  ]);
  const cached = readUpdateCache(context);
  const engineFresh = engineLatest !== null;
  const extFresh = extLatest !== null;
  const fresh = engineFresh || extFresh;
  const now = Date.now();
  if (fresh) {
    // Only overwrite the channels that actually fetched: backfilling the
    // other one with a new timestamp would present stale data as current.
    await writeUpdateCache(context, {
      engineLatest: engineFresh ? engineLatest : cached?.engineLatest ?? null,
      ext: extFresh ? extLatest : cached?.ext ?? null,
      fetchedAt: now,
    });
  }
  const effectiveEngine = engineLatest ?? cached?.engineLatest ?? null;
  const effectiveExt = extLatest ?? cached?.ext ?? null;
  const stale = !fresh && cached !== null;
  const offline = !fresh && cached === null;
  // An update computed from cache while its channel failed this round.
  const engineStale = !engineFresh;
  const extStale = !extFresh;
  let engine: EngineUpdate | null = null;
  const state = await detectEnvironment(root);
  if (state.docsforgeVersion && effectiveEngine
    && compareVersions(state.docsforgeVersion, effectiveEngine) < 0) {
    engine = {
      kind: 'engine', current: state.docsforgeVersion, latest: effectiveEngine,
      editable: state.editable, location: state.location,
    };
  }
  let extension: ExtensionUpdate | null = null;
  const own = getOwnVersion();
  if (own && effectiveExt && compareVersions(own, effectiveExt.version) < 0) {
    extension = {
      kind: 'extension', current: own, latest: effectiveExt.version,
      tag: effectiveExt.tag, vsixUrl: effectiveExt.vsixUrl,
    };
  }
  return {
    engine, extension, offline, stale, engineStale, extStale,
    fetchedAt: fresh ? now : cached?.fetchedAt ?? null,
    ownVersion: own, engineCurrent: state.docsforgeVersion, includePre,
  };
}

/** Hook for surfacing update state elsewhere (e.g. the sidebar badge). */
export interface UpdateHooks {
  onUpdateKnown(summary: string | null): void;
}

/** One-line summary of available updates, or null when up to date.
 *  `channelStale` marks updates computed from cache while that channel
 *  failed this round, so mixed fresh/stale results are labeled per part. */
function summarize(
  engine: EngineUpdate | null, extension: ExtensionUpdate | null,
  channelStale: { engine: boolean; ext: boolean } = { engine: false, ext: false },
): string | null {
  const parts = [
    engine
      ? `engine ${engine.current} → ${engine.latest}`
        + `${engine.editable ? ' (editable install)' : ''}`
        + `${channelStale.engine ? ' (cached)' : ''}`
      : '',
    extension
      ? `extension ${extension.current} → ${extension.latest}`
        + `${channelStale.ext ? ' (cached)' : ''}`
      : '',
  ].filter(Boolean);
  return parts.length ? parts.join(', ') : null;
}

/** Manual command: check for engine + extension updates with progress UI. */
export async function checkForUpdates(
  context?: vscode.ExtensionContext, hooks?: UpdateHooks,
): Promise<void> {
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
    () => collectUpdates(root, context),
  );
  if (updates.offline) {
    vscode.window.showWarningMessage(
      'DocsForge: could not reach the update server. Check your connection and try again.',
    );
    return;
  }
  if (updates.stale) {
    vscode.window.showWarningMessage(
      `DocsForge: offline — showing versions cached at ${cachedDate(updates.fetchedAt ?? 0)}.`,
    );
  }
  const { engine, extension } = updates;
  const channelStale = { engine: updates.engineStale, ext: updates.extStale };
  hooks?.onUpdateKnown(summarize(engine, extension, channelStale));
  if (!engine && !extension) {
    await reportUpToDate(context, updates, hooks);
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

/** Explain "up to date": flag prerelease tracking and unknown versions. */
async function reportUpToDate(
  context: vscode.ExtensionContext | undefined,
  updates: {
    ownVersion: string | null;
    engineCurrent: string | null;
    includePre: boolean;
  },
  hooks?: UpdateHooks,
): Promise<void> {
  if (updates.ownVersion === null) {
    vscode.window.showWarningMessage(
      'DocsForge: could not determine the installed extension version, '
      + 'so only the engine was checked (up to date).',
    );
    return;
  }
  const onPre = (updates.ownVersion && isPrereleaseVersion(updates.ownVersion))
    || (updates.engineCurrent && isPrereleaseVersion(updates.engineCurrent));
  if (onPre && !updates.includePre) {
    const action = await vscode.window.showInformationMessage(
      'DocsForge is up to date on stable releases, but you are running a '
      + 'pre-release. Turn on pre-release tracking to be offered betas.',
      'Check pre-releases', 'Later',
    );
    if (action === 'Check pre-releases') {
      await vscode.workspace.getConfiguration('docsforge').update(
        'includePrereleases', true, vscode.ConfigurationTarget.Global,
      );
      await checkForUpdates(context, hooks);
    }
    return;
  }
  vscode.window.showInformationMessage('DocsForge is up to date.');
}

/** Silent startup check: notifies only when an update is found (once per version). */
export async function autoCheckUpdates(
  context: vscode.ExtensionContext, hooks?: UpdateHooks,
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
    updates = await collectUpdates(root, context);
  } catch {
    return;
  }
  if (updates.offline || (!updates.engine && !updates.extension)) {
    return;
  }
  // Offline-but-cached: refresh the sidebar badge silently, never pop up —
  // the versions may predate the latest release.
  if (updates.stale) {
    hooks?.onUpdateKnown(summarize(
      updates.engine, updates.extension,
      { engine: true, ext: true },
    ));
    return;
  }
  const summary = summarize(
    updates.engine, updates.extension,
    { engine: updates.engineStale, ext: updates.extStale },
  );
  hooks?.onUpdateKnown(summary);
  const seen = [
    updates.engine ? `engine:${updates.engine.latest}` : '',
    updates.extension ? `extension:${updates.extension.latest}` : '',
  ].filter(Boolean).join(',');
  if (context.globalState.get<string>('docsforge.update.dismissed', '') === seen) {
    return;
  }
  const action = await vscode.window.showInformationMessage(
    `DocsForge update available (${summary}).`,
    'Update now', 'Later', "Don't ask again",
  );
  if (action === 'Update now') {
    await checkForUpdates(context, hooks);
  } else if (action === "Don't ask again") {
    await context.globalState.update('docsforge.update.dismissed', seen);
  }
}

/** Register the update command (always available; guards live in handlers). */
export function registerUpdateCommands(
  context: vscode.ExtensionContext, hooks?: UpdateHooks,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      'docsforge.checkForUpdates', () => checkForUpdates(context, hooks),
    ),
  );
  void autoCheckUpdates(context, hooks);
}
