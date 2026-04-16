# VS Code Integration Guide

This guide explains how to add support for the Aster language to VS Code and how the integration works under the hood.

---

## 1. How to Add Aster to VS Code

There are two primary ways to add Aster support: using the development mode (Extension Development Host) or by packaging and installing the extension.

### Prerequisites
- **VS Code** (v1.85+)
- **Node.js & npm**
- **Aster CLI** installed with LSP support:
  ```bash
  pip install -e ".[lsp]"
  ```

### Option A: Development Mode (Quickest)
This is the best way to test the extension without a permanent installation.

1. Open the `editors/vscode` folder in VS Code.
2. Run `npm install` and `npm run compile` in the terminal.
3. Press **F5** (or select **Run and Debug > Launch Extension**).
4. A new VS Code window named **[Extension Development Host]** will open.
5. In that new window, open any `.aster` file to see syntax highlighting and LSP features in action.

### Option B: Manual Installation (.vsix)
If you want the extension to be permanently available in your main VS Code instance:

1. Navigate to `editors/vscode`.
2. Install the VS Code Extension Manager: `npm install -g @vscode/vsce`.
3. Package the extension: `vsce package`. This will create a file like `aster-lang-0.1.0.vsix`.
4. In VS Code, open the Extensions view (`Ctrl+Shift+X`).
5. Click the `...` menu in the top-right corner of the Extensions panel and select **Install from VSIX...**.
6. Select the `.vsix` file you just created.

---

## 2. How it Works (Under the Hood)

The Aster VS Code integration is divided into two parts: a **Client** (the extension) and a **Server** (the Language Server).

### The Client-Server Architecture
Aster uses the **Language Server Protocol (LSP)**, a standardized JSON-RPC based protocol that allows a single language server to support multiple IDEs.

1.  **Activation:** When you open a `.aster` file, VS Code identifies the language and activates the Aster extension.
2.  **Server Startup:** The extension spawns the `aster lsp --stdio` command as a background process.
3.  **Synchronization:** As you type, the client sends `textDocument/didChange` notifications containing the updated source code to the server.
4.  **Analysis:** The server runs the Aster lexer, parser, and semantic analyzer on the new text. It produces an `AnalysisResult` which contains any errors or warnings found.
5.  **Diagnostics:** The server converts these errors into LSP `Diagnostic` objects and sends them back to the client via `textDocument/publishDiagnostics`. VS Code then renders these as red or yellow squiggly lines.

### Key Features Explained

#### Syntax Highlighting
Unlike diagnostics, highlighting is handled locally by the client using a **TextMate Grammar** (`syntaxes/aster.tmLanguage.json`). This ensures that code is colored instantly as you type, even before the server has finished analyzing it.

#### Hover and Go-To-Definition
When you hover over a symbol or request its definition:
1.  The client sends a request (e.g., `textDocument/hover`) with your cursor's line and column.
2.  The server uses its cached **Symbol Table** from the last analysis to find the identifier at that position.
3.  It retrieves the type and declaration location and sends the response back to the client.

#### Formatting
When you trigger "Format Document":
1.  The client sends a `textDocument/formatting` request.
2.  The server calls the `aster_lang.formatter` library.
3.  It returns a "TextEdit" that tells VS Code exactly which text to replace to make the file canonical.

---

## 3. Configuration and Troubleshooting

### Configuring the Aster Path
If `aster` is not in your system `PATH` (for example, if it's in a specific virtual environment), you can tell the extension where to find it in your VS Code settings:

```json
{
  "aster.serverPath": "/path/to/your/.venv/bin/aster"
}
```

### Inspecting Communication
You can see the raw JSON-RPC messages being exchanged by setting:
```json
{
  "aster.trace.server": "verbose"
}
```
The logs will appear in the VS Code **Output** panel under the **Aster Language Server Trace** channel.
