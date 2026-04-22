import * as vscode from 'vscode';

const API_URL = 'http://localhost:5000/v1/chat/completions';

export function activate(context: vscode.ExtensionContext) {
    console.log('LLM Chat App extension activated');

    // Command: Send selected code
    const sendSelection = vscode.commands.registerCommand('llmchat.sendSelection', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        
        if (!selectedText) {
            vscode.window.showErrorMessage('No text selected');
            return;
        }

        await sendToAPI(selectedText, 'Selected code');
    });

    // Command: Send entire file
    const sendFile = vscode.commands.registerCommand('llmchat.sendFile', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }

        const fileContent = editor.document.getText();
        const fileName = editor.document.fileName.split('/').pop() || 'unknown';
        
        await sendToAPI(fileContent, `File: ${fileName}`);
    });

    // Command: Send entire project
    const sendProject = vscode.commands.registerCommand('llmchat.sendProject', async () => {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (!workspaceFolder) {
            vscode.window.showErrorMessage('No workspace folder open');
            return;
        }

        vscode.window.showInformationMessage('Reading project files...');
        
        const files = await vscode.workspace.findFiles('**/*', '**/node_modules/**');
        let projectContent = '';
        
        for (const file of files.slice(0, 10)) {
            const content = await vscode.workspace.fs.readFile(file);
            const fileName = file.path.split('/').pop() || 'unknown';
            projectContent += `\n--- File: ${fileName} ---\n`;
            projectContent += Buffer.from(content).toString('utf-8');
            projectContent += '\n';
        }
        
        await sendToAPI(projectContent, `Project: ${workspaceFolder.name}`);
    });

    // Command: Apply AI edit
    const applyEdit = vscode.commands.registerCommand('llmchat.applyEdit', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        
        const suggestion = await vscode.window.showInputBox({
            prompt: 'Paste AI suggestion or enter edit instruction',
            placeHolder: 'Paste code or describe the change...'
        });
        
        if (suggestion) {
            await editor.edit((editBuilder: vscode.TextEditorEdit) => {
                editBuilder.replace(editor.selection, suggestion);
            });
            vscode.window.showInformationMessage('Edit applied');
        }
    });

    context.subscriptions.push(sendSelection, sendFile, sendProject, applyEdit);
}

async function sendToAPI(content: string, contextInfo: string): Promise<void> {
    try {
        const prompt = `${contextInfo}\n\n\`\`\`\n${content}\n\`\`\`\n\nPlease analyze this code and provide insights.`;
        
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: [{ role: 'user', content: prompt }]
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data: any = await response.json();
        const aiResponse = data.choices[0].message.content;
        
        // Show response in VS Code
        const panel = vscode.window.createWebviewPanel(
            'llmChatResponse',
            'LLM Chat App Response',
            vscode.ViewColumn.Beside,
            { enableScripts: true }
        );
        
        panel.webview.html = getResponseHtml(aiResponse);
        
    } catch (error: any) {
        vscode.window.showErrorMessage(`Failed to connect to LLM Chat App: ${error.message}`);
        vscode.window.showInformationMessage('Make sure LLM Chat App is running with API Server enabled');
    }
}

function getResponseHtml(content: string): string {
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
                }
                code {
                    font-family: var(--vscode-editor-font-family);
                }
            </style>
        </head>
        <body>
            <h3>🤖 AI Response</h3>
            <div>${escapedContent.replace(/\n/g, '<br>')}</div>
            <hr>
            <button onclick="copyToClipboard()">📋 Copy Response</button>
            <script>
                function copyToClipboard() {
                    const text = document.body.innerText.replace('Copy Response', '').trim();
                    navigator.clipboard.writeText(text);
                }
            </script>
        </body>
        </html>
    `;
}

export function deactivate() {}