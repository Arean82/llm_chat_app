import * as vscode from 'vscode';

const API_URL = 'http://localhost:5000/v1/chat/completions';

export function activate(context: vscode.ExtensionContext) {
    console.log('LLM Chat App extension activated');

    // 1. Inline suggestions (triggered by typing)
    const inlineProvider: vscode.InlineCompletionItemProvider = {
        async provideInlineCompletionItems(document, position, context, token) {
            const line = document.lineAt(position.line).text;
            const lineText = line.substring(0, position.character);
            
            // Only suggest if line has content
            if (lineText.length < 3) return;
            
            const prompt = `Complete this code: ${lineText}`;
            const suggestion = await getInlineSuggestion(prompt);
            
            if (suggestion) {
                return [new vscode.InlineCompletionItem(suggestion)];
            }
            return;
        }
    };
    context.subscriptions.push(
        vscode.languages.registerInlineCompletionItemProvider('*', inlineProvider)
    );

    // 2. Code actions - Fix this code
    const fixCodeAction = vscode.commands.registerCommand('llmchat.fixCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        
        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        
        if (!selectedText) {
            vscode.window.showErrorMessage('No code selected');
            return;
        }
        
        await sendToAPI(selectedText, 'Fix this code', 'Fix any bugs or issues in this code and explain the fixes:');
    });
    
    // 2. Code actions - Explain this
    const explainCodeAction = vscode.commands.registerCommand('llmchat.explainCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        
        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        
        if (!selectedText) {
            vscode.window.showErrorMessage('No code selected');
            return;
        }
        
        await sendToAPI(selectedText, 'Explain this code', 'Explain this code in simple terms:');
    });
    
    // Register code action provider
    const codeActionProvider = vscode.languages.registerCodeActionsProvider('*', {
        provideCodeActions(document, range) {
            const actions = [];
            
            const fixAction = new vscode.CodeAction('Fix this code', vscode.CodeActionKind.QuickFix);
            fixAction.command = { command: 'llmchat.fixCode', title: 'Fix this code' };
            actions.push(fixAction);
            
            const explainAction = new vscode.CodeAction('Explain this code', vscode.CodeActionKind.QuickFix);
            explainAction.command = { command: 'llmchat.explainCode', title: 'Explain this code' };
            actions.push(explainAction);
            
            return actions;
        }
    });
    context.subscriptions.push(codeActionProvider);
    context.subscriptions.push(fixCodeAction, explainCodeAction);

    // 3. Terminal integration
    const terminalCommand = vscode.commands.registerCommand('llmchat.terminalCommand', async () => {
        const terminal = vscode.window.activeTerminal || vscode.window.createTerminal('LLM Chat');
        terminal.show();
        
        const userPrompt = await vscode.window.showInputBox({
            prompt: 'Describe what you want to do in terminal',
            placeHolder: 'e.g., "Install all dependencies for my Python project"'
        });
        
        if (userPrompt) {
            terminal.sendText(`echo "🤖 Generating command for: ${userPrompt}"`);
            await sendToAPI(userPrompt, 'Generate terminal command', 'Generate only the terminal command, no explanation:');
        }
    });

    // 4. Error explanation
    const explainError = vscode.commands.registerCommand('llmchat.explainError', async () => {
        const errorMessage = await vscode.window.showInputBox({
            prompt: 'Paste the error message',
            placeHolder: 'Error message from terminal or problem panel...'
        });
        
        if (errorMessage) {
            await sendToAPI(errorMessage, 'Explain this error', 'Explain this error and provide a fix:');
        }
    });
    
    // Register error hover provider
    const errorHoverProvider = vscode.languages.registerHoverProvider('*', {
        async provideHover(document, position) {
            const wordRange = document.getWordRangeAtPosition(position);
            const word = document.getText(wordRange);
            
            // Check if word is near an error (simplified)
            const diagnostics = vscode.languages.getDiagnostics(document.uri);
            const errorAtPosition = diagnostics.some(d => d.range.contains(position) && d.severity === vscode.DiagnosticSeverity.Error);
            
            if (errorAtPosition) {
                const errorText = diagnostics.find(d => d.range.contains(position))?.message || word;
                const suggestion = await getInlineSuggestion(`Explain this error: ${errorText}`);
                
                if (suggestion) {
                    return new vscode.Hover(`**LLM Chat:** ${suggestion}`);
                }
            }
            return;
        }
    });
    context.subscriptions.push(errorHoverProvider);

    // 5. Commit message generation
    const generateCommit = vscode.commands.registerCommand('llmchat.generateCommit', async () => {
        const gitExtension = vscode.extensions.getExtension('vscode.git');
        if (!gitExtension) {
            vscode.window.showErrorMessage('Git extension not found');
            return;
        }
        
        const git = gitExtension.exports.getAPI(1);
        const repo = git.repositories[0];
        
        if (!repo) {
            vscode.window.showErrorMessage('No git repository found');
            return;
        }
        
        const changes = repo.state.workingTreeChanges;
        if (changes.length === 0) {
            vscode.window.showErrorMessage('No changes to commit');
            return;
        }
        
        let changesText = '';
        for (const change of changes) {
            changesText += `- ${change.uri.path}\n`;
        }
        
        await sendToAPI(changesText, 'Generate commit message', 'Generate a concise git commit message for these changes:');
    });

    // 6. Documentation generator (add docstring)
    const generateDocstring = vscode.commands.registerCommand('llmchat.generateDocstring', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        
        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        const functionMatch = selectedText.match(/def\s+(\w+)\s*\([^)]*\)/);
        
        if (functionMatch) {
            await sendToAPI(selectedText, 'Generate docstring', 'Generate a Python docstring for this function:');
        } else {
            vscode.window.showErrorMessage('Select a function to generate docstring');
        }
    });

    // 7. Test generator
    const generateTests = vscode.commands.registerCommand('llmchat.generateTests', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        
        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        
        if (selectedText) {
            await sendToAPI(selectedText, 'Generate unit tests', 'Generate unit tests for this code using pytest:');
        } else {
            vscode.window.showErrorMessage('No code selected');
        }
    });

    // Register all commands
    context.subscriptions.push(
        terminalCommand,
        explainError,
        generateCommit,
        generateDocstring,
        generateTests,
        fixCodeAction,
        explainCodeAction
    );
}

async function getInlineSuggestion(prompt: string): Promise<string | undefined> {
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: [{ role: 'user', content: prompt }],
                max_tokens: 50,
                temperature: 0.3
            })
        });
        
        if (response.ok) {
            const data: any = await response.json();
            return data.choices[0].message.content.trim();
        }
    } catch (error) {
        // Silent fail for inline suggestions
    }
    return undefined;
}

async function sendToAPI(content: string, title: string, systemPrompt?: string): Promise<void> {
    try {
        const messages = [];
        if (systemPrompt) {
            messages.push({ role: 'system', content: systemPrompt });
        }
        messages.push({ role: 'user', content: `${title}:\n\n${content}` });
        
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: messages,
                temperature: 0.5,
                max_tokens: 2000
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data: any = await response.json();
        const aiResponse = data.choices[0].message.content;
        
        const panel = vscode.window.createWebviewPanel(
            'llmChatResponse',
            `LLM Chat: ${title}`,
            vscode.ViewColumn.Beside,
            { enableScripts: true }
        );
        
        panel.webview.html = getResponseHtml(aiResponse, title);
        
    } catch (error: any) {
        vscode.window.showErrorMessage(`Failed to connect to LLM Chat App: ${error.message}`);
    }
}

function getResponseHtml(content: string, title: string): string {
    const escapedContent = content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return `
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    font-family: var(--vscode-editor-font-family);
                    padding: 20px;
                    line-height: 1.6;
                }
                pre {
                    background-color: var(--vscode-textCodeBlock-background);
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                    white-space: pre-wrap;
                }
                code {
                    font-family: var(--vscode-editor-font-family);
                }
                button {
                    background-color: var(--vscode-button-background);
                    color: var(--vscode-button-foreground);
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    cursor: pointer;
                }
                button:hover {
                    background-color: var(--vscode-button-hoverBackground);
                }
            </style>
        </head>
        <body>
            <h3>🤖 ${title}</h3>
            <div>${escapedContent.replace(/\n/g, '<br>')}</div>
            <hr>
            <button onclick="copyToClipboard()">📋 Copy Response</button>
            <button onclick="insertToEditor()">✏️ Insert to Editor</button>
            <script>
                function copyToClipboard() {
                    const text = document.body.innerText.replace('Copy Response', '').replace('Insert to Editor', '').trim();
                    navigator.clipboard.writeText(text);
                }
                function insertToEditor() {
                    const vscode = acquireVsCodeApi();
                    vscode.postMessage({ command: 'insert', text: document.body.innerText });
                }
            </script>
        </body>
        </html>
    `;
}

export function deactivate() {}