"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PreviewPanel = void 0;
const vscode = require("vscode");
class PreviewPanel {
    static currentPanel;
    _panel;
    _extensionUri;
    static createOrShow(extensionUri) {
        const column = vscode.ViewColumn.Two;
        if (PreviewPanel.currentPanel) {
            PreviewPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel('docsforgePreview', 'DocsForge Preview', column, {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')]
        });
        PreviewPanel.currentPanel = new PreviewPanel(panel, extensionUri);
    }
    constructor(panel, extensionUri) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        const updateInterval = setInterval(() => {
            this._update();
        }, 2000);
        this._panel.onDidDispose(() => {
            clearInterval(updateInterval);
            PreviewPanel.currentPanel = undefined;
        });
        this._update();
    }
    _update() {
        const devAddr = vscode.workspace.getConfiguration('docsforge').get('devAddr', 'localhost:8000');
        const url = `http://${devAddr}`;
        this._panel.webview.html = `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body { margin: 0; padding: 0; height: 100vh; }
          iframe { width: 100%; height: 100%; border: none; }
          .error { padding: 20px; color: #c00; font-family: sans-serif; }
        </style>
      </head>
      <body>
        <iframe src="${url}" sandbox="allow-scripts allow-same-origin"></iframe>
      </body>
      </html>
    `;
    }
}
exports.PreviewPanel = PreviewPanel;
//# sourceMappingURL=previewPanel.js.map