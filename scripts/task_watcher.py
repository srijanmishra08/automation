#!/usr/bin/env python3
"""
Standalone Task Watcher Script
Alternative to the VS Code extension for simpler setups

This script watches for CHANGE.json files and opens them in VS Code
with a pre-formatted Copilot prompt copied to clipboard.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
TASKS_DIR = os.environ.get("TASKS_DIR", "./tasks")
POLL_INTERVAL = 2  # seconds
TARGET_REPO = os.environ.get("TARGET_REPO", ".")

processed_tasks = set()


def load_processed_tasks():
    """Load list of already processed tasks"""
    processed_file = Path(TASKS_DIR) / ".processed"
    if processed_file.exists():
        return set(processed_file.read_text().strip().split("\n"))
    return set()


def save_processed_task(task_id: str):
    """Save task as processed"""
    processed_file = Path(TASKS_DIR) / ".processed"
    with open(processed_file, "a") as f:
        f.write(f"{task_id}\n")


def build_copilot_prompt(task: dict) -> str:
    """Build the Copilot prompt from task"""
    scope_list = "\n".join(f"- {f}" for f in task["scope"])
    rules_list = "\n".join(f"- {r}" for r in task.get("rules", []))

    return f"""Apply the following change strictly:

## Task Type
{task["type"]}

## Description
{task["description"]}

## Target Files (ONLY modify these)
{scope_list}

## Rules (MUST follow)
{rules_list}

## Important
- Make ONLY the requested change
- Do NOT modify any other code
- Do NOT change layout or structure unless explicitly requested
- Preserve all existing functionality
- Keep the same code style and formatting

Please apply this change now."""


def copy_to_clipboard(text: str):
    """Copy text to clipboard (macOS)"""
    process = subprocess.Popen(
        ["pbcopy"],
        stdin=subprocess.PIPE,
        env={"LANG": "en_US.UTF-8"}
    )
    process.communicate(text.encode("utf-8"))


def open_in_vscode(files: list[str], repo_path: str):
    """Open files in VS Code"""
    full_paths = []
    for file in files:
        full_path = Path(repo_path) / file
        if full_path.exists():
            full_paths.append(str(full_path))
        else:
            print(f"  ⚠️  File not found: {file}")
    
    if full_paths:
        subprocess.run(["code"] + full_paths, check=True)


def update_task_status(task_path: Path, status: str, details: str = ""):
    """Update task status in the JSON file"""
    with open(task_path) as f:
        task = json.load(f)
    
    task["status"] = status
    task["result"] = {
        "status": status,
        "details": details,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    with open(task_path, "w") as f:
        json.dump(task, f, indent=2)


def process_task(task_path: Path):
    """Process a single task file"""
    print(f"\n📋 Processing: {task_path.name}")
    
    with open(task_path) as f:
        task = json.load(f)
    
    # Skip non-pending tasks
    if task.get("status") != "pending":
        print(f"  ⏭️  Skipping (status: {task.get('status')})")
        return
    
    print(f"  📝 {task['description']}")
    print(f"  🎯 Type: {task['type']}")
    print(f"  📁 Scope: {', '.join(task['scope'])}")
    
    # Update status
    update_task_status(task_path, "processing")
    
    # Build prompt and copy to clipboard
    prompt = build_copilot_prompt(task)
    copy_to_clipboard(prompt)
    print("  📋 Copilot prompt copied to clipboard!")
    
    # Open files in VS Code
    print("  🔓 Opening files in VS Code...")
    open_in_vscode(task["scope"], TARGET_REPO)
    
    # Wait for user
    print("\n" + "="*50)
    print("📌 NEXT STEPS:")
    print("1. Open Copilot Chat in VS Code (Cmd+Shift+I)")
    print("2. Paste the prompt (Cmd+V)")
    print("3. Review and apply changes")
    print("4. Save the files")
    print("="*50)
    
    # Mark as processed
    processed_tasks.add(task["id"])
    save_processed_task(task["id"])
    
    # Wait for user to mark complete
    while True:
        response = input("\n✅ Done? (y=success / n=failed / m=manual review): ").lower()
        if response == "y":
            update_task_status(task_path, "success", "Completed via watcher script")
            print("  ✅ Task marked as success")
            
            # Offer to commit
            if task.get("auto_commit", False):
                commit = input("🔄 Auto-commit? (y/n): ").lower()
                if commit == "y":
                    run_git_commit(task)
            break
        elif response == "n":
            update_task_status(task_path, "failed", "Failed via watcher script")
            print("  ❌ Task marked as failed")
            break
        elif response == "m":
            update_task_status(task_path, "manual_review", "Requires manual review")
            print("  ⚠️  Task marked for manual review")
            break


def run_git_commit(task: dict):
    """Run git commit and push"""
    print("  📤 Committing changes...")
    
    try:
        # Stage files
        for file in task["scope"]:
            subprocess.run(["git", "add", file], cwd=TARGET_REPO, check=True)
        
        # Commit
        message = f"🤖 Auto: {task['description']}\n\nTask ID: {task['id']}\nType: {task['type']}"
        subprocess.run(["git", "commit", "-m", message], cwd=TARGET_REPO, check=True)
        
        # Push
        subprocess.run(["git", "push"], cwd=TARGET_REPO, check=True)
        print("  ✅ Changes pushed!")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Git error: {e}")


def watch_tasks():
    """Main watch loop"""
    global processed_tasks
    
    tasks_dir = Path(TASKS_DIR)
    tasks_dir.mkdir(parents=True, exist_ok=True)
    
    processed_tasks = load_processed_tasks()
    
    print(f"👀 Watching for tasks in: {tasks_dir.absolute()}")
    print(f"📂 Target repo: {Path(TARGET_REPO).absolute()}")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            # Find new task files
            for task_file in tasks_dir.glob("CHANGE-*.json"):
                task_id = task_file.stem.replace("CHANGE-", "")
                
                if task_id not in processed_tasks:
                    process_task(task_file)
            
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n👋 Stopping watcher...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    # Allow overriding paths via command line
    if len(sys.argv) > 1:
        TASKS_DIR = sys.argv[1]
    if len(sys.argv) > 2:
        TARGET_REPO = sys.argv[2]
    
    watch_tasks()
