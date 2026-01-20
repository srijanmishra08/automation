/**
 * WhatsApp Copilot Automation Extension
 * Main entry point
 */

import * as vscode from 'vscode';
import { TaskWatcher } from './taskWatcher';
import { TaskProcessor } from './taskProcessor';
import { GitManager } from './gitManager';
import { TasksViewProvider } from './views/tasksView';
import { HistoryViewProvider } from './views/historyView';

let taskWatcher: TaskWatcher | undefined;
let taskProcessor: TaskProcessor | undefined;
let gitManager: GitManager | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('WhatsApp Copilot Automation extension activated');

    // Initialize components
    gitManager = new GitManager();
    taskProcessor = new TaskProcessor(gitManager, context);
    
    // Initialize views
    const tasksViewProvider = new TasksViewProvider(context);
    const historyViewProvider = new HistoryViewProvider(context);
    
    vscode.window.registerTreeDataProvider('whatsappAutomation.tasksView', tasksViewProvider);
    vscode.window.registerTreeDataProvider('whatsappAutomation.historyView', historyViewProvider);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('whatsappAutomation.startWatching', async () => {
            await startWatching(context, tasksViewProvider);
        }),

        vscode.commands.registerCommand('whatsappAutomation.stopWatching', () => {
            stopWatching();
        }),

        vscode.commands.registerCommand('whatsappAutomation.processTask', async (uri?: vscode.Uri) => {
            await processTaskFile(uri);
        }),

        vscode.commands.registerCommand('whatsappAutomation.showTasks', async () => {
            await showPendingTasks();
        }),

        vscode.commands.registerCommand('whatsappAutomation.configureTasksDir', async () => {
            await configureTasksDirectory();
        }),

        vscode.commands.registerCommand('whatsappAutomation.refreshTasks', () => {
            tasksViewProvider.refresh();
        }),

        vscode.commands.registerCommand('whatsappAutomation.openTask', async (taskPath: string) => {
            const doc = await vscode.workspace.openTextDocument(taskPath);
            await vscode.window.showTextDocument(doc);
        })
    );

    // Auto-start watcher if configured
    const config = vscode.workspace.getConfiguration('whatsappAutomation');
    const tasksDir = config.get<string>('tasksDirectory');
    
    if (tasksDir) {
        startWatching(context, tasksViewProvider);
    } else {
        vscode.window.showInformationMessage(
            'WhatsApp Automation: Configure tasks directory to start watching',
            'Configure'
        ).then(selection => {
            if (selection === 'Configure') {
                configureTasksDirectory();
            }
        });
    }
}

async function startWatching(
    context: vscode.ExtensionContext,
    tasksViewProvider: TasksViewProvider
): Promise<void> {
    const config = vscode.workspace.getConfiguration('whatsappAutomation');
    let tasksDir = config.get<string>('tasksDirectory');

    if (!tasksDir) {
        tasksDir = await configureTasksDirectory();
        if (!tasksDir) {
            return;
        }
    }

    // Stop existing watcher
    if (taskWatcher) {
        taskWatcher.stop();
    }

    // Create new watcher
    taskWatcher = new TaskWatcher(tasksDir, async (taskPath) => {
        console.log(`New task detected: ${taskPath}`);
        
        // Refresh the tasks view
        tasksViewProvider.refresh();
        
        // Show notification
        const action = await vscode.window.showInformationMessage(
            `New task detected: ${taskPath}`,
            'Process Now',
            'View Task',
            'Ignore'
        );

        if (action === 'Process Now') {
            await processTaskFile(vscode.Uri.file(taskPath));
        } else if (action === 'View Task') {
            const doc = await vscode.workspace.openTextDocument(taskPath);
            await vscode.window.showTextDocument(doc);
        }
    });

    taskWatcher.start();
    
    vscode.window.showInformationMessage(`Watching for tasks in: ${tasksDir}`);
    
    // Update status bar
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.text = '$(eye) WhatsApp Automation Active';
    statusBarItem.tooltip = `Watching: ${tasksDir}`;
    statusBarItem.command = 'whatsappAutomation.showTasks';
    statusBarItem.show();
    
    context.subscriptions.push(statusBarItem);
}

function stopWatching(): void {
    if (taskWatcher) {
        taskWatcher.stop();
        taskWatcher = undefined;
        vscode.window.showInformationMessage('Task watcher stopped');
    }
}

async function processTaskFile(uri?: vscode.Uri): Promise<void> {
    let taskPath: string;

    if (uri) {
        taskPath = uri.fsPath;
    } else {
        // Prompt for file selection
        const files = await vscode.window.showOpenDialog({
            canSelectFiles: true,
            canSelectFolders: false,
            canSelectMany: false,
            filters: {
                'Task Files': ['json']
            },
            title: 'Select Task File'
        });

        if (!files || files.length === 0) {
            return;
        }

        taskPath = files[0].fsPath;
    }

    if (!taskProcessor) {
        vscode.window.showErrorMessage('Task processor not initialized');
        return;
    }

    try {
        await taskProcessor.processTask(taskPath);
    } catch (error) {
        vscode.window.showErrorMessage(`Error processing task: ${error}`);
    }
}

async function showPendingTasks(): Promise<void> {
    const config = vscode.workspace.getConfiguration('whatsappAutomation');
    const tasksDir = config.get<string>('tasksDirectory');

    if (!tasksDir) {
        vscode.window.showWarningMessage('Tasks directory not configured');
        return;
    }

    // Focus on the tasks view
    await vscode.commands.executeCommand('whatsappAutomation.tasksView.focus');
}

async function configureTasksDirectory(): Promise<string | undefined> {
    const folders = await vscode.window.showOpenDialog({
        canSelectFiles: false,
        canSelectFolders: true,
        canSelectMany: false,
        title: 'Select Tasks Directory'
    });

    if (!folders || folders.length === 0) {
        return undefined;
    }

    const tasksDir = folders[0].fsPath;
    
    const config = vscode.workspace.getConfiguration('whatsappAutomation');
    await config.update('tasksDirectory', tasksDir, vscode.ConfigurationTarget.Global);
    
    vscode.window.showInformationMessage(`Tasks directory set to: ${tasksDir}`);
    
    return tasksDir;
}

export function deactivate() {
    if (taskWatcher) {
        taskWatcher.stop();
    }
}
