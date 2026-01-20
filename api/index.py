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

app = FastAPI(title="WhatsApp Automation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (resets on cold start - use database for persistence)
tasks_store = {}
messages_store = []


class TaskRequest(BaseModel):
    type: str
    description: str
    scope: list[str]
    rules: list[str] = []
    auto_commit: bool = True


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
        "time": datetime.utcnow().isoformat()
    }


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    From: str = Form(default="unknown"),
    Body: str = Form(default=""),
):
    """Twilio WhatsApp webhook"""
    try:
        from twilio.twiml.messaging_response import MessagingResponse
    except ImportError:
        return Response(
            content="<Response><Message>Error: Twilio not installed</Message></Response>",
            media_type="application/xml"
        )
    
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
    
    response.message(
        f"✅ Task created!\n\n"
        f"📋 {task['type']}\n"
        f"📝 {task['description'][:100]}\n"
        f"📁 {', '.join(task['scope'])}\n"
        f"🆔 {task_id}"
    )
    
    return Response(content=str(response), media_type="application/xml")


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
