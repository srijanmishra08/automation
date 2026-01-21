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


async def write_task_to_github(task: dict) -> bool:
    """Write task file to GitHub repo"""
    if not GITHUB_TOKEN:
        print("No GITHUB_TOKEN set")
        return False
    
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
                print(f"Task written to GitHub: {file_path}")
                return True
            else:
                print(f"GitHub API error: {resp.status_code} - {resp.text}")
                return False
    except Exception as e:
        print(f"Error writing to GitHub: {e}")
        return False


def parse_intent(message: str) -> dict:
    """Simple intent parsing"""
    msg = message.lower()
    
    task_type = "copy_change" if any(w in msg for w in ["change", "update", "modify", "text", "button"]) else "component_edit"
    
    scope = ["app/components/Hero.tsx"]
    for component in ["header", "footer", "nav", "hero", "cta"]:
        if component in msg:
            scope = [f"app/components/{component.title()}.tsx"]
            break
    
    return {
        "type": task_type,
        "description": message,
        "scope": scope,
        "rules": ["Do not change layout", "Only modify what is requested"],
        "auto_commit": True
    }


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "WhatsApp Automation API",
        "time": datetime.utcnow().isoformat(),
        "github_connected": bool(GITHUB_TOKEN),
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
        github_success = await write_task_to_github(task)
        
        status_emoji = "✅" if github_success else "⚠️"
        github_status = "Synced to GitHub" if github_success else "Local only"
        
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
