"""
Task Manager - Creates and manages CHANGE.json task files
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class TaskManager:
    """
    Manages task files in the tasks directory
    """
    
    def __init__(self, tasks_dir: Path):
        self.tasks_dir = tasks_dir
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        
        # Archive completed tasks
        self.archive_dir = tasks_dir / "archive"
        self.archive_dir.mkdir(exist_ok=True)
    
    def create_task(
        self,
        task_type: str,
        description: str,
        scope: list[str],
        rules: list[str] = None,
        auto_commit: bool = True,
        source_message: str = "",
        sender: str = ""
    ) -> dict:
        """
        Create a new task file (CHANGE.json)
        """
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
        
        # Write task file
        task_file = self.tasks_dir / f"CHANGE-{task_id}.json"
        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)
        
        print(f"Created task: {task_file}")
        return task
    
    def list_tasks(self, status: str = None) -> list[dict]:
        """
        List all task files, optionally filtered by status
        """
        tasks = []
        
        for task_file in self.tasks_dir.glob("CHANGE-*.json"):
            try:
                with open(task_file) as f:
                    task = json.load(f)
                    if status is None or task.get("status") == status:
                        tasks.append(task)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading task file {task_file}: {e}")
        
        # Sort by creation time
        tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        return tasks
    
    def get_task(self, task_id: str) -> Optional[dict]:
        """
        Get a specific task by ID
        """
        task_file = self.tasks_dir / f"CHANGE-{task_id}.json"
        
        if not task_file.exists():
            # Check archive
            task_file = self.archive_dir / f"CHANGE-{task_id}.json"
        
        if task_file.exists():
            with open(task_file) as f:
                return json.load(f)
        
        return None
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        details: str = "",
        result: dict = None
    ) -> bool:
        """
        Update a task's status
        """
        task_file = self.tasks_dir / f"CHANGE-{task_id}.json"
        
        if not task_file.exists():
            return False
        
        with open(task_file) as f:
            task = json.load(f)
        
        task["status"] = status
        task["updated_at"] = datetime.utcnow().isoformat() + "Z"
        task["result"] = {
            "status": status,
            "details": details,
            "data": result
        }
        
        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)
        
        # Archive completed tasks
        if status in ["success", "failed", "manual_review"]:
            self._archive_task(task_file)
        
        return True
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task file
        """
        task_file = self.tasks_dir / f"CHANGE-{task_id}.json"
        
        if task_file.exists():
            task_file.unlink()
            return True
        
        return False
    
    def _archive_task(self, task_file: Path):
        """
        Move a completed task to the archive
        """
        archive_file = self.archive_dir / task_file.name
        task_file.rename(archive_file)
        print(f"Archived task: {archive_file}")
    
    def get_pending_tasks(self) -> list[dict]:
        """
        Get all pending tasks
        """
        return self.list_tasks(status="pending")
    
    def claim_task(self, task_id: str) -> bool:
        """
        Mark a task as being processed
        """
        return self.update_task_status(task_id, "processing")
