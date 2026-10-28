/**
 * DocsForge Output view — a WebviewView living inside the DocsForge sidebar
 * panel (activity bar), instead of a separate editor tab or the bottom
 * Output tab. Streams build/serve/init logs.
 *
 * Usage: get the singleton via `DocsForgeLogPanel.get()`, then `append` or
 * `appendLine`. The view is revealed automatically when output arrives.
 */
import * as vscode from 'vscode';
import { stripAnsi } from './pure';

const VIEW_ID = 'docsforge.output';

/** Max lines kept in the view's scrollback buffer. */
const MAX_LINES = 5000;
/** The webview trims down to this many lines once it passes MAX_LINES, so
 *  removals happen per chunk rather than on every arriving line. */
const TRIM_TO_LINES = 4000;

export class DocsForgeLogPanel implements vscode.WebviewViewProvider {
  private static singleton: DocsForgeLogPanel | undefined;

  private view: vscode.WebviewView | undefined;
  private buffer: string[] = [];

  private constructor() {}

  /** Get (creating on demand) the singleton panel. */
  static get(): DocsForgeLogPanel {
    if (!DocsForgeLogPanel.singleton) {
      DocsForgeLogPanel.singleton = new DocsForgeLogPanel();
    }
    return DocsForgeLogPanel.singleton;
  }

  /** Reveal the output view in the sidebar. */
  show(): void {
    // Focus the view; if it doesn't exist yet (never opened), creating the
    // webview triggers resolveWebviewView, which replays the buffer.
    void vscode.commands.executeCommand(`${VIEW_ID}.focus`);
  }

  /** Append raw text (may contain newlines and ANSI escapes). */
  append(text: string): void {
    const lines = stripAnsi(text).split('\n');
    this.pushLines(lines);
  }

  /** Append a single line (no trailing newline needed). */
  appendLine(line = ''): void {
    this.append(`${line}\n`);
  }

  clear(): void {
    this.buffer = [];
    this.view?.webview.postMessage({ type: 'clear' });
  }

  /* ------------------------------------------------------------------ */
  /* WebviewViewProvider                                                */
  /* ------------------------------------------------------------------ */

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this.html();
    webviewView.webview.onDidReceiveMessage((msg) => {
      if (msg.type === 'ready') {
        webviewView.webview.postMessage({ type: 'replace', lines: this.buffer });
      }
    });
    // When hidden and reshown, the webview may be re-created — replay buffer.
    webviewView.onDidDispose(() => {
      if (this.view === webviewView) {
        this.view = undefined;
      }
    });
  }

  private pushLines(lines: string[]): void {
    // Drop the trailing empty element produced by a final newline.
    const content = lines.length && lines[lines.length - 1] === '' ? lines.slice(0, -1) : lines;
    if (!content.length) {
      return;
    }
    this.buffer.push(...content);
    if (this.buffer.length > MAX_LINES) {
      this.buffer = this.buffer.slice(-MAX_LINES);
    }
    this.view?.webview.postMessage({ type: 'append', lines: content });
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
  #log > div { white-space: pre-wrap; }
</style>
</head>
<body>
<pre id="log"></pre>
<script nonce="${nonce}">
  const MAX_LINES = ${MAX_LINES};
  // Trim well below the cap so removals happen in batches (per chunk node),
  // not once per arriving line.
  const TRIM_TO = ${TRIM_TO_LINES};
  const log = document.getElementById('log');
  const vscode = acquireVsCodeApi();
  let lineCount = 0;
  function scrollToBottom() { window.scrollTo(0, document.body.scrollHeight); }
  function addChunk(text, count) {
    const node = document.createElement('div');
    node.dataset.lines = String(count);
    node.textContent = text;
    log.appendChild(node);
    lineCount += count;
  }
  // The renderer must not grow forever: an all-day serve session would
  // otherwise accumulate every line ever printed. Drop the oldest chunk nodes
  // once the buffer passes the cap, keeping at least TRIM_TO lines.
  function trim() {
    while (lineCount > TRIM_TO && log.firstChild) {
      lineCount -= Number(log.firstChild.dataset.lines || 0);
      log.removeChild(log.firstChild);
    }
  }
  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (msg.type === 'append') {
      addChunk(msg.lines.join('\\n') + '\\n', msg.lines.length);
      if (lineCount > MAX_LINES) trim();
    } else if (msg.type === 'replace') {
      while (log.firstChild) log.removeChild(log.firstChild);
      lineCount = 0;
      if (msg.lines.length) addChunk(msg.lines.join('\\n') + '\\n', msg.lines.length);
    } else if (msg.type === 'clear') {
      while (log.firstChild) log.removeChild(log.firstChild);
      lineCount = 0;
    }
    scrollToBottom();
  });
  window.addEventListener('load', () => {
    scrollToBottom();
    // Signal readiness so the extension can replay the buffer.
    vscode.postMessage({ type: 'ready' });
  });
</script>
</body>
</html>`;
  }
}
