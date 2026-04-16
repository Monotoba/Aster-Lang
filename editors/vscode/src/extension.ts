/**
 * Aster Language VS Code Extension
 *
 * Activates the Aster language server via the `aster lsp --stdio` command and
 * wires it up through vscode-languageclient.  The server provides:
 *   - Diagnostics (parse errors + semantic errors shown as squiggles)
 *
 * Future server capabilities (hover, go-to-definition, completion, formatting)
 * will be picked up automatically once the server advertises them.
 */

import * as path from "path";
import * as vscode from "vscode";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
  TransportKind,
  RevealOutputChannelOn,
} from "vscode-languageclient/node";

let client: LanguageClient | undefined;

export function activate(context: vscode.ExtensionContext): void {
  const config = vscode.workspace.getConfiguration("aster");
  const serverExecutable: string = config.get("serverPath") ?? "aster";

  // ------------------------------------------------------------------
  // Server options: spawn `aster lsp --stdio`
  // ------------------------------------------------------------------
  const serverOptions: ServerOptions = {
    command: serverExecutable,
    args: ["lsp", "--stdio"],
    transport: TransportKind.stdio,
    options: {
      // Inherit PATH so virtual-env / pipx installs are found.
      env: process.env,
    },
  };

  // ------------------------------------------------------------------
  // Client options
  // ------------------------------------------------------------------
  const clientOptions: LanguageClientOptions = {
    // Only activate for .aster files.
    documentSelector: [{ scheme: "file", language: "aster" }],
    synchronize: {
      // Re-analyse when .aster files change on disk (not just in the editor).
      fileEvents: vscode.workspace.createFileSystemWatcher("**/*.aster"),
    },
    revealOutputChannelOn: RevealOutputChannelOn.Error,
    outputChannelName: "Aster Language Server",
    traceOutputChannel: vscode.window.createOutputChannel(
      "Aster Language Server Trace"
    ),
  };

  client = new LanguageClient(
    "aster",
    "Aster Language Server",
    serverOptions,
    clientOptions
  );

  // Start the client; this also starts the server subprocess.
  client.start();

  // Register a manual restart command so users can recover from crashes.
  context.subscriptions.push(
    vscode.commands.registerCommand("aster.restartServer", async () => {
      if (client) {
        await client.stop();
        client.start();
        vscode.window.showInformationMessage("Aster language server restarted.");
      }
    })
  );

  context.subscriptions.push(client);
}

export async function deactivate(): Promise<void> {
  if (client) {
    await client.stop();
  }
}
