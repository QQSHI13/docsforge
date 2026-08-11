/**
 * Python environment management for the DocsForge extension.
 *
 * Responsibilities:
 *  - resolve a Python interpreter (settings override, remembered venv, PATH)
 *  - check pip availability
 *  - check whether docsforge is importable and at which version
 *  - if docsforge is missing, offer to install it into a project venv,
 *    for the current user (pip --user), or globally (pip)
 *  - remember the chosen interpreter so serve/build reuse it
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import { spawn } from 'child_process';
import { venvPythonPath, parseDocsforgeVersion } from './pure';

/** Result of a probe/install attempt. */
export interface EnvironmentState {
  /** Absolute path or bare name of the interpreter to run docsforge with. */
  python: string;
  /** Detected docsforge version (e.g. "12.4.0"), or null if not installed. */
  docsforgeVersion: string | null;
  /** Where docsforge is installed. */
  installKind: 'system' | 'venv' | 'user' | 'missing';
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

/** Probe the environment for python + docsforge. */
export async function detectEnvironment(
  workspaceRoot: string,
): Promise<EnvironmentState> {
  const python = await resolvePython(workspaceRoot);
  if (!python) {
    return { python: 'python', docsforgeVersion: null, installKind: 'missing' };
  }
  const version = await checkDocsforge(python);
  if (!version) {
    return { python, docsforgeVersion: null, installKind: 'missing' };
  }
  const inVenv = python.includes('.venv');
  return {
    python,
    docsforgeVersion: version,
    installKind: inVenv ? 'venv' : 'system',
  };
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

  const choice = await vscode.window.showQuickPick(
    [
      {
        label: 'Project virtual environment',
        description: 'Create .venv in the workspace and install docsforge there (recommended)',
        value: 'venv' as const,
      },
      {
        label: 'User installation',
        description: 'pip install --user docsforge',
        value: 'user' as const,
      },
      {
        label: 'Global installation',
        description: 'pip install docsforge (may need administrator rights)',
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

  const pipArgs = choice.value === 'user' ? ['--user', '--upgrade', 'docsforge'] : ['--upgrade', 'docsforge'];
  const installed = await pipInstall(
    state.python, workspaceRoot, pipArgs,
    `Installing DocsForge (${choice.value})…`, onLine,
  );
  if (!installed) {
    return null;
  }
  return state.python;
}
