import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

async function getActiveEnvironmentPath(): Promise<string | undefined> {
	const extension = vscode.extensions.getExtension('ms-python.python');
	if (!extension) {
		vscode.window.showErrorMessage('Python extension is not installed.');
		return;
	}
	if (!extension.isActive) {
		await extension.activate();
	}
	const pythonApi = extension.exports;
	if (pythonApi?.environments?.getActiveEnvironmentPath) {
		const envPath = pythonApi.environments.getActiveEnvironmentPath();
		return envPath?.path;
	}
	if (pythonApi?.settings?.getExecutionDetails) {
		return pythonApi.settings.getExecutionDetails().execCommand?.[0];
	}
}

async function getAvlExecutable(): Promise<string> {
	const pythonPath = await getActiveEnvironmentPath();
	if (pythonPath) {
		const pythonDir = path.dirname(pythonPath);
		const isWin = process.platform === 'win32';
		const avlName = isWin ? 'avl.exe' : 'avl';
		const candidatePaths = [
			path.join(pythonDir, avlName),
			path.join(pythonDir, 'Scripts', avlName),
			path.join(pythonDir, 'bin', avlName)
		];
		for (const p of candidatePaths) {
			if (fs.existsSync(p)) return p;
		}
	}
	return 'avl';
}

let avalaTerminal: vscode.Terminal | undefined;

export function activate(context: vscode.ExtensionContext) {
	console.log('Avala extension active');

	const codeLensProvider = vscode.languages.registerCodeLensProvider(
		{ language: 'python' },
		new ExploitCodeLensProvider()
	);

	const runExploitCommand = vscode.commands.registerCommand(
		'avala.runExploit',
		async (alias: string) => {
			const avlPath = await getAvlExecutable();
			const folder = vscode.workspace.workspaceFolders?.[0];
			const cwd = folder ? folder.uri.fsPath : undefined;

			if (!avalaTerminal) {
				avalaTerminal = vscode.window.createTerminal({
					name: 'Avala',
					cwd
				});
				avalaTerminal.show(true);
			} else {
				avalaTerminal.show(true);
			}

			avalaTerminal.sendText(`"${avlPath}" run "${alias}"`);
		}
	);

	context.subscriptions.push(codeLensProvider, runExploitCommand);
}

class ExploitCodeLensProvider implements vscode.CodeLensProvider {
	provideCodeLenses(
		document: vscode.TextDocument
	): vscode.CodeLens[] {
		const text = document.getText();
		const codeLenses: vscode.CodeLens[] = [];

		const aliasRegex = /alias\s*=\s*['"](.+?)['"]/;
		const aliasWithDecoratorRegex = /@exploit\((?:[\s\S]*?)alias\s*=\s*['"](.+?)['"](?:[\s\S]*?)\)/g;
		const noAliasDecoratorRegex = /@exploit\(([\s\S]*?)\)/g;

		let match;
		const processedDecoratorRanges: vscode.Range[] = [];

		while ((match = aliasWithDecoratorRegex.exec(text)) !== null) {
			const alias = match[1];
			const startPos = document.positionAt(match.index);
			const funcLine = findFunctionLineAfter(document, startPos.line);
			const range = new vscode.Range(funcLine ?? startPos.line, 0, funcLine ?? startPos.line, 0);

			codeLenses.push(
				new vscode.CodeLens(range, {
					title: `🚀 Run exploit ${alias}`,
					command: 'avala.runExploit',
					arguments: [alias],
					tooltip: `Runs the exploit with alias: ${alias}`
				})
			);
			processedDecoratorRanges.push(range);
		}

		while ((match = noAliasDecoratorRegex.exec(text)) !== null) {
			const decoratorArgs = match[1];
			if (!aliasRegex.test(decoratorArgs)) {
				const decoratorLine = document.positionAt(match.index).line;
				const funcLine = findFunctionLineAfter(document, decoratorLine);
				let alias = '';

				if (funcLine !== undefined) {
					const fileName = document.fileName.split('/').pop()?.replace('.py', '') || 'unknown';
					const functionName = document.lineAt(funcLine).text.match(/^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)/)?.[1];
					if (functionName) {
						alias = `${fileName}.${functionName}`;
					}
				}

				if (alias) {
					const range = new vscode.Range(funcLine ?? decoratorLine, 0, funcLine ?? decoratorLine, 0);
					if (!processedDecoratorRanges.some(r => r.isEqual(range))) {
						codeLenses.push(
							new vscode.CodeLens(range, {
								title: `🚀 Run exploit ${alias}`,
								command: 'avala.runExploit',
								arguments: [alias],
								tooltip: `Runs the exploit with alias: ${alias}`
							})
						);
					}
				}
			}
		}
		return codeLenses;
	}
}

function findFunctionLineAfter(doc: vscode.TextDocument, startLine: number): number | undefined {
	for (let i = startLine + 1; i < doc.lineCount; i++) {
		const line = doc.lineAt(i);
		if (/^\s*def\s+/.test(line.text)) {
			return i;
		}
	}
}

export function deactivate() { }
