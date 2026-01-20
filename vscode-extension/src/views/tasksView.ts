/**
 * Tasks View Provider - Shows pending tasks in the sidebar
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

interface TaskItem {
    id: string;
    type: string;
    description: string;
    scope: string[];
    status: string;
    created_at: string;
    filePath: string;
}

export class TasksViewProvider implements vscode.TreeDataProvider<TaskTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<TaskTreeItem | undefined | null | void> = new vscode.EventEmitter<TaskTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<TaskTreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: TaskTreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: TaskTreeItem): Promise<TaskTreeItem[]> {
        if (element) {
            // Return task details
            return this.getTaskDetails(element.task);
        }

        // Return list of tasks
        const tasks = await this.loadTasks();
        return tasks.map(task => new TaskTreeItem(
            task,
            vscode.TreeItemCollapsibleState.Collapsed
        ));
    }

    private async loadTasks(): Promise<TaskItem[]> {
        const config = vscode.workspace.getConfiguration('whatsappAutomation');
        const tasksDir = config.get<string>('tasksDirectory');

        if (!tasksDir || !fs.existsSync(tasksDir)) {
            return [];
        }

        const tasks: TaskItem[] = [];
        const files = fs.readdirSync(tasksDir);

        for (const file of files) {
            if (file.startsWith('CHANGE-') && file.endsWith('.json')) {
                const filePath = path.join(tasksDir, file);
                try {
                    const content = fs.readFileSync(filePath, 'utf-8');
                    const task = JSON.parse(content);
                    tasks.push({
                        ...task,
                        filePath
                    });
                } catch (error) {
                    console.error(`Error reading task file ${file}:`, error);
                }
            }
        }

        // Sort by status (pending first) then by date
        tasks.sort((a, b) => {
            if (a.status === 'pending' && b.status !== 'pending') return -1;
            if (a.status !== 'pending' && b.status === 'pending') return 1;
            return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });

        return tasks;
    }

    private getTaskDetails(task: TaskItem): TaskTreeItem[] {
        const items: TaskTreeItem[] = [];

        // Type
        items.push(new TaskTreeItem(
            { ...task, id: `${task.id}-type` } as TaskItem,
            vscode.TreeItemCollapsibleState.None,
            `Type: ${task.type}`,
            'symbol-type'
        ));

        // Scope
        for (const file of task.scope) {
            items.push(new TaskTreeItem(
                { ...task, id: `${task.id}-${file}` } as TaskItem,
                vscode.TreeItemCollapsibleState.None,
                file,
                'file-code'
            ));
        }

        // Created at
        const createdDate = new Date(task.created_at).toLocaleString();
        items.push(new TaskTreeItem(
            { ...task, id: `${task.id}-date` } as TaskItem,
            vscode.TreeItemCollapsibleState.None,
            `Created: ${createdDate}`,
            'calendar'
        ));

        return items;
    }
}

class TaskTreeItem extends vscode.TreeItem {
    constructor(
        public readonly task: TaskItem,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        label?: string,
        iconId?: string
    ) {
        super(label || task.description, collapsibleState);

        if (!label) {
            // This is the main task item
            this.tooltip = `${task.description}\n\nType: ${task.type}\nStatus: ${task.status}\nFiles: ${task.scope.join(', ')}`;
            
            // Set icon based on status
            switch (task.status) {
                case 'pending':
                    this.iconPath = new vscode.ThemeIcon('circle-outline', new vscode.ThemeColor('charts.yellow'));
                    break;
                case 'processing':
                    this.iconPath = new vscode.ThemeIcon('sync~spin', new vscode.ThemeColor('charts.blue'));
                    break;
                case 'success':
                    this.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('charts.green'));
                    break;
                case 'failed':
                    this.iconPath = new vscode.ThemeIcon('error', new vscode.ThemeColor('charts.red'));
                    break;
                case 'manual_review':
                    this.iconPath = new vscode.ThemeIcon('warning', new vscode.ThemeColor('charts.orange'));
                    break;
                default:
                    this.iconPath = new vscode.ThemeIcon('circle-outline');
            }

            // Set context value for menu items
            this.contextValue = `task-${task.status}`;

            // Set command to open task
            this.command = {
                command: 'whatsappAutomation.openTask',
                title: 'Open Task',
                arguments: [task.filePath]
            };

            // Add status badge
            this.description = task.status;
        } else {
            // This is a detail item
            if (iconId) {
                this.iconPath = new vscode.ThemeIcon(iconId);
            }
        }
    }
}
