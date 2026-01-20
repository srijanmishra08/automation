/**
 * Git Manager - Handles git operations for auto-commit/push
 */

import * as vscode from 'vscode';
import { simpleGit, SimpleGit, StatusResult } from 'simple-git';
import * as path from 'path';

export class GitManager {
    /**
     * Get the number of lines changed in the current diff
     */
    async getDiffLineCount(repoPath: string): Promise<number> {
        const git: SimpleGit = simpleGit(repoPath);
        
        try {
            const diff = await git.diff(['--stat']);
            
            // Parse the stat output to get total lines changed
            const lines = diff.split('\n');
            const summaryLine = lines[lines.length - 2]; // Second to last line has summary
            
            // Example: " 3 files changed, 45 insertions(+), 12 deletions(-)"
            const match = summaryLine.match(/(\d+) insertions?\(\+\), (\d+) deletions?\(-\)/);
            
            if (match) {
                return parseInt(match[1]) + parseInt(match[2]);
            }
            
            return 0;
        } catch (error) {
            console.error('Error getting diff line count:', error);
            return 0;
        }
    }

    /**
     * Get list of changed files
     */
    async getChangedFiles(repoPath: string): Promise<string[]> {
        const git: SimpleGit = simpleGit(repoPath);
        
        try {
            const status: StatusResult = await git.status();
            
            const changedFiles: string[] = [
                ...status.modified,
                ...status.created,
                ...status.deleted,
                ...status.renamed.map(r => r.to)
            ];
            
            return changedFiles;
        } catch (error) {
            console.error('Error getting changed files:', error);
            return [];
        }
    }

    /**
     * Stage specific files
     */
    async stageFiles(repoPath: string, files: string[]): Promise<void> {
        const git: SimpleGit = simpleGit(repoPath);
        
        try {
            await git.add(files);
            console.log(`Staged files: ${files.join(', ')}`);
        } catch (error) {
            console.error('Error staging files:', error);
            throw error;
        }
    }

    /**
     * Commit staged changes
     */
    async commit(repoPath: string, message: string): Promise<string> {
        const git: SimpleGit = simpleGit(repoPath);
        
        try {
            const result = await git.commit(message);
            console.log(`Committed: ${result.commit}`);
            return result.commit;
        } catch (error) {
            console.error('Error committing:', error);
            throw error;
        }
    }

    /**
     * Push to remote
     */
    async push(repoPath: string, remote: string = 'origin', branch?: string): Promise<void> {
        const git: SimpleGit = simpleGit(repoPath);
        
        try {
            // Get current branch if not specified
            if (!branch) {
                const branchResult = await git.revparse(['--abbrev-ref', 'HEAD']);
                branch = branchResult.trim();
            }
            
            await git.push(remote, branch);
            console.log(`Pushed to ${remote}/${branch}`);
        } catch (error) {
            console.error('Error pushing:', error);
            throw error;
        }
    }

    /**
     * Check if working directory is clean
     */
    async isClean(repoPath: string): Promise<boolean> {
        const git: SimpleGit = simpleGit(repoPath);
        
        try {
            const status = await git.status();
            return status.isClean();
        } catch (error) {
            console.error('Error checking status:', error);
            return false;
        }
    }

    /**
     * Get the diff for specific files
     */
    async getDiff(repoPath: string, files?: string[]): Promise<string> {
        const git: SimpleGit = simpleGit(repoPath);
        
        try {
            if (files && files.length > 0) {
                return await git.diff(['--', ...files]);
            }
            return await git.diff();
        } catch (error) {
            console.error('Error getting diff:', error);
            return '';
        }
    }

    /**
     * Validate that only allowed files are changed
     */
    async validateChanges(repoPath: string, allowedFiles: string[]): Promise<{
        valid: boolean;
        unexpectedFiles: string[];
    }> {
        const changedFiles = await this.getChangedFiles(repoPath);
        const normalizedAllowed = new Set(allowedFiles.map(f => path.normalize(f)));
        
        const unexpectedFiles: string[] = [];
        
        for (const file of changedFiles) {
            const normalizedFile = path.normalize(file);
            if (!normalizedAllowed.has(normalizedFile)) {
                unexpectedFiles.push(file);
            }
        }
        
        return {
            valid: unexpectedFiles.length === 0,
            unexpectedFiles
        };
    }

    /**
     * Revert changes to specific files
     */
    async revertFiles(repoPath: string, files: string[]): Promise<void> {
        const git: SimpleGit = simpleGit(repoPath);
        
        try {
            await git.checkout(['--', ...files]);
            console.log(`Reverted files: ${files.join(', ')}`);
        } catch (error) {
            console.error('Error reverting files:', error);
            throw error;
        }
    }

    /**
     * Create a new branch
     */
    async createBranch(repoPath: string, branchName: string): Promise<void> {
        const git: SimpleGit = simpleGit(repoPath);
        
        try {
            await git.checkoutLocalBranch(branchName);
            console.log(`Created and switched to branch: ${branchName}`);
        } catch (error) {
            console.error('Error creating branch:', error);
            throw error;
        }
    }

    /**
     * Stash current changes
     */
    async stash(repoPath: string, message?: string): Promise<void> {
        const git: SimpleGit = simpleGit(repoPath);
        
        try {
            if (message) {
                await git.stash(['push', '-m', message]);
            } else {
                await git.stash(['push']);
            }
            console.log('Changes stashed');
        } catch (error) {
            console.error('Error stashing:', error);
            throw error;
        }
    }

    /**
     * Pop stashed changes
     */
    async stashPop(repoPath: string): Promise<void> {
        const git: SimpleGit = simpleGit(repoPath);
        
        try {
            await git.stash(['pop']);
            console.log('Stash popped');
        } catch (error) {
            console.error('Error popping stash:', error);
            throw error;
        }
    }
}
