/**
 * History View Provider - Shows completed/processed tasks
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

interface HistoryItem {
    id: string;
    type: string;
    description: string;
    status: string;
    created_at: string;
    updated_at?: string;
    filePath: string;
}

export class HistoryViewProvider implements vscode.TreeDataProvider<HistoryTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<HistoryTreeItem | undefined | null | void> = new vscode.EventEmitter<HistoryTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<HistoryTreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: HistoryTreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: HistoryTreeItem): Promise<HistoryTreeItem[]> {
        if (element) {
            return [];
        }

        const items = await this.loadHistory();
        return items.map(item => new HistoryTreeItem(item));
    }

    private async loadHistory(): Promise<HistoryItem[]> {
        const config = vscode.workspace.getConfiguration('whatsappAutomation');
        const tasksDir = config.get<string>('tasksDirectory');

        if (!tasksDir) {
            return [];
        }

        const archiveDir = path.join(tasksDir, 'archive');
        if (!fs.existsSync(archiveDir)) {
            return [];
        }

        const items: HistoryItem[] = [];
        const files = fs.readdirSync(archiveDir);

        for (const file of files) {
            if (file.startsWith('CHANGE-') && file.endsWith('.json')) {
                const filePath = path.join(archiveDir, file);
                try {
                    const content = fs.readFileSync(filePath, 'utf-8');
                    const task = JSON.parse(content);
                    items.push({
                        ...task,
                        filePath
                    });
                } catch (error) {
                    console.error(`Error reading history file ${file}:`, error);
                }
            }
        }

        // Sort by date descending
        items.sort((a, b) => {
            const dateA = a.updated_at || a.created_at;
            const dateB = b.updated_at || b.created_at;
            return new Date(dateB).getTime() - new Date(dateA).getTime();
        });

        return items.slice(0, 50); // Limit to last 50
    }
}

class HistoryTreeItem extends vscode.TreeItem {
    constructor(public readonly item: HistoryItem) {
        super(item.description, vscode.TreeItemCollapsibleState.None);

        const date = new Date(item.updated_at || item.created_at).toLocaleDateString();
        this.description = `${item.status} • ${date}`;

        this.tooltip = `${item.description}\n\nStatus: ${item.status}\nType: ${item.type}`;

        // Set icon based on status
        switch (item.status) {
            case 'success':
                this.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('charts.green'));
                break;
            case 'failed':
                this.iconPath = new vscode.ThemeIcon('error', new vscode.ThemeColor('charts.red'));
                break;
            case 'manual_review':
                this.iconPath = new vscode.ThemeIcon('warning', new vscode.ThemeColor('charts.orange'));
                break;
            case 'rejected':
                this.iconPath = new vscode.ThemeIcon('close', new vscode.ThemeColor('charts.red'));
                break;
            default:
                this.iconPath = new vscode.ThemeIcon('history');
        }

        this.command = {
            command: 'whatsappAutomation.openTask',
            title: 'Open Task',
            arguments: [item.filePath]
        };
    }
}
