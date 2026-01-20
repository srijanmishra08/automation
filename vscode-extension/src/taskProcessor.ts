/**
 * Task Processor - Processes task files and invokes Copilot
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { GitManager } from './gitManager';

export interface Task {
    id: string;
    type: string;
    description: string;
    scope: string[];
    rules: string[];
    auto_commit: boolean;
    status: string;
    created_at: string;
    source?: {
        message: string;
        sender: string;
        timestamp: string;
    };
    result?: {
        status: string;
        details: string;
        data?: any;
    };
}

export class TaskProcessor {
    private gitManager: GitManager;
    private context: vscode.ExtensionContext;

    constructor(gitManager: GitManager, context: vscode.ExtensionContext) {
        this.gitManager = gitManager;
        this.context = context;
    }

    async processTask(taskPath: string): Promise<void> {
        console.log(`Processing task: ${taskPath}`);

        // Read and parse task
        const taskContent = fs.readFileSync(taskPath, 'utf-8');
        const task: Task = JSON.parse(taskContent);

        // Update status to processing
        this.updateTaskStatus(taskPath, task, 'processing');

        try {
            // Show progress
            await vscode.window.withProgress(
                {
                    location: vscode.ProgressLocation.Notification,
                    title: `Processing: ${task.description}`,
                    cancellable: true
                },
                async (progress, token) => {
                    // Step 1: Open target files
                    progress.report({ message: 'Opening files...', increment: 10 });
                    const openedFiles = await this.openTargetFiles(task.scope);

                    if (openedFiles.length === 0) {
                        throw new Error('No target files found');
                    }

                    // Step 2: Build and execute Copilot prompt
                    progress.report({ message: 'Invoking Copilot...', increment: 30 });
                    await this.invokeCopilot(task, openedFiles);

                    // Step 3: Wait for user to review/apply changes
                    progress.report({ message: 'Waiting for changes...', increment: 20 });
                    
                    // Give user time to review
                    const action = await vscode.window.showInformationMessage(
                        'Copilot has been invoked. Review the suggested changes.',
                        'Changes Applied',
                        'Reject Changes'
                    );

                    if (action === 'Reject Changes') {
                        this.updateTaskStatus(taskPath, task, 'rejected', 'User rejected changes');
                        return;
                    }

                    // Step 4: Check diff and auto-commit if allowed
                    progress.report({ message: 'Checking changes...', increment: 20 });
                    
                    if (task.auto_commit && this.canAutoCommit(task)) {
                        progress.report({ message: 'Auto-committing...', increment: 20 });
                        await this.autoCommitAndPush(task);
                        this.updateTaskStatus(taskPath, task, 'success', 'Changes committed and pushed');
                        
                        vscode.window.showInformationMessage(
                            `✅ Task completed: ${task.description}\nChanges committed and pushed.`
                        );
                    } else {
                        this.updateTaskStatus(taskPath, task, 'manual_review', 'Requires manual commit');
                        
                        vscode.window.showInformationMessage(
                            `⚠️ Task completed: ${task.description}\nManual commit required.`
                        );
                    }

                    // Notify webhook
                    await this.notifyWebhook(task);
                }
            );
        } catch (error) {
            console.error(`Error processing task: ${error}`);
            this.updateTaskStatus(taskPath, task, 'failed', `${error}`);
            vscode.window.showErrorMessage(`Task failed: ${error}`);
        }
    }

    private async openTargetFiles(scope: string[]): Promise<vscode.TextDocument[]> {
        const openedDocs: vscode.TextDocument[] = [];
        const workspaceFolders = vscode.workspace.workspaceFolders;

        if (!workspaceFolders) {
            throw new Error('No workspace folder open');
        }

        for (const filePath of scope) {
            // Try to find file in workspace
            for (const folder of workspaceFolders) {
                const fullPath = path.join(folder.uri.fsPath, filePath);
                
                if (fs.existsSync(fullPath)) {
                    const doc = await vscode.workspace.openTextDocument(fullPath);
                    await vscode.window.showTextDocument(doc, { preview: false });
                    openedDocs.push(doc);
                    break;
                }
            }
        }

        return openedDocs;
    }

    private async invokeCopilot(task: Task, openedFiles: vscode.TextDocument[]): Promise<void> {
        // Build the Copilot prompt
        const prompt = this.buildCopilotPrompt(task);

        // Focus on the first file
        if (openedFiles.length > 0) {
            await vscode.window.showTextDocument(openedFiles[0]);
        }

        // Try to use Copilot Chat API if available
        try {
            // Method 1: Use Copilot Chat command
            await vscode.commands.executeCommand('workbench.action.chat.open', {
                query: prompt
            });
        } catch (e) {
            // Method 2: Copy prompt to clipboard and notify user
            await vscode.env.clipboard.writeText(prompt);
            
            vscode.window.showInformationMessage(
                'Copilot prompt copied to clipboard. Open Copilot Chat and paste to apply changes.',
                'Open Copilot Chat'
            ).then(async (selection) => {
                if (selection === 'Open Copilot Chat') {
                    await vscode.commands.executeCommand('workbench.panel.chat.view.copilot.focus');
                }
            });
        }
    }

    private buildCopilotPrompt(task: Task): string {
        const scopeList = task.scope.map(f => `- ${f}`).join('\n');
        const rulesList = task.rules.map(r => `- ${r}`).join('\n');

        return `Apply the following change strictly:

## Task Type
${task.type}

## Description
${task.description}

## Target Files (ONLY modify these)
${scopeList}

## Rules (MUST follow)
${rulesList}

## Important
- Make ONLY the requested change
- Do NOT modify any other code
- Do NOT change layout or structure unless explicitly requested
- Preserve all existing functionality
- Keep the same code style and formatting

Please apply this change now.`;
    }

    private canAutoCommit(task: Task): boolean {
        const config = vscode.workspace.getConfiguration('whatsappAutomation');
        const autoCommitEnabled = config.get<boolean>('autoCommit', true);
        const safePatterns = config.get<string[]>('safeFilePatterns', ['*.tsx', '*.ts', '*.css', '*.json', '*.md']);

        if (!autoCommitEnabled) {
            return false;
        }

        // Check if task type is safe
        const safeTaskTypes = ['copy_change', 'color_change', 'seo_update'];
        if (!safeTaskTypes.includes(task.type)) {
            return false;
        }

        // Check if all files match safe patterns
        const minimatch = require('minimatch');
        for (const file of task.scope) {
            const isSafe = safePatterns.some(pattern => minimatch(file, pattern));
            if (!isSafe) {
                return false;
            }
        }

        return true;
    }

    private async autoCommitAndPush(task: Task): Promise<void> {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            throw new Error('No workspace folder');
        }

        const repoPath = workspaceFolders[0].uri.fsPath;

        // Check diff
        const config = vscode.workspace.getConfiguration('whatsappAutomation');
        const maxDiffLines = config.get<number>('maxDiffLines', 50);

        const diffLines = await this.gitManager.getDiffLineCount(repoPath);
        if (diffLines > maxDiffLines) {
            throw new Error(`Diff too large (${diffLines} lines). Max allowed: ${maxDiffLines}`);
        }

        // Validate changed files
        const changedFiles = await this.gitManager.getChangedFiles(repoPath);
        const allowedFiles = new Set(task.scope.map(f => path.normalize(f)));

        for (const file of changedFiles) {
            const normalizedFile = path.normalize(file);
            if (!allowedFiles.has(normalizedFile)) {
                throw new Error(`Unexpected file changed: ${file}. Only allowed: ${task.scope.join(', ')}`);
            }
        }

        // Stage, commit, and push
        const commitMessage = `🤖 Auto: ${task.description}\n\nTask ID: ${task.id}\nType: ${task.type}`;
        
        await this.gitManager.stageFiles(repoPath, task.scope);
        await this.gitManager.commit(repoPath, commitMessage);
        await this.gitManager.push(repoPath);
    }

    private updateTaskStatus(taskPath: string, task: Task, status: string, details: string = ''): void {
        task.status = status;
        task.result = {
            status,
            details,
            data: {
                updated_at: new Date().toISOString()
            }
        };

        fs.writeFileSync(taskPath, JSON.stringify(task, null, 2));
    }

    private async notifyWebhook(task: Task): Promise<void> {
        const config = vscode.workspace.getConfiguration('whatsappAutomation');
        const webhookUrl = config.get<string>('webhookUrl');

        if (!webhookUrl) {
            return;
        }

        try {
            const response = await fetch(webhookUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_id: task.id,
                    status: task.status,
                    details: task.result?.details || ''
                })
            });

            if (!response.ok) {
                console.error(`Webhook notification failed: ${response.status}`);
            }
        } catch (error) {
            console.error(`Webhook notification error: ${error}`);
        }
    }
}
