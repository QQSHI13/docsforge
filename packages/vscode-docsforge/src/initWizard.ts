import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { spawn } from 'child_process';

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
  static async run() {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
      vscode.window.showErrorMessage('DocsForge: open a workspace folder first.');
      return;
    }

    const workspaceRoot = workspaceFolder.uri.fsPath;

    if (fs.existsSync(path.join(workspaceRoot, 'docsforge.yml'))) {
      vscode.window.showInformationMessage('DocsForge: docsforge.yml already exists.');
      return;
    }

    const siteName = await vscode.window.showInputBox({
      prompt: 'Site name',
      placeHolder: 'My Documentation',
      validateInput: (value) => (value?.trim() ? null : 'Site name is required'),
    });
    if (!siteName) { return; }

    const siteDescription = await vscode.window.showInputBox({
      prompt: 'Site description (optional)',
      placeHolder: 'A short description of the project',
    });

    const siteUrl = await vscode.window.showInputBox({
      prompt: 'Public site URL (optional)',
      placeHolder: 'https://example.github.io/project',
    });

    const repoUrl = await vscode.window.showInputBox({
      prompt: 'Repository URL (optional)',
      placeHolder: 'https://github.com/user/repo',
    });

    const authorName = await vscode.window.showInputBox({
      prompt: 'Author name (optional)',
      placeHolder: 'Jane Doe',
    });

    const copyright = await vscode.window.showInputBox({
      prompt: 'Copyright text (optional)',
      placeHolder: 'Copyright 2026 Jane Doe',
    });

    const themeColor = await vscode.window.showQuickPick(THEME_COLORS, {
      placeHolder: 'Select a theme color',
    });
    if (!themeColor) { return; }

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

    const privacyPick = await vscode.window.showQuickPick(
      [
        { label: 'Yes', value: true, description: 'Fetch and inline external assets locally' },
        { label: 'No', value: false, description: 'Use external assets directly' },
      ],
      { placeHolder: 'Enable privacy mode?' }
    );
    if (privacyPick === undefined) { return; }

    const favicon = await vscode.window.showInputBox({
      prompt: 'Path to favicon (optional)',
      placeHolder: 'assets/favicon.png',
    });

    const logo = await vscode.window.showInputBox({
      prompt: 'Path to logo (optional)',
      placeHolder: 'assets/logo.png',
    });

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

    const pythonScript = `
import sys, json
from docsforge import init
args = json.loads(sys.argv[1])
init.init(**args)
`;

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

        let stderr = '';
        proc.stderr?.on('data', (data: Buffer) => { stderr += data.toString(); });

        proc.on('error', (err: Error) => {
          reject(new Error(`Failed to run DocsForge init: ${err.message}`));
        });

        proc.on('close', (code: number | null) => {
          if (code === 0) {
            resolve();
          } else {
            reject(new Error(stderr || `DocsForge init exited with code ${code}`));
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
