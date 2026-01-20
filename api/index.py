"""
Vercel Serverless Function Entry Point
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json
import uuid
from pathlib import Path

app = FastAPI(
    title="WhatsApp Automation Pipeline",
    description="Receives WhatsApp messages and converts them to Copilot tasks",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory storage for serverless (Vercel doesn't persist /tmp across invocations)
# In production, use a database like Vercel KV, Supabase, or MongoDB
tasks_store = {}
messages_store = []


class ManualTaskRequest(BaseModel):
    type: str
    description: str
    scope: list[str]
    rules: list[str] = []
    auto_commit: bool = True


def create_task(
    task_type: str,
    description: str,
    scope: list[str],
    rules: list[str] = None,
    auto_commit: bool = True,
    source_message: str = "",
    sender: str = ""
) -> dict:
    """Create a new task"""
    task_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    task = {
        "id": task_id,
        "type": task_type,
        "description": description,
        "scope": scope,
        "rules": rules or [],
        "auto_commit": auto_commit,
        "status": "pending",
        "created_at": timestamp,
        "source": {
            "message": source_message,
            "sender": sender,
            "timestamp": timestamp
        },
        "result": None
    }
    
    tasks_store[task_id] = task
    return task


def parse_intent_simple(message: str) -> dict:
    """Simple rule-based intent parsing (no OpenAI dependency for basic deployment)"""
    message_lower = message.lower()
    
    # Detect task type
    task_type = "component_edit"
    if any(word in message_lower for word in ["change text", "change button", "change cta", "rename", "update text"]):
        task_type = "copy_change"
    elif any(word in message_lower for word in ["color", "theme", "background"]):
        task_type = "color_change"
    elif any(word in message_lower for word in ["seo", "meta", "title tag"]):
        task_type = "seo_update"
    
    # Detect scope
    scope = ["app/components/Hero.tsx"]
    if "hero" in message_lower:
        scope = ["app/components/Hero.tsx"]
    elif "header" in message_lower:
        scope = ["app/components/Header.tsx"]
    elif "footer" in message_lower:
        scope = ["app/components/Footer.tsx"]
    elif "nav" in message_lower:
        scope = ["app/components/Nav.tsx"]
    
    # Generate rules
    rules = [
        "Do not change layout structure",
        "Do not remove existing functionality",
        "Preserve all existing imports",
        "Only modify what is explicitly requested"
    ]
    
    return {
        "type": task_type,
        "description": message,
        "scope": scope,
        "rules": rules,
        "auto_commit": task_type in ["copy_change", "color_change", "seo_update"],
        "confidence": 0.7
    }


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "WhatsApp Automation Pipeline",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(default=""),
    Body: str = Form(default=""),
    NumMedia: int = Form(default=0),
):
    """Twilio WhatsApp webhook endpoint"""
    from twilio.twiml.messaging_response import MessagingResponse
    
    sender = From
    message_text = Body
    response = MessagingResponse()
    
    try:
        # Store message
        messages_store.append({
            "id": str(uuid.uuid4()),
            "sender": sender,
            "content": message_text,
            "type": "text",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        if not message_text:
            response.message("Please send a text message describing the change you want to make.")
            return PlainTextResponse(content=str(response), media_type="application/xml")
        
        # Parse intent
        intent = parse_intent_simple(message_text)
        
        # Create task
        task = create_task(
            task_type=intent["type"],
            description=intent["description"],
            scope=intent["scope"],
            rules=intent.get("rules", []),
            auto_commit=intent.get("auto_commit", True),
            source_message=message_text,
            sender=sender
        )
        
        # Respond to user
        response.message(
            f"✅ Task created!\n\n"
            f"📋 Type: {task['type']}\n"
            f"📝 {task['description']}\n"
            f"📁 Files: {', '.join(task['scope'])}\n\n"
            f"🆔 Task ID: {task['id']}"
        )
        
    except Exception as e:
        print(f"Error processing message: {e}")
        response.message(f"❌ Error: {str(e)}")
    
    return PlainTextResponse(content=str(response), media_type="application/xml")


@app.post("/tasks/create")
async def create_task_manually(task_request: ManualTaskRequest):
    """Create a task manually via API"""
    task = create_task(
        task_type=task_request.type,
        description=task_request.description,
        scope=task_request.scope,
        rules=task_request.rules,
        auto_commit=task_request.auto_commit,
        source_message="Manual API request",
        sender="api"
    )
    return JSONResponse(content=task, status_code=201)


@app.get("/tasks")
async def list_tasks():
    """List all tasks"""
    return {"tasks": list(tasks_store.values()), "count": len(tasks_store)}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task"""
    task = tasks_store.get(task_id)
    if not task:
        return JSONResponse(content={"error": "Task not found"}, status_code=404)
    return task


@app.get("/messages")
async def list_messages(limit: int = 50):
    """List stored messages"""
    return {"messages": messages_store[-limit:], "count": len(messages_store)}


# Vercel handler
handler = app
