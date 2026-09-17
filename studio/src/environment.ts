/**
 * Python environment management for the DocsForge extension.
 *
 * Responsibilities:
 *  - resolve a Python interpreter (settings override, remembered venv, PATH)
 *  - discover every interpreter and let the user pick when several have
 *    docsforge installed (single installs resolve silently)
 *  - check pip availability
 *  - check whether docsforge is importable and at which version
 *  - if docsforge is missing, offer to install it into a project venv,
 *    for the current user (pip --user), or globally (pip), adding
 *    --break-system-packages on PEP 668 externally-managed interpreters
 *  - remember the chosen interpreter so serve/build reuse it
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { spawn } from 'child_process';
import { venvPythonPath, parseDocsforgeVersion, isEditableDirectUrl, pipFlagPrefix } from './pure';

/** Result of a probe/install attempt. */
export interface EnvironmentState {
  /** Absolute path or bare name of the interpreter to run docsforge with. */
  python: string;
  /** Detected docsforge version (e.g. "12.4.0"), or null if not installed. */
  docsforgeVersion: string | null;
  /** Where docsforge is installed. */
  installKind: 'system' | 'venv' | 'user' | 'editable' | 'missing';
  /** True when docsforge is an editable (source-checkout) install. */
  editable: boolean;
  /** `docsforge.__file__` for the probed interpreter, if importable. */
  location: string | null;
}

/** Well-known interpreters, best first. */
const CANDIDATES = ['python3', 'python', 'py'];

/** Whether a command runs successfully (exit code 0). */
function runOk(command: string, args: string[]): Promise<boolean> {
  return new Promise((resolve) => {
    const proc = spawn(command, args, { stdio: 'ignore' });
    proc.on('error', () => resolve(false));
    proc.on('close', (code) => resolve(code === 0));
  });
}

/** Capture stdout of a short command; resolves to '' on failure. */
function runCapture(command: string, args: string[]): Promise<string> {
  return new Promise((resolve) => {
    let out = '';
    const proc = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    proc.stdout.on('data', (d: Buffer) => { out += d.toString(); });
    proc.on('error', () => resolve(''));
    proc.on('close', (code) => resolve(code === 0 ? out : ''));
  });
}

/** Check `python -m pip --version` succeeds. */
export function hasPip(python: string): Promise<boolean> {
  return runOk(python, ['-m', 'pip', '--version']);
}

/** Check `python -c "import docsforge"` and report its version. */
export async function checkDocsforge(python: string): Promise<string | null> {
  const out = await runCapture(python, [
    '-c', 'import docsforge; print(docsforge.__version__)',
  ]);
  return parseDocsforgeVersion(out);
}

/** Absolute path of the imported docsforge package, or null when missing. */
export async function docsforgeLocation(python: string): Promise<string | null> {
  const out = await runCapture(python, [
    '-c', 'import docsforge; print(docsforge.__file__)',
  ]);
  const trimmed = out.trim();
  return trimmed ? trimmed : null;
}

/** Whether docsforge resolves to an editable (source-checkout) install. */
export async function checkDocsforgeEditable(python: string): Promise<boolean> {
  const out = await runCapture(python, [
    '-c',
    "import importlib.metadata as m; "
    + "print(m.distribution('docsforge').read_text('direct_url.json') or '')",
  ]);
  return isEditableDirectUrl(out);
}

/** Whether the interpreter is PEP 668 externally-managed (Debian/Ubuntu
 *  system Pythons refuse `pip install` without `--break-system-packages`;
 *  venvs never carry the marker). Cached per interpreter path. */
const externallyManagedCache = new Map<string, boolean>();

export async function isExternallyManaged(python: string): Promise<boolean> {
  const hit = externallyManagedCache.get(python);
  if (hit !== undefined) {
    return hit;
  }
  const out = await runCapture(python, [
    '-c',
    'import os, sysconfig; '
    + 'print(os.path.exists(os.path.join('
    + 'sysconfig.get_path("stdlib"), "EXTERNALLY-MANAGED")))',
  ]);
  const value = out.trim() === 'True';
  externallyManagedCache.set(python, value);
  return value;
}

/** Interpreter's user site-packages dir, or null when undiscoverable. */
async function userSitePath(python: string): Promise<string | null> {
  const out = await runCapture(python, [
    '-c', 'import site; print(site.getusersitepackages())',
  ]);
  const trimmed = out.trim();
  return trimmed ? trimmed : null;
}

/** Icons dir of the installed docsforge package, for `:icon:` completions.
 *  Resolves through the workspace interpreter (a repo-relative
 *  `<root>/docsforge/templates/.icons` path only exists inside a docsforge
 *  checkout, never in a user project). Null when undiscoverable. */
export async function installedIconsDir(workspaceRoot: string): Promise<string | null> {
  const python = await resolvePython(workspaceRoot);
  if (!python) {
    return null;
  }
  const out = await runCapture(python, [
    '-c',
    'import docsforge, os; '
    + 'print(os.path.join(os.path.dirname(docsforge.__file__), "templates", ".icons"))',
  ]);
  const dir = out.trim();
  if (!dir || !fs.existsSync(path.join(dir, 'material'))) {
    return null;
  }
  return dir;
}

/** Resolve the interpreter to use for this workspace.
 *
 * Priority:
 *  1. `docsforge.pythonPath` setting, when explicitly set
 *  2. a `.venv` we created earlier (remembered in workspace state), if present
 *  3. a `.venv` already present in the workspace root
 *  4. python3 / python / py on PATH
 */
export async function resolvePython(workspaceRoot: string): Promise<string | null> {
  const configured = vscode.workspace
    .getConfiguration('docsforge')
    .get<string>('pythonPath', 'python')
    .trim();
  if (configured && configured !== 'python') {
    return (await runOk(configured, ['--version'])) ? configured : null;
  }

  const remembered = vscode.workspace.getConfiguration('docsforge')
    .get<string>('rememberedPython', '');
  if (remembered && fs.existsSync(remembered)) {
    return remembered;
  }

  const venv = venvPythonPath(workspaceRoot);
  if (venv && fs.existsSync(venv)) {
    return venv;
  }

  for (const cand of CANDIDATES) {
    if (await runOk(cand, ['--version'])) {
      return cand;
    }
  }
  return null;
}

/** Probe one interpreter for python + docsforge. */
export async function probePython(python: string): Promise<EnvironmentState> {
  const version = await checkDocsforge(python);
  if (!version) {
    return { python, docsforgeVersion: null, installKind: 'missing', editable: false, location: null };
  }
  const [location, editable, userSite] = await Promise.all([
    docsforgeLocation(python),
    checkDocsforgeEditable(python),
    userSitePath(python),
  ]);
  if (editable) {
    return { python, docsforgeVersion: version, installKind: 'editable', editable: true, location };
  }
  if (userSite && location && location.startsWith(userSite)) {
    return { python, docsforgeVersion: version, installKind: 'user', editable: false, location };
  }
  const inVenv = python.includes('.venv') || (!!location && location.includes('.venv'));
  return {
    python,
    docsforgeVersion: version,
    installKind: inVenv ? 'venv' : 'system',
    editable: false,
    location,
  };
}

/** Every viable interpreter, best first: explicit setting, remembered venv,
 *  project .venv, then PATH candidates that respond to `--version`. */
async function candidatePythons(workspaceRoot: string): Promise<string[]> {
  const out: string[] = [];
  const push = (p: string | null) => {
    if (p && !out.includes(p)) {
      out.push(p);
    }
  };
  const configured = vscode.workspace
    .getConfiguration('docsforge')
    .get<string>('pythonPath', 'python')
    .trim();
  if (configured && configured !== 'python' && await runOk(configured, ['--version'])) {
    push(configured);
  }
  const remembered = vscode.workspace.getConfiguration('docsforge')
    .get<string>('rememberedPython', '');
  if (remembered && fs.existsSync(remembered)) {
    push(remembered);
  }
  const venv = venvPythonPath(workspaceRoot);
  if (venv && fs.existsSync(venv)) {
    push(venv);
  }
  for (const cand of CANDIDATES) {
    if (await runOk(cand, ['--version'])) {
      push(cand);
    }
  }
  return out;
}

/** Probe the environment for python + docsforge. */
export async function detectEnvironment(
  workspaceRoot: string,
): Promise<EnvironmentState> {
  const missing: EnvironmentState = {
    python: 'python', docsforgeVersion: null, installKind: 'missing',
    editable: false, location: null,
  };
  const python = await resolvePython(workspaceRoot);
  if (!python) {
    return missing;
  }
  return probePython(python);
}

/** One-line label for the install picker, e.g. `13.0.0 · venv · /w/.venv/bin/python`. */
function installLabel(state: EnvironmentState): string {
  const where = state.editable && state.location
    ? `editable · ${state.location}`
    : `${state.installKind} · ${state.location ?? state.python}`;
  return `${state.docsforgeVersion} · ${where}`;
}

export type InstallPick =
  | { kind: 'picked'; state: EnvironmentState }
  | { kind: 'none'; python: string | null }
  | { kind: 'cancelled' };

/** Remember an explicitly chosen interpreter so later resolves reuse it. */
async function rememberPython(python: string): Promise<void> {
  try {
    await vscode.workspace.getConfiguration('docsforge').update(
      'rememberedPython', python, vscode.ConfigurationTarget.Workspace,
    );
  } catch {
    /* settings write is best-effort */
  }
}

/** Choose which docsforge install to use. Probes every interpreter and,
 *  when several have docsforge, always asks — the remembered choice is
 *  pre-selected so confirming is one keypress. A single install resolves
 *  silently; none yields `none` with a usable interpreter for the install
 *  flow (or null when no Python exists at all). */
export async function pickInstall(workspaceRoot: string): Promise<InstallPick> {
  const pythons = await candidatePythons(workspaceRoot);
  if (!pythons.length) {
    return { kind: 'none', python: null };
  }
  const states = await Promise.all(pythons.map((p) => probePython(p)));
  const withEngine = states.filter((s) => s.docsforgeVersion);
  if (!withEngine.length) {
    return { kind: 'none', python: pythons[0] };
  }
  if (withEngine.length === 1) {
    return { kind: 'picked', state: withEngine[0] };
  }
  const remembered = vscode.workspace.getConfiguration('docsforge')
    .get<string>('rememberedPython', '');
  interface InstallItem extends vscode.QuickPickItem {
    state: EnvironmentState;
  }
  const items: InstallItem[] = withEngine.map((s) => ({
    label: `DocsForge ${installLabel(s)}`,
    description: s.python,
    state: s,
  }));
  // createQuickPick (not showQuickPick) so the remembered interpreter can
  // be pre-selected — confirming the default is a single Enter.
  const qp = vscode.window.createQuickPick<InstallItem>();
  qp.items = items;
  qp.activeItems = items.filter((i) => i.state.python === remembered);
  qp.placeholder = 'Several DocsForge installs found. Which one should be used?';
  const choice = await new Promise<InstallItem | undefined>((resolve) => {
    const done = (v: InstallItem | undefined) => {
      qp.dispose();
      resolve(v);
    };
    qp.onDidAccept(() => done(qp.selectedItems[0]));
    qp.onDidHide(() => done(undefined));
    qp.show();
  });
  if (!choice) {
    return { kind: 'cancelled' };
  }
  await rememberPython(choice.state.python);
  return { kind: 'picked', state: choice.state };
}

/** Run a command, streaming stdout/stderr to the DocsForge output panel. */
function runStreamed(
  python: string, args: string[], cwd: string, onLine: (line: string) => void,
): Promise<number | null> {
  return new Promise((resolve) => {
    const proc = spawn(python, args, { cwd, env: { ...process.env, FORCE_COLOR: '1' } });
    proc.stdout.on('data', (d: Buffer) => onLine(d.toString()));
    proc.stderr.on('data', (d: Buffer) => onLine(d.toString()));
    proc.on('error', (err) => onLine(`Failed to run: ${err.message}\n`));
    proc.on('close', (code) => resolve(code));
  });
}

/** Install docsforge with the given pip arguments inside a progress UI. */
async function pipInstall(
  python: string, workspaceRoot: string, pipArgs: string[],
  label: string, onLine: (line: string) => void,
): Promise<boolean> {
  return vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: label, cancellable: false },
    async () => {
      onLine(`$ ${python} -m pip install ${pipArgs.join(' ')}\n`);
      const code = await runStreamed(
        python, ['-m', 'pip', 'install', ...pipArgs], workspaceRoot, onLine,
      );
      if (code !== 0) {
        vscode.window.showErrorMessage(
          `DocsForge install failed (pip exited ${code}). See the DocsForge Output panel.`,
        );
        return false;
      }
      return true;
    },
  );
}

/** Upgrade an installed docsforge to an exact version via pip.
 *
 * Reuses the installer's progress UI and output panel. Returns true when
 * pip exited 0 (the caller should re-probe the version afterwards).
 * Never call this on an editable install without asking first: pip would
 * replace the source checkout with the PyPI build.
 */
export async function upgradeDocsforge(
  python: string, workspaceRoot: string,
  installKind: EnvironmentState['installKind'], version: string,
  onLine: (line: string) => void,
): Promise<boolean> {
  const target = `docsforge==${version}`;
  const flags = pipFlagPrefix(installKind, await isExternallyManaged(python));
  const pipArgs = [...flags, '--upgrade', target];
  const flagText = flags.length ? `${flags.join(' ')} ` : '';
  const manual = `${python} -m pip install ${flagText}--upgrade "${target}"`;
  const ok = await pipInstall(
    python, workspaceRoot, pipArgs,
    `Updating DocsForge to ${version}…`, onLine,
  );
  if (!ok) {
    onLine(
      `\nDocsForge engine update failed. To retry by hand, run:\n  ${manual}\n`,
    );
  }
  return ok;
}

/** Ensure docsforge is installed, offering venv / user / global installs.
 *
 * Returns the interpreter to use, or null if the user cancelled / install failed.
 */
export async function ensureDocsforge(
  workspaceRoot: string, state: EnvironmentState,
  onLine: (line: string) => void,
): Promise<string | null> {
  if (state.docsforgeVersion) {
    return state.python;
  }
  if (!(await hasPip(state.python))) {
    const action = await vscode.window.showErrorMessage(
      'DocsForge is not installed and pip is unavailable for the detected Python. ' +
        'Install pip first, or set "docsforge.pythonPath" to an interpreter that has it.',
      'Open Settings',
    );
    if (action === 'Open Settings') {
      await vscode.commands.executeCommand(
        'workbench.action.openSettings', 'docsforge.pythonPath',
      );
    }
    return null;
  }

  const managed = await isExternallyManaged(state.python);
  const userFlags = pipFlagPrefix('user', managed);
  const globalFlags = pipFlagPrefix('system', managed);
  const fmt = (flags: string[]) => flags.length ? `${flags.join(' ')} ` : '';
  const choice = await vscode.window.showQuickPick(
    [
      {
        label: 'Project virtual environment',
        description: 'Create .venv in the workspace and install docsforge there (recommended)',
        value: 'venv' as const,
      },
      {
        label: 'User installation',
        description: `pip install ${fmt(userFlags)}docsforge`,
        value: 'user' as const,
      },
      {
        label: 'Global installation',
        description: `pip install ${fmt(globalFlags)}docsforge`
          + (managed ? ' (externally-managed interpreter)' : ' (may need administrator rights)'),
        value: 'global' as const,
      },
    ],
    { placeHolder: 'DocsForge is not installed. Choose an installation method.' },
  );
  if (!choice) {
    return null;
  }

  const cfg = vscode.workspace.getConfiguration('docsforge');
  if (choice.value === 'venv') {
    const venv = venvPythonPath(workspaceRoot)!;
    const venvDir = venv.replace(/(Scripts|bin)[/\\]python(\.exe)?$/, '');
    const ok = await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: 'Creating virtual environment…', cancellable: false },
      async () => {
        onLine(`$ ${state.python} -m venv ${venvDir}\n`);
        const code = await runStreamed(state.python, ['-m', 'venv', venvDir], workspaceRoot, onLine);
        return code === 0;
      },
    );
    if (!ok) {
      vscode.window.showErrorMessage('Failed to create the virtual environment.');
      return null;
    }
    const venvPython = venvPythonPath(workspaceRoot)!;
    const installed = await pipInstall(
      venvPython, workspaceRoot, ['--upgrade', 'docsforge'],
      'Installing DocsForge into the virtual environment…', onLine,
    );
    if (!installed) {
      return null;
    }
    await cfg.update('rememberedPython', venvPython, vscode.ConfigurationTarget.Workspace);
    return venvPython;
  }

  const pipArgs = choice.value === 'user'
    ? [...userFlags, '--upgrade', 'docsforge']
    : [...globalFlags, '--upgrade', 'docsforge'];
  const installed = await pipInstall(
    state.python, workspaceRoot, pipArgs,
    `Installing DocsForge (${choice.value})…`, onLine,
  );
  if (!installed) {
    return null;
  }
  return state.python;
}
