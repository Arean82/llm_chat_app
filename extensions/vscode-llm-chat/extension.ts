import * as vscode from 'vscode';

async function getApiConfig(context: vscode.ExtensionContext): Promise<{ apiUrl: string, authHeader: string }> {
    const config = vscode.workspace.getConfiguration('llmChat');
    const baseUrl = config.get<string>('apiUrl') || 'http://localhost:5000';
    
    // Check if secure token exists in context.secrets
    let apiToken = await context.secrets.get('apiToken');
    if (!apiToken) {
        apiToken = config.get<string>('apiToken') || 'llm-local-auth-82c4f3eb0d';
    }
    
    return {
        apiUrl: `${baseUrl.replace(/\/$/, '')}/v1/chat/completions`,
        authHeader: `Bearer ${apiToken}`
    };
}

export function activate(context: vscode.ExtensionContext) {
    console.log('Synora Studio extension activated');

    // 1. Inline suggestions (triggered by typing)
    const inlineProvider: vscode.InlineCompletionItemProvider = {
        async provideInlineCompletionItems(document, position, inlineContext, token) {
            const line = document.lineAt(position.line).text;
            const lineText = line.substring(0, position.character);
            
            // Only suggest if line has content
            if (lineText.length < 3) return;
            
            const prompt = `Complete this code: ${lineText}`;
            try {
                const config = await getApiConfig(context);
                const suggestion = await getInlineSuggestion(config.apiUrl, config.authHeader, prompt);
                
                if (suggestion) {
                    return [new vscode.InlineCompletionItem(suggestion)];
                }
            } catch (e) {
                // silent error
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
        
        const config = await getApiConfig(context);
        await sendToAPI(config.apiUrl, config.authHeader, selectedText, 'Fix this code', 'Fix any bugs or issues in this code and explain the fixes:');
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
        
        const config = await getApiConfig(context);
        await sendToAPI(config.apiUrl, config.authHeader, selectedText, 'Explain this code', 'Explain this code in simple terms:');
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
            const config = await getApiConfig(context);
            await sendToAPI(config.apiUrl, config.authHeader, userPrompt, 'Generate terminal command', 'Generate only the terminal command, no explanation:');
        }
    });

    // 4. Error explanation
    const explainError = vscode.commands.registerCommand('llmchat.explainError', async () => {
        const errorMessage = await vscode.window.showInputBox({
            prompt: 'Paste the error message',
            placeHolder: 'Error message from terminal or problem panel...'
        });
        
        if (errorMessage) {
            const config = await getApiConfig(context);
            await sendToAPI(config.apiUrl, config.authHeader, errorMessage, 'Explain this error', 'Explain this error and provide a fix:');
        }
    });
    
    // Register error hover provider
    const errorHoverProvider = vscode.languages.registerHoverProvider('*', {
        async provideHover(document, position) {
            const wordRange = document.getWordRangeAtPosition(position);
            const word = document.getText(wordRange);
            
            const diagnostics = vscode.languages.getDiagnostics(document.uri);
            const errorAtPosition = diagnostics.some(d => d.range.contains(position) && d.severity === vscode.DiagnosticSeverity.Error);
            
            if (errorAtPosition) {
                const errorText = diagnostics.find(d => d.range.contains(position))?.message || word;
                try {
                    const config = await getApiConfig(context);
                    const suggestion = await getInlineSuggestion(config.apiUrl, config.authHeader, `Explain this error: ${errorText}`);
                    
                    if (suggestion) {
                        return new vscode.Hover(`**LLM Chat:** ${suggestion}`);
                    }
                } catch (e) {
                    // silent hover fail
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
        
        const config = await getApiConfig(context);
        await sendToAPI(config.apiUrl, config.authHeader, changesText, 'Generate commit message', 'Generate a concise git commit message for these changes:');
    });

    // 6. Documentation generator (add docstring)
    const generateDocstring = vscode.commands.registerCommand('llmchat.generateDocstring', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;
        
        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);
        const functionMatch = selectedText.match(/def\s+(\w+)\s*\([^)]*\)/);
        
        if (functionMatch) {
            const config = await getApiConfig(context);
            await sendToAPI(config.apiUrl, config.authHeader, selectedText, 'Generate docstring', 'Generate a Python docstring for this function:');
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
            const config = await getApiConfig(context);
            await sendToAPI(config.apiUrl, config.authHeader, selectedText, 'Generate unit tests', 'Generate unit tests for this code using pytest:');
        } else {
            vscode.window.showErrorMessage('No code selected');
        }
    });

    // 8. Onboard Workspace / Settings Command
    const onboardCommand = vscode.commands.registerCommand('llmchat.onboard', () => {
        const panel = vscode.window.createWebviewPanel(
            'llmChatOnboard',
            'Synora Studio SaaS: Onboard Workspace',
            vscode.ViewColumn.One,
            { enableScripts: true }
        );

        panel.webview.html = getOnboardingHtml();

        panel.webview.onDidReceiveMessage(async (message) => {
            const { command, serverUrl, email, username, password, apiPassportKey } = message;

            if (command === 'login' || command === 'register') {
                const targetUrl = serverUrl.replace(/\/$/, '');
                try {
                    if (command === 'register') {
                        // POST /api/register to provision isolated cloud sandbox
                        const regResponse = await fetch(`${targetUrl}/api/register`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                api_key: apiPassportKey,
                                username: username || 'Developer',
                                email: email,
                                password: password,
                                key_type: 'byok'
                            })
                        });

                        const regData: any = await regResponse.json();
                        if (!regResponse.ok) {
                            throw new Error(regData.error || 'Registration failed');
                        }
                        vscode.window.showInformationMessage('🎉 Cloud sandbox successfully provisioned!');
                    }

                    // Authenticate and fetch secure JWT / Tenant access token
                    const authResponse = await fetch(`${targetUrl}/api/login`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            username_or_email: email,
                            password: password
                        })
                    });

                    const authData: any = await authResponse.json();
                    if (!authResponse.ok) {
                        throw new Error(authData.error || 'Authentication handshake failed');
                    }

                    const secureKey = authData.user?.api_key || authData.user?.passport_token || '';
                    if (!secureKey) {
                        throw new Error('SaaS server returned empty API key access token.');
                    }

                    // Commit configurations and secure vault token
                    await context.secrets.store('apiToken', secureKey);
                    
                    const config = vscode.workspace.getConfiguration('llmChat');
                    await config.update('apiUrl', targetUrl, vscode.ConfigurationTarget.Global);
                    await config.update('apiToken', 'vault-secured', vscode.ConfigurationTarget.Global);

                    vscode.window.showInformationMessage(`💻 Workspace connected successfully! Welcome, ${authData.user?.username}.`);
                    panel.dispose();

                } catch (e: any) {
                    panel.webview.postMessage({ status: 'error', message: e.message });
                }
            }
        });
    });

    // Register all commands
    context.subscriptions.push(
        terminalCommand,
        explainError,
        generateCommit,
        generateDocstring,
        generateTests,
        fixCodeAction,
        explainCodeAction,
        onboardCommand
    );
}

async function getInlineSuggestion(apiUrl: string, authHeader: string, prompt: string): Promise<string | undefined> {
    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': authHeader
            },
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

async function sendToAPI(apiUrl: string, authHeader: string, content: string, title: string, systemPrompt?: string): Promise<void> {
    try {
        const messages = [];
        if (systemPrompt) {
            messages.push({ role: 'system', content: systemPrompt });
        }
        messages.push({ role: 'user', content: `${title}:\n\n${content}` });
        
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': authHeader
            },
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
        vscode.window.showErrorMessage(`Failed to connect to Synora Studio: ${error.message}`);
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

function getOnboardingHtml(): string {
    return `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Quantum Onboard</title>
            <style>
                body {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    font-family: sans-serif;
                    padding: 2rem;
                    display: flex;
                    justify-content: center;
                }
                .card {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    padding: 2rem;
                    width: 100%;
                    max-width: 450px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                }
                h2 {
                    margin-top: 0;
                    color: #569cd6;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    padding-bottom: 10px;
                }
                .input-group {
                    margin-bottom: 1.2rem;
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }
                label {
                    font-size: 0.9rem;
                    font-weight: bold;
                }
                input {
                    background: rgba(0,0,0,0.3);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    color: white;
                    padding: 8px;
                    border-radius: 4px;
                    outline: none;
                }
                input:focus {
                    border-color: #569cd6;
                }
                .btn {
                    background: #0e639c;
                    border: none;
                    color: white;
                    padding: 10px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: bold;
                    width: 100%;
                    margin-top: 10px;
                }
                .btn:hover {
                    background: #1177bb;
                }
                .btn-success {
                    background: #388a34;
                }
                .btn-success:hover {
                    background: #43a047;
                }
                .status {
                    margin-top: 15px;
                    padding: 10px;
                    border-radius: 4px;
                    font-size: 0.9rem;
                }
                .error {
                    background: rgba(244, 67, 54, 0.15);
                    border: 1px solid #f44336;
                    color: #f44336;
                }
                .tabs {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 1.5rem;
                }
                .tab {
                    flex: 1;
                    padding: 8px;
                    text-align: center;
                    background: rgba(255,255,255,0.05);
                    border: 1px solid transparent;
                    border-radius: 4px;
                    cursor: pointer;
                }
                .tab.active {
                    background: rgba(255,255,255,0.1);
                    border-color: #569cd6;
                    color: #569cd6;
                }
            </style>
        </head>
        <body>
            <div class="card">
                <h2>🤖 Quantum Workspace Onboarding</h2>
                
                <div class="tabs">
                    <div id="tab-login" class="tab active" onclick="switchMode('login')">Connect Sign In</div>
                    <div id="tab-register" class="tab" onclick="switchMode('register')">Register Workspace</div>
                </div>

                <form id="onboard-form" onsubmit="handleSubmit(event)">
                    <div class="input-group">
                        <label>SaaS Server Host URL:</label>
                        <input type="url" id="serverUrl" value="http://localhost:5000" required>
                    </div>

                    <div class="input-group" id="group-username" style="display: none;">
                        <label>Developer Display Name:</label>
                        <input type="text" id="username" placeholder="CyberPilot">
                    </div>

                    <div class="input-group">
                        <label>Email Address:</label>
                        <input type="email" id="email" placeholder="pilot@quantum.net" required autocomplete="username">
                    </div>

                    <div class="input-group">
                        <label>Master Password:</label>
                        <input type="password" id="password" required autocomplete="current-password">
                    </div>

                    <div class="input-group" id="group-passport" style="display: none;">
                        <label>API Key Passport (BYOK Key):</label>
                        <input type="password" id="apiPassportKey" placeholder="nvapi-xxxxxx / sk-xxxxxx">
                    </div>

                    <div id="feedback" class="status error" style="display: none;"></div>

                    <button type="submit" id="submit-btn" class="btn">Connect Workspace</button>
                </form>
            </div>

            <script>
                const vscode = acquireVsCodeApi();
                let mode = 'login';

                function switchMode(newMode) {
                    mode = newMode;
                    document.getElementById('tab-login').className = newMode === 'login' ? 'tab active' : 'tab';
                    document.getElementById('tab-register').className = newMode === 'register' ? 'tab active' : 'tab';
                    
                    document.getElementById('group-username').style.display = newMode === 'register' ? 'flex' : 'none';
                    document.getElementById('group-passport').style.display = newMode === 'register' ? 'flex' : 'none';
                    
                    const submitBtn = document.getElementById('submit-btn');
                    if (newMode === 'login') {
                        submitBtn.innerText = 'Connect Workspace';
                        submitBtn.className = 'btn';
                        document.getElementById('username').required = false;
                        document.getElementById('apiPassportKey').required = false;
                    } else {
                        submitBtn.innerText = 'Register & Provision Workspace';
                        submitBtn.className = 'btn btn-success';
                        document.getElementById('username').required = true;
                        document.getElementById('apiPassportKey').required = true;
                    }
                }

                function handleSubmit(e) {
                    e.preventDefault();
                    document.getElementById('feedback').style.display = 'none';
                    
                    const serverUrl = document.getElementById('serverUrl').value;
                    const email = document.getElementById('email').value;
                    const password = document.getElementById('password').value;
                    const username = document.getElementById('username').value;
                    const apiPassportKey = document.getElementById('apiPassportKey').value;

                    vscode.postMessage({
                        command: mode,
                        serverUrl,
                        email,
                        password,
                        username,
                        apiPassportKey
                    });
                }

                window.addEventListener('message', event => {
                    const message = event.data;
                    if (message.status === 'error') {
                        const feedback = document.getElementById('feedback');
                        feedback.innerText = '⚠️ ' + message.message;
                        feedback.style.display = 'block';
                    }
                });
            </script>
        </body>
        </html>
    `;
}

export function deactivate() {}