/**
 * Task Watcher - Monitors the tasks directory for new CHANGE.json files
 */

import * as fs from 'fs';
import * as path from 'path';
import * as chokidar from 'chokidar';

export class TaskWatcher {
    private watcher: chokidar.FSWatcher | undefined;
    private tasksDir: string;
    private onTaskCallback: (taskPath: string) => void;
    private processedFiles: Set<string> = new Set();

    constructor(tasksDir: string, onTask: (taskPath: string) => void) {
        this.tasksDir = tasksDir;
        this.onTaskCallback = onTask;
    }

    start(): void {
        console.log(`Starting task watcher on: ${this.tasksDir}`);

        // Ensure directory exists
        if (!fs.existsSync(this.tasksDir)) {
            fs.mkdirSync(this.tasksDir, { recursive: true });
        }

        // Watch for new CHANGE-*.json files
        const pattern = path.join(this.tasksDir, 'CHANGE-*.json');
        
        this.watcher = chokidar.watch(pattern, {
            persistent: true,
            ignoreInitial: false,  // Process existing files on startup
            awaitWriteFinish: {
                stabilityThreshold: 500,
                pollInterval: 100
            }
        });

        this.watcher.on('add', (filePath: string) => {
            this.handleNewTask(filePath);
        });

        this.watcher.on('change', (filePath: string) => {
            // Re-process if file was modified (e.g., status changed back to pending)
            this.handleTaskChange(filePath);
        });

        this.watcher.on('error', (error: Error) => {
            console.error(`Watcher error: ${error}`);
        });

        console.log('Task watcher started');
    }

    stop(): void {
        if (this.watcher) {
            this.watcher.close();
            this.watcher = undefined;
            console.log('Task watcher stopped');
        }
    }

    private handleNewTask(filePath: string): void {
        // Skip if already processed
        if (this.processedFiles.has(filePath)) {
            return;
        }

        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            const task = JSON.parse(content);

            // Only process pending tasks
            if (task.status === 'pending') {
                console.log(`New pending task found: ${filePath}`);
                this.processedFiles.add(filePath);
                this.onTaskCallback(filePath);
            }
        } catch (error) {
            console.error(`Error reading task file ${filePath}:`, error);
        }
    }

    private handleTaskChange(filePath: string): void {
        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            const task = JSON.parse(content);

            // If status changed back to pending, allow re-processing
            if (task.status === 'pending') {
                this.processedFiles.delete(filePath);
                this.handleNewTask(filePath);
            }
        } catch (error) {
            console.error(`Error reading task file ${filePath}:`, error);
        }
    }

    isWatching(): boolean {
        return this.watcher !== undefined;
    }
}
