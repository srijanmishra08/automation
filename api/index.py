"""
Vercel Serverless Function Entry Point
Simplified version for Vercel deployment
"""

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import uuid
import os
import base64
import httpx

app = FastAPI(title="WhatsApp Automation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GitHub configuration - set these in Vercel environment variables
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "srijanmishra08/automation")  # Your repo
TARGET_REPO = os.environ.get("TARGET_REPO", "")  # The landing page repo to modify

# In-memory storage (resets on cold start)
tasks_store = {}
messages_store = []


class TaskRequest(BaseModel):
    type: str
    description: str
    scope: list[str]
    rules: list[str] = []
    auto_commit: bool = True


async def write_task_to_github(task: dict) -> tuple[bool, str]:
    """Write task file to GitHub repo. Returns (success, error_message)"""
    if not GITHUB_TOKEN:
        return False, "No GITHUB_TOKEN set"
    
    try:
        repo = GITHUB_REPO
        file_path = f"tasks/CHANGE-{task['id']}.json"
        content = json.dumps(task, indent=2)
        content_b64 = base64.b64encode(content.encode()).decode()
        
        url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        data = {
            "message": f"📋 New task: {task['description'][:50]}",
            "content": content_b64,
            "branch": "main"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(url, headers=headers, json=data)
            if resp.status_code in [200, 201]:
                return True, "Success"
            else:
                return False, f"GitHub API error {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, f"Exception: {str(e)}"


def parse_intent(message: str) -> dict:
    """
    Simple rule-based intent parsing.
    
    NOTE: This is a SIMPLE RULE-BASED parser, NOT an AI model.
    For production, you could integrate:
    - OpenAI GPT-4 for better understanding
    - Claude API for structured extraction
    - Custom fine-tuned model
    
    Supports patterns like:
    - "change hero text to X"
    - "update footer in my-repo"
    - "modify navbar color to blue"
    """
    import re
    msg = message.lower()
    original_msg = message
    
    # Detect task type
    if any(w in msg for w in ["change", "update", "modify", "text", "copy", "title", "heading"]):
        task_type = "copy_change"
    elif any(w in msg for w in ["color", "background", "style", "font", "size"]):
        task_type = "style_change"
    elif any(w in msg for w in ["add", "create", "new"]):
        task_type = "component_add"
    elif any(w in msg for w in ["remove", "delete", "hide"]):
        task_type = "component_remove"
    else:
        task_type = "general_edit"
    
    # Detect target repo FIRST (pattern: "in repo-name" at the end)
    target_repo = None
    repo_match = re.search(r'\bin\s+([a-zA-Z0-9_-]+)\s*$', original_msg, re.IGNORECASE)
    if repo_match:
        target_repo = repo_match.group(1)
    
    # For sphereco_production - it's a single HTML file
    if target_repo and "sphereco" in target_repo.lower():
        scope = ["index.html"]
    else:
        # Detect target component for React/Next.js projects
        scope = ["index.html"]  # default for simple sites
        component_map = {
            "header": "app/components/Header.tsx",
            "footer": "app/components/Footer.tsx",
            "nav": "app/components/Navbar.tsx",
            "navbar": "app/components/Navbar.tsx",
            "hero": "app/components/Hero.tsx",
            "cta": "app/components/CTA.tsx",
            "button": "app/components/Button.tsx",
            "form": "app/components/ContactForm.tsx",
            "pricing": "app/components/Pricing.tsx",
            "features": "app/components/Features.tsx",
        }
        
        for keyword, file_path in component_map.items():
            if keyword in msg:
                scope = [file_path]
                break
    
    # Determine if auto-commit is safe
    safe_types = ["copy_change", "style_change"]
    auto_commit = task_type in safe_types
    
    result = {
        "type": task_type,
        "description": original_msg,
        "scope": scope,
        "target_repo": target_repo,
        "rules": [
            "Do not change layout or structure",
            "Only modify what is explicitly requested",
            "Preserve existing functionality",
            "Keep the same code style"
        ],
        "auto_commit": auto_commit
    }
    
    if target_repo:
        result["target_repo"] = target_repo
    
    return result


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "WhatsApp Automation API",
        "time": datetime.utcnow().isoformat(),
        "github_connected": bool(GITHUB_TOKEN),
        "github_token_length": len(GITHUB_TOKEN) if GITHUB_TOKEN else 0,
        "repo": GITHUB_REPO
    }


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    From: str = Form(default="unknown"),
    Body: str = Form(default=""),
):
    """Twilio WhatsApp webhook"""
    try:
        from twilio.twiml.messaging_response import MessagingResponse
        
        response = MessagingResponse()
        
        if not Body:
            response.message("Please send a message describing the change you want.")
            return Response(content=str(response), media_type="application/xml")
        
        # Store message
        messages_store.append({
            "sender": From,
            "content": Body,
            "time": datetime.utcnow().isoformat()
        })
        
        # Parse and create task
        intent = parse_intent(Body)
        task_id = str(uuid.uuid4())[:8]
        
        task = {
            "id": task_id,
            **intent,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "sender": From
        }
        tasks_store[task_id] = task
        
        # Write task to GitHub
        github_success, github_error = await write_task_to_github(task)
        
        status_emoji = "✅" if github_success else "⚠️"
        github_status = "Synced to GitHub" if github_success else f"Local only ({github_error[:50]})"
        
        response.message(
            f"{status_emoji} Task created!\n\n"
            f"📋 {task['type']}\n"
            f"📝 {task['description'][:100]}\n"
            f"📁 {', '.join(task['scope'])}\n"
            f"🆔 {task_id}\n\n"
            f"📌 {github_status}"
        )
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        # Return error as TwiML so Twilio doesn't retry
        error_xml = f'<Response><Message>Error: {str(e)[:100]}</Message></Response>'
        return Response(content=error_xml, media_type="application/xml")


@app.post("/tasks/create")
def create_task(req: TaskRequest):
    task_id = str(uuid.uuid4())[:8]
    task = {
        "id": task_id,
        "type": req.type,
        "description": req.description,
        "scope": req.scope,
        "rules": req.rules,
        "auto_commit": req.auto_commit,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    tasks_store[task_id] = task
    return task


@app.get("/tasks")
def list_tasks():
    return {"tasks": list(tasks_store.values()), "count": len(tasks_store)}


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_store[task_id]


@app.get("/messages")
def list_messages():
    return {"messages": messages_store[-50:], "count": len(messages_store)}


@app.get("/test-github")
async def test_github_write():
    """Test endpoint to verify GitHub integration"""
    test_task = {
        "id": "test-" + str(uuid.uuid4())[:4],
        "type": "test",
        "description": "Test task from API",
        "scope": ["test.tsx"],
        "rules": [],
        "status": "test",
        "created_at": datetime.utcnow().isoformat()
    }
    
    success, error_msg = await write_task_to_github(test_task)
    
    return {
        "success": success,
        "error": error_msg,
        "task_id": test_task["id"],
        "github_token_set": bool(GITHUB_TOKEN),
        "github_token_prefix": GITHUB_TOKEN[:20] + "..." if GITHUB_TOKEN else None,
        "repo": GITHUB_REPO
    }
