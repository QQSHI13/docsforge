/**
 * DocsForge Output panel — a webview that shows build/serve logs inside the
 * editor area, instead of VS Code's bottom Output tab.
 *
 * Usage: get a singleton via `DocsForgeLogPanel.get()`, then `append`
 * or `appendLine`. The panel auto-reveals the first time output arrives; a
 * command ("docsforge.openLog") shows it on demand.
 */
import * as vscode from 'vscode';
import { stripAnsi } from './pure';

const VIEW_TYPE = 'docsforge.log';
const TITLE = 'DocsForge Output';

/** Max lines kept in the panel's scrollback buffer. */
const MAX_LINES = 5000;

export class DocsForgeLogPanel {
  private static singleton: DocsForgeLogPanel | undefined;

  private panel: vscode.WebviewPanel | undefined;
  private buffer: string[] = [];

  private constructor() {}

  /** Get (creating on demand) the singleton panel. */
  static get(): DocsForgeLogPanel {
    if (!DocsForgeLogPanel.singleton) {
      DocsForgeLogPanel.singleton = new DocsForgeLogPanel();
    }
    return DocsForgeLogPanel.singleton;
  }

  /** Reveal the panel (create it if needed). */
  show(): void {
    this.ensurePanel();
    this.panel?.reveal(vscode.ViewColumn.Beside, true);
  }

  /** Append raw text (may contain newlines and ANSI escapes). */
  append(text: string): void {
    this.pushLines(stripAnsi(text).split('\n'));
  }

  /** Append a single line (no trailing newline needed). */
  appendLine(line = ''): void {
    this.append(`${line}\n`);
  }

  clear(): void {
    this.buffer = [];
    this.panel?.webview.postMessage({ type: 'clear' });
  }

  private ensurePanel(): vscode.WebviewPanel {
    if (this.panel) {
      return this.panel;
    }
    const panel = vscode.window.createWebviewPanel(
      VIEW_TYPE,
      TITLE,
      { viewColumn: vscode.ViewColumn.Beside, preserveFocus: true },
      { enableScripts: true, retainContextWhenHidden: true },
    );
    panel.webview.html = this.html();
    panel.onDidDispose(() => {
      if (this.panel === panel) {
        this.panel = undefined;
      }
    });
    this.panel = panel;
    // Replay buffered output into the fresh webview.
    panel.webview.onDidReceiveMessage((msg) => {
      if (msg.type === 'ready') {
        panel.webview.postMessage({ type: 'replace', lines: this.buffer });
      }
    });
    return panel;
  }

  private pushLines(lines: string[]): void {
    const panel = this.ensurePanel();
    const nonEmpty = lines.length && lines[lines.length - 1] === '' ? lines.slice(0, -1) : lines;
    if (!nonEmpty.length) {
      return;
    }
    this.buffer.push(...nonEmpty);
    if (this.buffer.length > MAX_LINES) {
      this.buffer = this.buffer.slice(-MAX_LINES);
    }
    panel.webview.postMessage({ type: 'append', lines: nonEmpty });
  }

  private html(): string {
    const nonce = [...Array(32)]
      .map(() => Math.random().toString(36)[2])
      .join('');
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}'">
<style>
  body { margin: 0; font-family: var(--vscode-editor-font-family, monospace);
         font-size: var(--vscode-editor-font-size, 13px);
         background: var(--vscode-editor-background);
         color: var(--vscode-editor-foreground); }
  #log { padding: 8px 12px; white-space: pre-wrap; word-break: break-word; }
</style>
</head>
<body>
<pre id="log"></pre>
<script nonce="${nonce}">
  const log = document.getElementById('log');
  const vscode = acquireVsCodeApi();
  let first = true;
  function scrollToBottom() { window.scrollTo(0, document.body.scrollHeight); }
  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (msg.type === 'append') {
      log.textContent += msg.lines.join('\\n') + '\\n';
    } else if (msg.type === 'replace') {
      log.textContent = msg.lines.join('\\n');
    } else if (msg.type === 'clear') {
      log.textContent = '';
    }
    scrollToBottom();
    first = false;
  });
  window.addEventListener('load', () => {
    if (first) scrollToBottom();
    // Signal readiness so the extension can replay the buffer.
    vscode.postMessage({ type: 'ready' });
  });
</script>
</body>
</html>`;
  }
}
