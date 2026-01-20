# VS Code Extension Setup Guide

## Prerequisites

- VS Code 1.85.0 or later
- Node.js 18+ and npm
- GitHub Copilot extension installed

## Installation

### Option 1: Development Mode (Recommended for now)

1. Open the extension folder in VS Code:
   ```bash
   cd vscode-extension
   code .
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Compile the extension:
   ```bash
   npm run compile
   ```

4. Press **F5** to launch the Extension Development Host

5. In the new VS Code window, open your target project

### Option 2: Package and Install

1. Install vsce:
   ```bash
   npm install -g @vscode/vsce
   ```

2. Package the extension:
   ```bash
   cd vscode-extension
   npm install
   npm run compile
   vsce package
   ```

3. Install the .vsix file:
   - Open VS Code
   - Go to Extensions → ⋯ → Install from VSIX
   - Select the generated .vsix file

## Configuration

### Set Tasks Directory

1. Open Command Palette (Cmd+Shift+P)
2. Run: **WhatsApp Automation: Configure Tasks Directory**
3. Select the `tasks` folder from this project

Or set it manually in settings:
```json
{
  "whatsappAutomation.tasksDirectory": "/path/to/automation/tasks"
}
```

### Other Settings

```json
{
  // Enable/disable auto-commit
  "whatsappAutomation.autoCommit": true,
  
  // Webhook URL for task completion notifications
  "whatsappAutomation.webhookUrl": "http://localhost:8000/webhook/task-completed",
  
  // File patterns safe for auto-commit
  "whatsappAutomation.safeFilePatterns": [
    "*.tsx",
    "*.ts", 
    "*.css",
    "*.json",
    "*.md"
  ],
  
  // Max lines changed for auto-commit
  "whatsappAutomation.maxDiffLines": 50
}
```

## Usage

### Automatic Task Processing

1. Start the watcher: **WhatsApp Automation: Start Task Watcher**
2. When a new CHANGE.json appears in the tasks folder:
   - A notification will appear
   - Click "Process Now" to apply changes

### Manual Task Processing

1. Open Command Palette (Cmd+Shift+P)
2. Run: **WhatsApp Automation: Process Task File**
3. Select the task JSON file

### View Tasks

- Click the WhatsApp Automation icon in the Activity Bar
- See pending tasks in the "Tasks" view
- See completed tasks in the "History" view

## How It Works

1. **Task Detection**: Extension watches the tasks directory for new `CHANGE-*.json` files

2. **File Opening**: Opens all files listed in the task's `scope`

3. **Copilot Invocation**: Opens Copilot Chat with a structured prompt:
   ```
   Apply the following change strictly:
   
   ## Task Type
   copy_change
   
   ## Description
   Change hero CTA to 'Book a Free Audit'
   
   ## Target Files (ONLY modify these)
   - app/components/Hero.tsx
   
   ## Rules (MUST follow)
   - Do not change layout
   - Do not touch styles
   ```

4. **Review**: User reviews Copilot's suggested changes

5. **Auto-Commit** (if enabled and safe):
   - Validates only allowed files changed
   - Checks diff size is within limits
   - Commits and pushes automatically

## Troubleshooting

### Extension not activating
- Check VS Code version (1.85.0+)
- Check Developer Console for errors (Help → Toggle Developer Tools)

### Copilot Chat not opening
- Ensure GitHub Copilot extension is installed and active
- Prompt will be copied to clipboard as fallback

### Auto-commit failing
- Check git is configured in the workspace
- Verify file patterns match settings
- Check diff size limits
