"""
WhatsApp → Copilot Automation Pipeline
FastAPI Backend - Main Application
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

from intent_parser import IntentParser
from task_manager import TaskManager
from message_store import MessageStore
from voice_transcriber import VoiceTranscriber

load_dotenv()

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

# Initialize components
tasks_dir = Path(os.getenv("TASKS_DIR", "../tasks"))
tasks_dir.mkdir(parents=True, exist_ok=True)

intent_parser = IntentParser()
task_manager = TaskManager(tasks_dir)
message_store = MessageStore()
voice_transcriber = VoiceTranscriber()


class ManualTaskRequest(BaseModel):
    """Manual task creation request"""
    type: str
    description: str
    scope: list[str]
    rules: list[str] = []
    auto_commit: bool = True


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "WhatsApp Automation Pipeline",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(default=""),
    NumMedia: int = Form(default=0),
    MediaUrl0: Optional[str] = Form(default=None),
    MediaContentType0: Optional[str] = Form(default=None),
):
    """
    Twilio WhatsApp webhook endpoint
    Receives messages and voice notes, processes them into tasks
    """
    # Validate Twilio request (optional but recommended for production)
    # validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))
    # ... validation logic
    
    sender = From
    message_text = Body
    response = MessagingResponse()
    
    try:
        # Handle voice messages
        if NumMedia > 0 and MediaContentType0 and "audio" in MediaContentType0:
            # Download and transcribe voice note
            transcription = await voice_transcriber.transcribe_from_url(MediaUrl0)
            message_text = transcription
            
            # Store the voice message
            message_store.store_message(
                sender=sender,
                content=transcription,
                message_type="voice",
                metadata={"original_url": MediaUrl0}
            )
            
            response.message(f"🎤 Transcribed: \"{transcription}\"")
        else:
            # Store text message
            message_store.store_message(
                sender=sender,
                content=message_text,
                message_type="text"
            )
        
        if not message_text:
            response.message("Please send a text message or voice note describing the change you want to make.")
            return str(response)
        
        # Parse intent from message
        intent = await intent_parser.parse(message_text)
        
        if intent.get("confidence", 0) < 0.5:
            response.message(
                "🤔 I'm not sure what change you want. Please be more specific.\n\n"
                "Example: \"Change the hero button text to 'Book a Free Audit'\""
            )
            return str(response)
        
        # Create task file
        task = task_manager.create_task(
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
            f"🚀 VS Code will process this shortly."
        )
        
    except Exception as e:
        print(f"Error processing message: {e}")
        response.message(
            "❌ Sorry, there was an error processing your request. Please try again."
        )
    
    return str(response)


@app.post("/tasks/create")
async def create_task_manually(task_request: ManualTaskRequest):
    """
    Create a task manually via API (for testing or integrations)
    """
    task = task_manager.create_task(
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
    """List all pending tasks"""
    tasks = task_manager.list_tasks()
    return {"tasks": tasks, "count": len(tasks)}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task by ID"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    success = task_manager.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted", "task_id": task_id}


@app.get("/messages")
async def list_messages(limit: int = 50):
    """List stored messages"""
    messages = message_store.get_messages(limit=limit)
    return {"messages": messages, "count": len(messages)}


@app.post("/webhook/task-completed")
async def task_completed_webhook(request: Request):
    """
    Webhook called by VS Code extension when a task is completed
    """
    data = await request.json()
    task_id = data.get("task_id")
    status = data.get("status")  # "success", "failed", "manual_review"
    details = data.get("details", "")
    
    # Update task status
    task_manager.update_task_status(task_id, status, details)
    
    # TODO: Send WhatsApp notification back to user
    # This would use the Twilio API to send a message
    
    return {"received": True, "task_id": task_id, "status": status}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
