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
import { detectEnvironment, upgradeDocsforge, pickInstall, EnvironmentState } from './environment';
import { buildDismissedKey } from './pure';
import { openInBrowser } from './browser';
import { currentProjectRoot } from './roots';
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

/** Last successfully fetched versions, so update checks degrade gracefully
 *  offline (sidebar badge + manual check reuse them, clearly labeled).
 *  Timestamps are per channel: a mixed round (one fetch failed) must not
 *  re-stamp the stale channel as just fetched. */
interface CachedUpdates {
  engineLatest: string | null;
  engineFetchedAt: number;
  ext: GithubLatest | null;
  extFetchedAt: number;
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

function cachedDate(fetchedAt: number | null): string {
  if (!fetchedAt) {
    return 'unknown time';
  }
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

/** First workspace root containing a config, else the active file's folder.
 *  Delegates to the shared multi-root resolution so update checks probe the
 *  same interpreter serve would run. */
function resolveRoot(): string | undefined {
  return currentProjectRoot();
}

function releaseNotesUrl(version: string): string {
  return `${RELEASE_TAG_URL}v${version}`;
}

/** Release page for an extension update. Uses the release tag, not the VSIX
 *  version: prereleases ship as `13.0.1-beta.1` but are tagged `v13.0.1b1`,
 *  so `.../tag/v13.0.1-beta.1` would 404. */
function extensionNotesUrl(update: ExtensionUpdate): string {
  return `${RELEASE_TAG_URL}${update.tag}`;
}

/** Open release notes in the editor browser (external fallback inside). */
async function openReleaseNotes(url: string): Promise<void> {
  await openInBrowser(url);
}

/** Which install an update applies to: asks when several have docsforge,
 *  then verifies the picked install is actually behind `latest` (the check
 *  may have probed a different interpreter than the user picks). */
async function resolveUpdateState(
  root: string, latest: string,
): Promise<EnvironmentState | null> {
  const pick = await pickInstall(root);
  if (pick.kind === 'cancelled') {
    return null;
  }
  if (pick.kind === 'none') {
    vscode.window.showWarningMessage('DocsForge: no Python environment found to update.');
    return null;
  }
  if (pick.state.docsforgeVersion
    && compareVersions(pick.state.docsforgeVersion, latest) >= 0) {
    vscode.window.showInformationMessage(
      `DocsForge engine ${pick.state.docsforgeVersion} is already up to date.`,
    );
    return null;
  }
  return pick.state;
}

/** Display-only notes for cached (offline) versions: pip/VSIX need network. */
function cachedEngineInfo(update: EngineUpdate): void {
  vscode.window.showInformationMessage(
    `DocsForge engine ${update.current} → ${update.latest} (cached versions, offline). ` +
      'Reconnect and re-check to update.',
  );
}

function cachedExtensionInfo(update: ExtensionUpdate): void {
  vscode.window.showInformationMessage(
    `DocsForge Studio ${update.current} → ${update.latest} (cached versions, offline). ` +
      'Reconnect and re-check to update.',
  );
}

/** Run the engine upgrade: one safety question for editable installs
 *  (pip would replace the source checkout), otherwise straight to pip.
 *  Callers confirm first (quick-pick choice or single-update dialog). */
async function executeEngineUpdate(
  root: string, state: EnvironmentState, update: EngineUpdate,
): Promise<void> {
  if (state.editable) {
    const where = state.location ? ` at ${state.location}` : '';
    const action = await vscode.window.showWarningMessage(
      `DocsForge engine ${state.docsforgeVersion} is an editable install${where}. `
      + `Updating to ${update.latest} via pip would replace your source checkout. `
      + 'To track source instead, pull the repo and reinstall (`pip install -e .`).',
      'Replace with PyPI version',
    );
    if (action !== 'Replace with PyPI version') {
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

/** Single-update entry: one confirmation dialog (release notes re-shows the
 *  same dialog via loop, not recursion). The multi-update quick-pick calls
 *  `executeEngineUpdate` directly — the pick itself is the confirmation. */
async function offerEngineUpdate(
  root: string, update: EngineUpdate, stale = false,
): Promise<void> {
  if (stale) {
    cachedEngineInfo(update);
    return;
  }
  const state = await resolveUpdateState(root, update.latest);
  if (!state) {
    return;
  }
  for (;;) {
    const action = await vscode.window.showInformationMessage(
      `DocsForge engine ${state.docsforgeVersion ?? update.current} → ${update.latest} is available.`,
      'Update', 'Release notes',
    );
    if (action === 'Release notes') {
      await openReleaseNotes(releaseNotesUrl(update.latest));
      continue;
    }
    if (action !== 'Update') {
      return;
    }
    break;
  }
  await executeEngineUpdate(root, state, update);
}

/** Download a VSIX and hand it to VS Code's installer, then offer reload.
 *  Callers confirm first (quick-pick choice or single-update dialog). */
async function executeExtensionUpdate(update: ExtensionUpdate): Promise<void> {
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

/** Single-update entry: one confirmation dialog (release notes re-shows the
 *  same dialog via loop, not recursion). */
async function offerExtensionUpdate(update: ExtensionUpdate, stale = false): Promise<void> {
  if (stale) {
    cachedExtensionInfo(update);
    return;
  }
  for (;;) {
    const action = await vscode.window.showInformationMessage(
      `DocsForge Studio ${update.current} → ${update.latest} is available.`,
      'Download & install', 'Release notes',
    );
    if (action === 'Release notes') {
      await openReleaseNotes(extensionNotesUrl(update));
      continue;
    }
    if (action !== 'Download & install') {
      return;
    }
    break;
  }
  await executeExtensionUpdate(update);
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
  const engineFetchedAt = engineFresh ? now : cached?.engineFetchedAt ?? 0;
  const extFetchedAt = extFresh ? now : cached?.extFetchedAt ?? 0;
  if (fresh) {
    // Only overwrite the channels that actually fetched: backfilling the
    // other one with a new timestamp would present stale data as current.
    await writeUpdateCache(context, {
      engineLatest: engineFresh ? engineLatest : cached?.engineLatest ?? null,
      engineFetchedAt,
      ext: extFresh ? extLatest : cached?.ext ?? null,
      extFetchedAt,
    });
  }
  const effectiveEngine = engineLatest ?? cached?.engineLatest ?? null;
  const effectiveExt = extLatest ?? cached?.ext ?? null;
  const stale = !fresh && cached !== null;
  const offline = !fresh && cached === null;
  // An update computed from cache while its channel failed this round.
  const engineStale = !engineFresh;
  const extStale = !extFresh;
  // Editable installs track source, never PyPI: no engine update is ever
  // offered for them, and the installed version is excluded from the
  // up-to-date messaging below.
  const state = await detectEnvironment(root);
  const editableEngine = state.editable;
  let engine: EngineUpdate | null = null;
  if (!editableEngine && state.docsforgeVersion && effectiveEngine
    && compareVersions(state.docsforgeVersion, effectiveEngine) < 0) {
    engine = { kind: 'engine', current: state.docsforgeVersion, latest: effectiveEngine };
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
    // Offline messaging dates the older channel: the notice is only as
    // fresh as its stalest part.
    fetchedAt: Math.min(engineFetchedAt, extFetchedAt) || null,
    ownVersion: own, engineCurrent: editableEngine ? null : state.docsforgeVersion, includePre,
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
      `DocsForge: offline — showing versions cached at ${cachedDate(updates.fetchedAt)}.`,
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
    // Both stale: display-only, nothing actionable — never offer updates.
    if (updates.engineStale && updates.extStale) {
      cachedEngineInfo(engine);
      cachedExtensionInfo(extension);
      return;
    }
    // Step 1: everything up front — both versions plus notes, before any pick.
    const engineUrl = releaseNotesUrl(engine.latest);
    const extUrl = extensionNotesUrl(extension);
    const sameNotes = engineUrl === extUrl;
    const engineLine = `• Engine ${engine.current} → ${engine.latest}`
      + `${updates.engineStale ? ' (cached)' : ''}`;
    const extLine = `• Studio ${extension.current} → ${extension.latest}`
      + `${updates.extStale ? ' (cached)' : ''}`;
    const notesButtons = sameNotes ? ['Release notes'] : ['Engine notes', 'Extension notes'];
    for (;;) {
      const action = await vscode.window.showInformationMessage(
        `DocsForge updates available:\n${engineLine}\n${extLine}`,
        'Update…', ...notesButtons,
      );
      if (action === 'Engine notes' || action === 'Release notes') {
        await openReleaseNotes(engineUrl);
        continue;
      }
      if (action === 'Extension notes') {
        await openReleaseNotes(extUrl);
        continue;
      }
      if (action !== 'Update…') {
        return;
      }
      break;
    }
    // Step 2: pick. Stale items are not offered (their info was shown above).
    const freshEngine = !updates.engineStale;
    const freshExt = !updates.extStale;
    let doEngine = freshEngine;
    let doExt = freshExt;
    if (freshEngine && freshExt) {
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
      doEngine = choice.value === 'all' || choice.value === 'engine';
      doExt = choice.value === 'all' || choice.value === 'extension';
    }
    if (doEngine) {
      const state = await resolveUpdateState(root, engine.latest);
      if (state) {
        await executeEngineUpdate(root, state, engine);
      }
    }
    if (doExt) {
      await executeExtensionUpdate(extension);
    }
    return;
  }
  if (engine) {
    await offerEngineUpdate(root, engine, updates.engineStale);
    return;
  }
  if (extension) {
    await offerExtensionUpdate(extension, updates.extStale);
  }
}

/** Explain "up to date": flag prerelease tracking and unknown versions. */
async function reportUpToDate(
  context: vscode.ExtensionContext | undefined,
  updates: {
    ownVersion: string | null;
    engineCurrent: string | null;
    includePre: boolean;
    stale: boolean;
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
  vscode.window.showInformationMessage(
    updates.stale
      ? 'DocsForge is up to date (cached versions, offline).'
      : 'DocsForge is up to date.',
  );
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
  const channelStale = { engine: updates.engineStale, ext: updates.extStale };
  const summary = summarize(updates.engine, updates.extension, channelStale);
  hooks?.onUpdateKnown(summary);
  // Notify only for freshly confirmed updates. Anything computed from cache
  // (all-stale rounds, or mixed rounds) may predate the latest release, so
  // it refreshes the sidebar badge above and stays silent here.
  const freshUpdate = (updates.engine && !updates.engineStale)
    || (updates.extension && !updates.extStale);
  if (!freshUpdate || !summary) {
    return;
  }
  // The dismissed key carries per-channel freshness, matching the summary's
  // granularity: dismissing a mixed cached/fresh notice must not suppress
  // the later fully-fresh notice for the same versions (or vice versa).
  const seen = buildDismissedKey(
    updates.engine ? { latest: updates.engine.latest, stale: updates.engineStale } : null,
    updates.extension ? { latest: updates.extension.latest, stale: updates.extStale } : null,
  );
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
