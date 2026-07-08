import * as vscode from 'vscode';
import { spawn } from 'child_process';
import { findConfig } from './pure';

const THEME_COLORS = [
  'teal',
  'indigo',
  'blue',
  'green',
  'purple',
  'red',
  'orange',
  'pink',
];

const LANGUAGES = [
  { label: 'English', value: 'en' },
  { label: '中文', value: 'zh' },
  { label: 'Español', value: 'es' },
  { label: 'Français', value: 'fr' },
  { label: 'Deutsch', value: 'de' },
  { label: 'Other', value: 'other' },
];

export class InitWizard {
  /** Run the interactive project initialization wizard, matching the CLI
   *  `docsforge init` flow. Accepts a ServerManager so the user can
   *  immediately start the server after creation. */
  static async run(_serverManager?: unknown) {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
      vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
      return;
    }

    const workspaceRoot = workspaceFolder.uri.fsPath;

    const existingConfig = findConfig(workspaceRoot);
    if (existingConfig) {
      vscode.window.showInformationMessage(`DocsForge: ${existingConfig} already exists.`);
      return;
    }

    // --- Step 1: Site name ---
    const siteName = await vscode.window.showInputBox({
      prompt: 'Site name',
      placeHolder: 'My Documentation',
      validateInput: (value) => (value?.trim() ? null : 'Site name is required'),
    });
    if (!siteName) { return; }

    // --- Step 2: Site description ---
    const siteDescription = await vscode.window.showInputBox({
      prompt: 'Site description (optional)',
      placeHolder: 'A short description of the project',
    });

    // --- Step 3: Author / Organization ---
    const authorName = await vscode.window.showInputBox({
      prompt: 'Author / Organization (optional)',
      placeHolder: 'Jane Doe',
    });

    // --- Step 4: Copyright ---
    const currentYear = new Date().getFullYear().toString();
    const copyright = await vscode.window.showInputBox({
      prompt: 'Copyright notice (optional)',
      placeHolder: `Copyright ${currentYear} ${authorName || 'Jane Doe'}`,
    });

    // --- Step 5: Theme color ---
    const themeColor = await vscode.window.showQuickPick(THEME_COLORS, {
      placeHolder: 'Select a theme color',
    });
    if (!themeColor) { return; }

    // --- Step 6: Language ---
    const languagePick = await vscode.window.showQuickPick(LANGUAGES, {
      placeHolder: 'Select a language',
    });
    let language = languagePick?.value ?? 'en';
    if (language === 'other') {
      language = (await vscode.window.showInputBox({
        prompt: 'Language code',
        placeHolder: 'en',
      })) || 'en';
    }

    // --- Step 7: GitHub repository ---
    const repoUrl = await vscode.window.showInputBox({
      prompt: 'GitHub repository URL (optional)',
      placeHolder: 'https://github.com/user/repo',
    });

    // --- Step 8: Site URL ---
    const siteUrl = await vscode.window.showInputBox({
      prompt: 'Public site URL (optional)',
      placeHolder: 'https://example.github.io/project',
    });

    // --- Step 9: Branding assets ---
    const favicon = await vscode.window.showInputBox({
      prompt: 'Path to favicon, relative to docs/ (optional)',
      placeHolder: 'assets/favicon.png',
    });

    const logo = await vscode.window.showInputBox({
      prompt: 'Path to logo, relative to docs/ (optional)',
      placeHolder: 'assets/logo.png',
    });

    // --- Step 10: Privacy mode ---
    const privacyPick = await vscode.window.showQuickPick(
      [
        { label: 'Yes', value: true, description: 'Fetch and inline external assets locally' },
        { label: 'No', value: false, description: 'Use external assets directly' },
      ],
      { placeHolder: 'Enable privacy mode?' }
    );
    if (privacyPick === undefined) { return; }

    // --- Run init via Python CLI ---
    const pythonPath = vscode.workspace.getConfiguration('docsforge').get('pythonPath', 'python');

    const initArgs = JSON.stringify({
      project_directory: workspaceRoot,
      site_name: siteName.trim(),
      site_url: siteUrl?.trim() || null,
      theme_color: themeColor,
      privacy: privacyPick.value,
      author_name: authorName?.trim() || null,
      repo_url: repoUrl?.trim() || null,
      site_description: siteDescription?.trim() || null,
      language,
      copyright: copyright?.trim() || null,
      favicon: favicon?.trim() || null,
      logo: logo?.trim() || null,
    });

    // Use the CLI's `ProjectManager.init()` code path for consistent behavior.
    // We call `docsforge.init.init(**args)` directly — same backend the CLI uses.
    const pythonScript = [
      'import sys, json',
      "from docsforge import init",
      'args = json.loads(sys.argv[1])',
      'init.init(**args)',
    ].join('\n');

    const outputChannel = vscode.window.createOutputChannel('DocsForge Init');
    outputChannel.show();
    outputChannel.appendLine('Creating DocsForge project...');
    outputChannel.appendLine(`$ ${pythonPath} -c "<init script>"`);
    outputChannel.appendLine('');

    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'Creating DocsForge project...',
          cancellable: false,
        },
        () => new Promise<void>((resolve, reject) => {
          const proc = spawn(pythonPath, ['-c', pythonScript, initArgs], {
            cwd: workspaceRoot,
          });

          proc.stdout?.on('data', (data: Buffer) => {
            outputChannel.append(data.toString());
          });

          let stderr = '';
          proc.stderr?.on('data', (data: Buffer) => {
            stderr += data.toString();
            outputChannel.append(data.toString());
          });

          proc.on('error', (err: Error) => {
            const msg = `Failed to run python: ${err.message}. Check "docsforge.pythonPath" in settings.`;
            outputChannel.appendLine(msg);
            reject(new Error(msg));
          });

          proc.on('close', (code: number | null) => {
            if (code === 0) {
              outputChannel.appendLine('Project created successfully.');
              resolve();
            } else {
              const msg = stderr.trim() || `docsforge init exited with code ${code}`;
              outputChannel.appendLine(`Init failed: ${msg}`);
              reject(new Error(msg));
            }
          });
        })
      );

    const choice = await vscode.window.showInformationMessage(
      'DocsForge project created!',
      'Start Server'
    );
    if (choice === 'Start Server') {
      vscode.commands.executeCommand('docsforge.serve');
    }
  }
}
