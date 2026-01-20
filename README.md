# WhatsApp → Copilot Automation Pipeline

Automated workflow that receives WhatsApp messages via Twilio, converts them to structured tasks, and uses VS Code + Copilot to apply changes automatically.

## Architecture

```
WhatsApp → Twilio → FastAPI Server → CHANGE.json → VS Code Extension → Copilot → Git → Vercel
```

## Components

1. **FastAPI Backend** (`/backend`) - Webhook receiver & task generator
2. **VS Code Extension** (`/vscode-extension`) - File watcher & Copilot invoker
3. **Task Files** - JSON-based change specifications

## Quick Start

### 1. Start the FastAPI Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure your Twilio credentials
uvicorn main:app --reload --port 8000
```

### 2. Expose Local Server (for Twilio webhook)

```bash
ngrok http 8000
```

### 3. Install VS Code Extension

```bash
cd vscode-extension
npm install
npm run compile
# Press F5 in VS Code to run the extension
```

### 4. Configure Twilio

Set your webhook URL in Twilio Console:
`https://your-ngrok-url.ngrok.io/webhook/whatsapp`

## Task File Format

```json
{
  "id": "task-uuid",
  "type": "copy_change",
  "description": "Change hero CTA to 'Book a Free Audit'",
  "scope": ["app/components/Hero.tsx"],
  "rules": [
    "Do not change layout",
    "Do not touch styles"
  ],
  "auto_commit": true,
  "created_at": "2026-01-20T10:00:00Z"
}
```

## Supported Task Types

- `copy_change` - Text/copy modifications
- `section_reorder` - Reorder page sections
- `color_change` - Update color tokens
- `seo_update` - Modify SEO tags
- `component_edit` - General component changes

## Safety Rules

Auto-commit is only allowed for:
- Text changes
- Section reordering
- Color token updates
- SEO tag modifications

Changes outside the whitelist require manual review.
